import os
import json
import shlex
import argparse
import subprocess

BASE_DIR = "."
CONFIG_FNAME = os.path.join("config", "forza_config.json")

def run_cmd(cmd_string, print_result=True):
    process = subprocess.Popen(
        shlex.split(cmd_string),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    outs, errs = process.communicate()
    if print_result:
        if outs:
            print(outs.decode())
        else:
            print(errs.decode())
    return process.returncode, outs, errs

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Run Forza IoT demo device client.')
    parser.add_argument('--base_dir', dest='base_dir', default=BASE_DIR,
                    help='Base directory of the Forza IoT demo repository.')
    parser.add_argument('--config', dest='config_path', default=CONFIG_FNAME,
                    help='Path of the config file, relevant to BASE_DIR.')
    args = parser.parse_args()
    
    with open(os.path.join(args.base_dir, args.config_path), "r") as f:
        forza_iot_config = json.load(f)["iothub"]
    
    forza_iot_location = forza_iot_config["location"]
    forza_iot_resource_group = forza_iot_config["resource_group"]
    forza_iot_iothub = forza_iot_config["name"]
    forza_iot_iothub_sku = forza_iot_config["sku"]
    forza_iot_device_id = forza_iot_config["device_id"]
    forza_iot_conn_str_path = os.path.join(args.base_dir, forza_iot_config["conn_str_fname"])

    ##################################################
    # Create IoT Hub
    ##################################################

    cmd_login = "az login"
    cmd_create_resource_group = "az group create --location {} --name {}".format(
        forza_iot_location, forza_iot_resource_group)
    cmd_create_iothub = "az iot hub create --resource-group {} --name {} --sku {}".format(
        forza_iot_resource_group, forza_iot_iothub, forza_iot_iothub_sku)

    print("Loging in...")
    run_cmd(cmd_login)
    print("Creating resource group...")
    run_cmd(cmd_create_resource_group)
    print("Creating IoT Hub...")
    run_cmd(cmd_create_iothub)

    ##################################################
    # Create device and save the connection string
    ##################################################

    #cmd_add_iot_extension = "az extension add --name azure-cli-iot-ext"
    cmd_create_device = "az iot hub device-identity create --hub-name {} --device-id {}".format(
        forza_iot_iothub, forza_iot_device_id)
    cmd_get_connection_string = "az iot hub device-identity show-connection-string --hub-name {} --device-id {}".format(
        forza_iot_iothub, forza_iot_device_id)

    #print(run_cmd(cmd_add_iot_extension))
    print("Creating device...")
    run_cmd(cmd_create_device)
    print("Getting connection string...")
    rc, outs, errs = run_cmd(cmd_get_connection_string, print_result=False)
    with open(forza_iot_conn_str_path, "w") as f:
        f.write(json.loads(outs)["connectionString"])

    ##################################################
    # Monitor IoT Hub
    # (Moved out to instructions because it requires
    # interactively update dependencies.)
    ##################################################
    # print("Monitoring IoT Hub...")
    # cmd_monitor_iothub = "az iot hub monitor-events --hub-name {} --output table".format(
    #     forza_iot_iothub)
    # run_cmd(cmd_monitor_iothub, terminate=False)
