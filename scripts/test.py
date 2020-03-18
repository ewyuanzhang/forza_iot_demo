import os
import json
import argparse
import multiprocessing as mp

from file_upload import upload_file_through_iothub

BASE_DIR = ".."
CONFIG_FNAME = "forza_config.json"

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='Run Forza IoT demo test scripts.')
    parser.add_argument('--base_dir', dest='base_dir', default=BASE_DIR,
                    help='Base directory of the Forza IoT demo repository.')
    parser.add_argument('--config', dest='config_path', default=CONFIG_FNAME,
                    help='Path of the config file, relevant to BASE_DIR.')
    args = parser.parse_args()
    
    with open(os.path.join(args.base_dir, args.config_path), "r") as f:
        forza_config = json.load(f)
    with open(os.path.join(args.base_dir, forza_config["iothub"]["conn_str_fname"]), "r") as f:
        conn_str = f.read()
    
    # Test file_upload.upload_file_through_iothub
    upload_file_name = os.path.join(BASE_DIR, "data/telemetry_20200317074355.csv")
    #upload_file_through_iothub(conn_str, path_to_file=upload_file_name, file_name=upload_file_name)
    p_upload = mp.Process(
        target=upload_file_through_iothub,
        args=(conn_str,
              upload_file_name,
              os.path.basename(upload_file_name)))
    p_upload.start()
    p_upload.join()
