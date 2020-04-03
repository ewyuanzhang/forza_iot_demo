import os
import json
import time
import shlex
import socket
import queue
import subprocess
import multiprocessing as mp
from functools import partial
import argparse

from azure.iot.device import IoTHubDeviceClient, Message

from forza_telemetry import TelemetryManager
from file_upload import upload_file_through_iothub

BASE_DIR = ".."
CONFIG_FNAME = os.path.join("config", "forza_config.json")

def run_cmd(cmd_string):
    return subprocess.run(
        shlex.split(cmd_string),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

def send_message(conn_str:str, q:mp.Queue):    
    # Create instance of the device client using the authentication provider
    device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)

    # Connect the device client.
    device_client.connect()
    
    message = q.get()
    while message is not None: # None is the task done indicator
        # Send a single message
        print("Sending message...")
        #device_client.send_message("This is a message that is being sent")
        iothub_msg = Message(
            json.dumps(message["data"]),
            content_encoding="UTF-8",
            content_type="application/json"
        )
        properties = message.get("custom_properties", None)
        if properties is not None:
            iothub_msg.custom_properties.update(properties)
        device_client.send_message(iothub_msg)
        print("Message successfully sent!")
        
        message = q.get()
    
    # finally, disconnect
    device_client.disconnect()
    print("Disconnected.")

def update_race_status(cur_status:int, race_pos_not_zero:bool, race_time_not_zero:bool) -> int:
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

def check_position(curr_pos:iter, start_pos:iter, threshold:float=200**2) -> bool:
    # The threshold is for the slight difference between
    # the starting position and the ending position.
    # Before a racing, your car is usually waiting at around 100 unit length
    # before the starting/ending line, which is known as the staging line.
    diff_pos = [(curr_i - start_i) ** 2 for curr_i, start_i in zip(curr_pos, start_pos)]
    diff_pos = sum(diff_pos)
    return diff_pos < threshold

if __name__ == "__main__":
    
    print("Initializing.")
    parser = argparse.ArgumentParser(description='Run Forza IoT demo device client.')
    parser.add_argument('--base_dir', dest='base_dir', default=BASE_DIR,
                    help='Base directory of the Forza IoT demo repository.')
    parser.add_argument('--config', dest='config_path', default=CONFIG_FNAME,
                    help='Path of the config file, relevant to BASE_DIR.')
    args = parser.parse_args()
    
    with open(os.path.join(args.base_dir, args.config_path), "r") as f:
        forza_config = json.load(f)
    
    recv_ip = forza_config["device"]["receive_ip"] #"" #"10.94.72.86" # "0.0.0.0" #"127.0.0.1"
    recv_port = forza_config["device"]["receive_port"]
    sock = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_DGRAM) # UDP
    sock.bind((recv_ip, recv_port))
    sock.settimeout(1)
    telemetry_manager = TelemetryManager()
    
    send_ip = forza_config["device"]["send_ip"]
    send_port = forza_config["device"]["send_port"]
    
    # Get the connection string
    # TODO(): Risk: the file is saved on the disk in plain text
    conn_str_fname = os.path.join(args.base_dir, forza_config["iothub"]["conn_str_fname"])
    conn_str = open(conn_str_fname, 'r').read()
    
    try:
        q = mp.Queue(1)
        p = mp.Process(target=send_message, args=(conn_str, q,))
        p.start()

        race_event_status = 0
        start_pos = None
        try:
            print("Ready. Waiting for messages.")
            last_put_time = time.time()
            p_upload = None
            while True:
                
                data = None
                # Set timeout to jump out of the blocked listening,
                # so that keyboard interupt can be receviced.
                while not data:
                    try:
                        data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
                    except socket.timeout:
                        pass
                # Forward the udp package to somewhere else, e.g. driving simulator.
                if send_ip:
                    sock.sendto(data, (send_ip, send_port))
                
                dict_telemetry = telemetry_manager.parse(data)
                this_put_time = time.time()

                race_event_status = update_race_status(
                    race_event_status,
                    dict_telemetry["RacePosition"] != 0,
                    dict_telemetry["CurrentRaceTime"] > 0
                )
                dict_telemetry["RaceStatus"] = race_event_status
                ##########################################################
                # TODO: Send race_event_status to iot hub / write it to the csv
                ##########################################################

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
                    if forza_config["device"].get("3_lap_race", True):
                        race_event_status = 4
                        if start_pos is None:
                            print("Start position not found.")
                            continue
                        stop_pos = (
                            prev_telemetry["PositionX"],
                            prev_telemetry["PositionY"],
                            prev_telemetry["PositionZ"]
                        )
                        if not check_position(stop_pos, start_pos):
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
                    if p_upload is not None:
                        p_upload.join()
                    upload_file_name = telemetry_manager.prepare_upload_file()
                    
                    ## Deprecated. Refresh power bi manually through service bus.
                    ## Now power bi will be automatically refreshed with event grid + logic app.
                    # msg_payload = {
                    #     "data": {"task": "refresh-power-bi"},
                    #     "custom_properties": {"value": "service-bus"}}
                    # p_upload = mp.Process(
                    #     target=upload_file_through_iothub,
                    #     args=(conn_str,
                    #           upload_file_name,
                    #           os.path.basename(upload_file_name),
                    #           partial(q.put, msg_payload)))
                    # p_upload.start()
                    p_upload = mp.Process(
                        target=upload_file_through_iothub,
                        args=(conn_str,
                              upload_file_name,
                              os.path.basename(upload_file_name))
                    )
                    p_upload.start()

                # Send telemetry data to IoT Hub no faster than 1 msg/sec
                # Note that power bi refreshing message will
                # also go through this queue.
                if this_put_time - last_put_time >= 1:
                    try:
                        q.put_nowait({"data": dict_telemetry})
                    except queue.Full:
                        continue
                    last_put_time = this_put_time

        finally:
            if p_upload is not None:
                p_upload.join()
    finally:
        q.put(None)
        p.join()
