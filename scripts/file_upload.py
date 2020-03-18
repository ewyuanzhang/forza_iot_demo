# Modified from https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-python-python-file-upload
import time
import sys
import iothub_client
import os
from iothub_client import IoTHubClient, IoTHubClientError, IoTHubTransportProvider, IoTHubClientResult, IoTHubError

PROTOCOL = IoTHubTransportProvider.HTTP

PATHTOFILE = os.path.join("..", "data", "telemetry.csv") # "[Full path to file]"
FILENAME = "telemetry.csv" # "[File name for storage]"

def blob_upload_conf_callback(result, user_context):
    if str(result) == 'OK':
        print ( "...file {} uploaded successfully.".format(user_context["file_name"]))
        user_context["done"] = True
    else:
        print ( "...file upload callback returned: " + str(result) )

def upload_file_through_iothub(conn_str:str, path_to_file:str=PATHTOFILE, file_name:str=FILENAME):
    try:
        print ( "Upload file through IoT Hub." )

        client = IoTHubClient(conn_str, PROTOCOL)

        f = open(path_to_file, "r")
        content = f.read()

        user_context = {
            "file_name": path_to_file,
            "done": False
        }
        client.upload_blob_async(file_name, content, len(content), blob_upload_conf_callback, user_context)

        print ( "" )
        print ( "File upload initiated..." )

        while True:
            if user_context["done"]:
                return
            time.sleep(1)

    except IoTHubError as iothub_error:
        print ( "Unexpected error %s from IoTHub" % iothub_error )
        return
    except KeyboardInterrupt:
        print ( "IoTHubClient stopped" )
    except:
        print ( "generic error" )
