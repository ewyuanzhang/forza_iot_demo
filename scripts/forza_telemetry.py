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
    output_file_name = None
    output_file_handler = None
    old_output_name = None
    csv_writer = None
    
    def __init__(self,
                 output_file_name=OUTPUT_FILE_FNAME,
                 telemetry_format_fname=TELEMETRY_FORMAT_FNAME,
                 new_output_file=False):
        self.telemetry_format_fname = telemetry_format_fname
        self._parse_telemetry_format()
        
        self.output_file_name = output_file_name
        self._get_csv_writer(new_output_file)
    
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
        
    def parse(self, udp_data):
        parsed_telemetry = self.telemetry(*struct.unpack(self.struct_format, udp_data))
        dict_data = self.telemetry._asdict(parsed_telemetry)
        if self.writer is not None:
            self.writer.writerow(dict_data)
        return dict_data
    
    def _get_csv_writer(self, new_output_file):
        if self.output_file_name is not None:
            output_file_exists = os.path.isfile(self.output_file_name)
            if new_output_file or not output_file_exists:
                # Backup the old csv if it exists
                if output_file_exists:
                    self._generate_old_output_name()
                    os.rename(self.output_file_name, self.old_output_name)
                self.output_file_handler = open(self.output_file_name, "w", newline='', encoding='utf-8')
                self.writer = csv.DictWriter(self.output_file_handler, fieldnames=list(self.telemetry._fields))
                self.writer.writeheader()
            else:
                self.output_file_handler = open(self.output_file_name, "a", newline='', encoding='utf-8')
                self.writer = csv.DictWriter(self.output_file_handler, fieldnames=self.telemetry._fields)
    
    def _generate_old_output_name(self):
        old_output_name = self.output_file_name.split(".")
        old_output_name[-2] += "_"
        old_output_name[-2] += datetime.now().strftime("%Y%m%d%H%M%S")
        old_output_name = ".".join(old_output_name)
        self.old_output_name = old_output_name
        return old_output_name
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self.output_file_handler is not None:
            self.output_file_handler.close()
