import os
import multiprocessing as mp

from file_upload import upload_file_through_iothub

base_dir = ".."
config_path = os.path.join(base_dir, "forza_config.json")

if __name__ == "__main__":
    with open(config_path, "r") as f:
        conn_str_fname = json.load(f)["iothub"]["conn_str_fname"]
    with open(os.path.join(base_dir, conn_str_fname), "r") as f:
        conn_str = f.read()
    
    #upload_file_through_iothub(conn_str, path_to_file=upload_file_name, file_name=upload_file_name)
    p_upload = mp.Process(
        target=upload_file_through_iothub,
        args=(conn_str,
              upload_file_name,
              os.path.basename(upload_file_name)))
    p_upload.start()
    p_upload.join()
