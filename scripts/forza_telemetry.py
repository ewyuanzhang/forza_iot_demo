import os
import csv
import collections
import struct
from datetime import datetime

OUTPUT_FILE_FNAME = os.path.join("..", "data", "telemetry.csv")
TELEMETRY_FORMAT_FNAME = os.path.join("..", "config", "telemetry_format")

class TelemetryParser():
    
    struct_format_map = {
        "s32":"i",
        "u32":"I",
        "f32":"f",
        "u16":"H",
        #"s8":"c",
        "s8":"b",
        "u8":"B",
    }
    struct_format = ""
    
    def __init__(self, telemetry_format_fname:str):
        self.telemetry_format_fname = telemetry_format_fname
        self._parse_telemetry_format()
    
    def _parse_telemetry_format(self):
        telemetry_format = open(self.telemetry_format_fname, 'r').read()
        
        self.struct_format = ""
        var_names = []
        for format_str in telemetry_format.split("\n"):
            if len(format_str) == 0 or format_str.startswith("//"):
                continue
            f, var = format_str.split("//")[0].strip().split(" ")
            self.struct_format += self.struct_format_map[f]
            var_names.append(var.replace(";", ""))
        var_name = " ".join(var_names)

        self.telemetry = collections.namedtuple("telemetry", var_name)
        self.fields = self.telemetry._fields
        
    def parse(self, udp_data:str) -> dict:
        parsed_telemetry = self.telemetry(*struct.unpack(self.struct_format, udp_data))
        dict_data = self.telemetry._asdict(parsed_telemetry)
        return dict_data

class TelemetryManager():
    
    telemetry_parser = None
    output_file_name = None
    output_file_handler = None
    last_output_fname = None
    csv_writer = None
    
    def __init__(self,
                 output_file_name:str=OUTPUT_FILE_FNAME,
                 telemetry_format_fname:str=TELEMETRY_FORMAT_FNAME,
                 forced_new_file:bool=False):
        
        self.output_file_name = output_file_name
        self.telemetry_parser = TelemetryParser(telemetry_format_fname)
        self._prepare_csv_writer(forced_new_file)
    
    def parse(self, udp_data: str) -> dict:
        dict_data = self.telemetry_parser.parse(udp_data)
        return dict_data
    
    def write(self, dict_data: dict):
        self.csv_writer.writerow(dict_data)
    
    def prepare_upload_file(self) -> str:
        self.output_file_handler.close()
        self._prepare_csv_writer(forced_new_file=True)
        if self.last_output_fname is not None:
            upload_file_name = self.last_output_fname
        else:
            upload_file_name = self.output_file_name
        return upload_file_name
    
    def _prepare_csv_writer(self, forced_new_file:bool):
        output_file_exists = os.path.isfile(self.output_file_name)
        if forced_new_file or not output_file_exists:
            file_dir = os.path.split(self.output_file_name)[0]
            if not os.path.isdir(file_dir):
                os.makedirs(file_dir)
            # Rename the output csv if it exists
            if output_file_exists:
                self._generate_last_output_fname()
                os.rename(self.output_file_name, self.last_output_fname)
            self.output_file_handler = open(self.output_file_name, "w", newline='', encoding='utf-8')
            self.csv_writer = csv.DictWriter(self.output_file_handler, fieldnames=list(self.telemetry_parser.fields))
            self.csv_writer.writeheader()
        else:
            self.output_file_handler = open(self.output_file_name, "a", newline='', encoding='utf-8')
            self.csv_writer = csv.DictWriter(self.output_file_handler, fieldnames=self.telemetry_parser.fields)

    def _generate_last_output_fname(self) -> str:
        # Generate file name /path/to/telemetry_yyyymmddHHMMss.csv from /path/to/telemetry.csv
        output_fame, ext = os.path.splitext(self.output_file_name)
        self.last_output_fname = output_fame+"_"+datetime.now().strftime("%Y%m%d%H%M%S")
        if ext:
            self.last_output_fname += ext
        return self.last_output_fname
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self.output_file_handler is not None:
            self.output_file_handler.close()
