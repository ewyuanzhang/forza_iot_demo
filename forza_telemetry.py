import os
import csv
import collections
import struct

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
    csv_writer = None
    
    def __init__(self,
                 output_file_name="telemetry.csv", new_output_file=False,
                 telemetry_format_fname="telemetry_format"):
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
        if self.writer is not None:
            dict_data = self.telemetry._asdict(parsed_telemetry)
            self.writer.writerow(dict_data)
        return parsed_telemetry
    
    def _get_csv_writer(self, new_output_file):
        if self.output_file_name is not None:
            if new_output_file or not os.path.isfile(self.output_file_name):
                csv_file = open(self.output_file_name, "w", newline='', encoding='utf-8')
                self.writer = csv.DictWriter(csv_file, fieldnames=list(self.telemetry._fields))
                self.writer.writeheader()
            else:
                csv_file = open(self.output_file_name, "a", newline='', encoding='utf-8')
                self.writer = csv.DictWriter(csv_file, fieldnames=self.telemetry._fields)
                
    def __exit__(self, exc_type, exc_value, traceback):
        if self.writer is not None:
            self.writer.close()
