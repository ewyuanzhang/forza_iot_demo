import socket
import time

from forza_telemetry import TelemetryParser

UDP_IP = "" #"10.94.72.86" # "0.0.0.0" #"127.0.0.1"
UDP_PORT = 6669

sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.bind((UDP_IP, UDP_PORT))

telemetry_parser = TelemetryParser()

while True:
    data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
    print("received message:", telemetry_parser.parse(data))
    #time.sleep(1)
    #TODO(v-yuzha1): Data will be sent at 60fps and old data will be kept in buffer. If you want to use data in other fps, consider:
    # 1) Clear the buffer before reading
    # 2) Use multi-processing and a queue with one item
