import collections
import struct

class TelemetryParser():
    
    struct_format_map = {
        "s32":"i",
        "u32":"I",
        "f32":"f",
        "u16":"H",
        "s8":"c",
        "u8":"B",
    }
    struct_format = ""
    
    def __init__(self, telemetry_format_fname="telemetry_format"):
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
        
    def parse(self, udp_data):
        return self.telemetry(*struct.unpack(self.struct_format, udp_data))
