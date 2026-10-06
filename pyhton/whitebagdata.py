# Zero out the first 8 bytes of the data, which are reserved for the header.

import struct

variable = "DD Tool OD"
value = "8.5"
unit = "in"

bytes_data = struct.pack("<II", 0x00, len(data))