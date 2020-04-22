import os
import sys
import json
import time
import shlex
import socket
import queue
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import argparse

from azure.iot.device import IoTHubDeviceClient, Message

from utils.forza_telemetry import TelemetryManager
from utils.file_upload import upload_file_through_iothub

BASE_DIR = "."
CONFIG_FNAME = os.path.join("config", "forza_config.json")
LOG_FILE_NAME = 'forza_iot.log'

tp = ThreadPoolExecutor(10)  # max 10 threads
def threaded(fn):
    def wrapper(*args, **kwargs):
        return tp.submit(fn, *args, **kwargs)  # returns Future object
    return wrapper

class ForzaIoTApp():
    
    def __init__(self, base_dir, config_path):
        with open(os.path.join(base_dir, config_path), "r") as f:
            self.forza_config = json.load(f)

        self._init_logger()

        self._setup_udp_socket()
        self.telemetry_manager = TelemetryManager(
            self.forza_config["device"]["output_fname"],
            self.forza_config["device"]["telemetry_format_fname"]
        )
        self.send_ip = self.forza_config["device"]["send_ip"]
        self.send_port = self.forza_config["device"]["send_port"]

        # Get the connection string
        # TODO(): Risk: the file is saved on the disk in plain text
        conn_str_fname = os.path.join(base_dir, self.forza_config["iothub"]["conn_str_fname"])
        self.conn_str = open(conn_str_fname, 'r').read()
        
        # Create instance of the device client using the authentication provider
        self.device_client = IoTHubDeviceClient.create_from_connection_string(self.conn_str)
        self.device_client.connect()
        
    def _init_logger(self):

        self.logger = logging.getLogger(__name__)
        if self.forza_config["device"].get("debug", False):
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.WARNING)
        self.logger.handlers = []
        formatter = logging.Formatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s',
                "%Y-%m-%dT%H:%M:%S%z")
        # Stream handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        # File handler
        if self.forza_config["device"].get("log_fname", None):
            handler = logging.FileHandler(self.forza_config["device"]["log_fname"])
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.telemetry_to_log = ["IsRaceOn", "RacePosition", "CurrentRaceTime", "PositionX", "PositionY", "PositionZ"]

    def _setup_udp_socket(self):
        recv_ip = self.forza_config["device"]["receive_ip"] #"" #"10.94.72.86" # "0.0.0.0" #"127.0.0.1"
        recv_port = self.forza_config["device"]["receive_port"]
        self.sock = socket.socket(socket.AF_INET, # Internet
                             socket.SOCK_DGRAM) # UDP
        self.sock.bind((recv_ip, recv_port))
        # Set timeout to jump out of the blocked listening,
        # so that keyboard interupt can be receviced.
        self.sock.settimeout(1)
    
    @threaded
    def _send_message(self, message):
        
        # Send a single message
        print("Sending message...")
        iothub_msg = Message(
            json.dumps(message["data"]),
            content_encoding="UTF-8",
            content_type="application/json"
        )
        properties = message.get("custom_properties", None)
        if properties is not None:
            iothub_msg.custom_properties.update(properties)
        self.device_client.send_message(iothub_msg)
        print("Message successfully sent!")
    
    @threaded
    def _upload_file(self, path_to_src:str, dst_fname:str):
        upload_file_through_iothub(self.conn_str, path_to_src, dst_fname)
    
    def _check_position(curr_pos:iter, start_pos:iter, threshold:float=200**2) -> bool:
        # The threshold is for the slight difference between
        # the starting position and the ending position.
        # Before a racing, your car is usually waiting at around 100 unit length
        # before the starting/ending line, which is known as the staging line.
        diff_pos = [(curr_i - start_i) ** 2 for curr_i, start_i in zip(curr_pos, start_pos)]
        diff_pos = sum(diff_pos)
        return diff_pos < threshold
    
    def _update_race_status(self, cur_status:int, race_pos_not_zero:bool, race_time_not_zero:bool) -> int:
        # cur_status: 0: not in race event,
        #             1: race event starts, will be set to 2 outside afterwards
        #             2: race event is on,
        #             3: race event stops, will be set to 0 or 4 outside afterwards
        #             4: race event is paused
        #
        # status transfer table:
        # cur_status, race_pos_not_zero, race_time_not_zero, next_status
        #          0,                 0,                              0
        #          0,                 1,                 0,           0
        #          0,                 1,                 1,           1
        #          2,                 0,                              3
        #          2,                 1,                              2
        #          4,                 0,                              4
        #          4,                 1,                              2
        if cur_status == 0 and race_pos_not_zero is True and race_time_not_zero is True:
            return 1
        if cur_status == 2 and race_pos_not_zero is False:
            return 3
        if cur_status == 4 and race_pos_not_zero is True:
            return 2
        return cur_status
    
    def run(self):
        
        race_event_status = 0
        start_pos = None

        print("Ready. Waiting for messages.")
        last_put_time = time.time()
        last_log_time = time.time()
        while True:
            
            # Set timeout to jump out of the blocked listening,
            # so that keyboard interupt can be receviced.
            data = None
            while not data:
                try:
                    data, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
                except socket.timeout:
                    pass

            # Forward the udp package to somewhere else, e.g. driving simulator.
            if self.send_ip:
                self.sock.sendto(data, (self.send_ip, self.send_port))

            dict_telemetry = self.telemetry_manager.parse(data)

            if self.forza_config["device"].get("debug", False):
                this_log_time = time.time()
                if this_log_time - last_log_time > 1:
                    self.logger.info({
                        k:v for k, v in dict_telemetry.items() if k in self.telemetry_to_log
                    })
                    last_log_time = this_log_time
            this_put_time = time.time()

            race_event_status = self._update_race_status(
                race_event_status,
                dict_telemetry["RacePosition"] != 0,
                dict_telemetry["CurrentRaceTime"] > 0
            )
            # Write the telemetry if in a race.
            if race_event_status in (1, 2):
                self.telemetry_manager.write(dict_telemetry)
            dict_telemetry["RaceStatus"] = race_event_status

            # If a race event starts, record the starting X, Y, Z position.
            # The position will be used in race event ending check.
            if race_event_status == 1:
                print("Recording start position.")
                start_pos = (
                    dict_telemetry["PositionX"],
                    dict_telemetry["PositionY"],
                    dict_telemetry["PositionZ"]
                )
                race_event_status = 2

            # If a race event is on, record the current telemetry.
            # It will be used to tell whether the race ends or
            # pauses when blank data is detected.
            if race_event_status == 2:
                prev_telemetry = dict_telemetry

            # If a race event stops, check whetehr it is a pause or an end.
            if race_event_status == 3:
                # For a full 3-lap race, if
                #     1) a race event stops (race_event_status == 3),
                #     2) the current position is close to the start position,
                #     3) is in the 3rd lap, and
                #     4) race time is in a reasonable range
                #   then it is the end of the race event.
                # For a short race, it is always the end of the race.
                if self.forza_config["device"].get("3_lap_race", True):
                    race_event_status = 4
                    if start_pos is None:
                        print("Start position not found.")
                        continue
                    stop_pos = (
                        prev_telemetry["PositionX"],
                        prev_telemetry["PositionY"],
                        prev_telemetry["PositionZ"]
                    )
                    if not self._check_position(stop_pos, start_pos):
                        print("Stop position {} is not close to the start position {}.".format(stop_pos, start_pos))
                        continue
                    stop_lap = prev_telemetry["LapNumber"]
                    if not (stop_lap == 2): # LapNumber starts from 0
                        print("In lap {}, not the 3rd.".format(stop_lap))
                        continue
                    if prev_telemetry["CurrentRaceTime"] < 2.5 * prev_telemetry["BestLap"]:
                        print("CurrentRaceTime is {}. Too early to stop.".format(prev_telemetry["CurrentRaceTime"]))
                        continue
                race_event_status = 0

                # At the end of a race event, we will
                #     1) rename the telemetry csv,
                #     2) send the telemetry csv to Azure Storage, and
                #     3) create a new csv
                # Remarks:
                #     1) If you want to remove the status transfer 2 -> 3,
                #        remember to handle prev_telemetry == None
                upload_file_name = self.telemetry_manager.prepare_upload_file()
                self._upload_file(upload_file_name, os.path.basename(upload_file_name))

            # Send telemetry data to IoT Hub no faster than 1 msg/sec
            # if race event is on.
            if race_event_status == 2 and this_put_time - last_put_time >= 1:
                self._send_message({"data": dict_telemetry})
                last_put_time = this_put_time

if __name__ == "__main__":
    
    print("Initializing.")
    parser = argparse.ArgumentParser(description='Run Forza IoT demo device client.')
    parser.add_argument('--base_dir', dest='base_dir', default=BASE_DIR,
                    help='Base directory of the Forza IoT demo repository.')
    parser.add_argument('--config', dest='config_path', default=CONFIG_FNAME,
                    help='Path of the config file, relevant to BASE_DIR.')
    args = parser.parse_args()
    
    app = ForzaIoTApp(args.base_dir, args.config_path)
    app.run()
