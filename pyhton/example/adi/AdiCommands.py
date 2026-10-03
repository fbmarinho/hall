from __future__ import annotations
import copy
import datetime
import inspect
import math
import re
import struct
import sys
from typing import TYPE_CHECKING
from urllib import response
import adi.AdiClient
import adi.AdiEnums
import adi.AdiDefinitions

if TYPE_CHECKING:
    import adi.AdiClientToLocal

def fromArrayToUTF8(buf: bytes | bytearray, start: int=0, end: int=None, encoding: str = "cp1252") -> str:
    # Maybe the default encoding is "latin-1" (not "cp1252")

    # Slice the segment once; this is O(n) in C and very fast.
    seg = buf[start:end]
    # Trim at first NUL if present.
    z = seg.find(0)
    if z != -1:
        seg = seg[:z]
    # Decode using a native codec. cp1252 is usually right for legacy Windows.
    # Use 'replace' so a rare bad byte doesn't crash the whole parse.
    return seg.decode(encoding, errors="replace")

def fromArrayToUTF8_old(arr, start=0, end=None):
    if end is None:
        end = len(arr)
    size_needed = 0
    for i in range(start, end):
        if arr[i] > 0x7f:
            size_needed += 2
        elif arr[i] == 0:
            break
        else:
            size_needed += 1
    buffer = bytearray(size_needed)

    ix = 0
    for i in range(start, end):
        if arr[i] > 0x7f:
            buffer[ix] = 0xc2
            ix += 1
            buffer[ix] = arr[i]
            ix += 1
        elif arr[i] == 0:
            break
        else:
            buffer[ix] = arr[i]
            ix += 1
    
    result = ""
    try:
        result = buffer.decode("utf-8")
    except:
        try:
            text = ""
            for i in range(start, end):
                if arr[i] == 0:
                    break
                text += chr(arr[i])
            result = text
        except: pass
    return result

def toUTF8Array(str):
    if str is None: return bytes()
    bytes_str = bytes(str, "utf-8")
    # return bytes_str
    
    utf8 = []
    for i in range(len(bytes_str)):
        charcode = bytes_str[i]
        if charcode == 0xc2: continue
        utf8.append(charcode)
    # utf8 = []
    # for i in range(len(bytes_str)):
    #     charcode = bytes_str[i]
    #     if charcode < 0x80:
    #         utf8.append(charcode)
    #     elif charcode < 0x800:
    #         utf8.append(0xc0 | (charcode >> 6))
    #         utf8.append(0x80 | (charcode & 0x3f))
    #     elif charcode < 0xd800 or charcode >= 0xe000:
    #         utf8.append(0xe0 | (charcode >> 12))
    #         utf8.append(0x80 | ((charcode >> 6) & 0x3f))
    #         utf8.append(0x80 | (charcode & 0x3f))
    #     else:
    #         # surrogate pair
    #         i += 1
    #         # UTF-16 encodes 0x10000-0x10FFFF by
    #         # subtracting 0x10000 and splitting the
    #         # 20 bits of 0x0-0xFFFFF into two halves
    #         charcode = 0x10000 + (((charcode & 0x3ff) << 10)
    #                               | (bytes_str[i] & 0x3ff))
    #         utf8.append(0xf0 | (charcode >> 18))
    #         utf8.append(0x80 | ((charcode >> 12) & 0x3f))
    #         utf8.append(0x80 | ((charcode >> 6) & 0x3f))
    #         utf8.append(0x80 | (charcode & 0x3f))
    return bytes(utf8)

def beautifyBytes(arr, show_per_line=16, show_per_separator=8):
    str_line = "00000    "
    str_chars = ""
    for i in range(len(arr)):
        n = arr[i]
        str_number = chr(n).rjust(1) if 0x20 <= n <= 0x7e else '\u00b7'
        if n == 0: str_line += f"\033[1;30;40m{hex(n)[2:].rjust(2, '0')}\033[0m "
        elif (n == 0x78 and 0 <= i <= len(arr) - 4 and list(arr[i + 0:i + 4]) == [0x78, 0x56, 0x34, 0x12]) or \
            (n == 0x56 and 1 <= i <= len(arr) - 3 and list(arr[i - 1:i + 3]) == [0x78, 0x56, 0x34, 0x12]) or \
            (n == 0x34 and 2 <= i <= len(arr) - 2 and list(arr[i - 2:i + 2]) == [0x78, 0x56, 0x34, 0x12]) or \
            (n == 0x12 and 3 <= i <= len(arr) - 1 and list(arr[i - 3:i + 1]) == [0x78, 0x56, 0x34, 0x12]):
            str_line += f"\033[1;35;40m{hex(n)[2:].rjust(2, '0')}\033[0m "
        else: str_line += f"{hex(n)[2:].rjust(2, '0')} "
        str_chars += f"{str_number}"
        if i % show_per_separator == 7 and i % show_per_line != 15:
            str_line += "  "
            str_chars += " "
        if i % show_per_line == 15 or i == len(arr) - 1:
            spaces_extra = (show_per_line - (i % show_per_line) - 1) * 3 + (0 if i % show_per_line > show_per_separator else 2)
            print(str_line + (" " * spaces_extra) + "    " + str_chars)
            str_line = f"{hex(int(math.floor((i + 1) / show_per_line)))[2:].rjust(4, '0')}0    "
            str_chars = ""

class AdiCommands:
    DEBUG_ON = False

    @staticmethod
    def IdentifyCommandFromHeader(client:adi.AdiClient.AdiClient=None, header:adi.AdiDefinitions.MessageHeader=None, data:bytearray=None):
        ignore_codes = [0x2049, 0x2006, 0x2013, 0x2015] #[0x1002, 0x2001, 0x2006, 0x2007, 0x2009, 0x2015, 0x2045, 0x2049, 0x205e, 0x9000, 0x9001, 0x9002, 0x9008, 0xa003, 0xa007]
        code = header.command
        obj:AdiCommands.AdiCommand
        for name, obj in inspect.getmembers(AdiCommands, inspect.isclass):
            attr = getattr(obj, "GetCode", None)
            if attr is not None and obj.GetCode() == code:
                obj_result = obj.CreateCommandFromBinaryData(client, header, data)
                if AdiCommands.DEBUG_ON and not code in ignore_codes:
                    formated_time = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    str = f"== {formated_time} - {hex(code)} - {name}"
                    desc_fn = getattr(obj, "GetDetails", None)
                    if desc_fn is not None:
                        desc = obj_result.GetDetails()
                        if desc is not None and len(desc) > 0: str += " - " + desc
                    print(str)
                
                return obj_result
        # raise Exception(f"Command {hex(code)} not found!")
        return AdiCommands.AdiCommand(code=code, client=client, header=header, data=data)

    @staticmethod
    def CurrentTimezoneSecsDiff():
        return datetime.datetime.now(datetime.timezone.utc).astimezone().utcoffset().total_seconds()

    @staticmethod
    def DateFromInsiteNumber(dt:float):
        result = None
        try:
            now_time = datetime.datetime.now().astimezone()
            dt = datetime.datetime.fromtimestamp(dt, tz=datetime.timezone.utc)
            # result = dt - datetime.timedelta(seconds=AdiCommands.CurrentTimezoneSecsDiff())
            result = datetime.datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, now_time.tzinfo)
            
            # utc_result = result - datetime.timedelta(seconds=AdiCommands.CurrentTimezoneSecsDiff())
            # result_tz = datetime.datetime(utc_result.year, utc_result.month, utc_result.day, utc_result.hour, utc_result.minute, utc_result.second, utc_result.microsecond, datetime.timezone.utc)
            # result = dt
        except Exception as ex:
            pass
        return result

    @staticmethod
    def DateToInsiteNumber(dt:datetime):
        tzname = dt.tzname()
        min_dt = datetime.datetime(1970, 1, 1, 0, 0, 0)
        if dt == min_dt: return 0
        if tzname is None and dt.astimezone() is not None and dt.astimezone().tzname() is not None:
            tzname = dt.astimezone().tzname()
        # dt_local = dt.astimezone() if tzname is not None else dt
        dt_local = dt if tzname is not None else dt
        if tzname is None or tzname.lower() == 'utf':
            # add the local timezone offset to the datetime
            dt_local = dt_local + datetime.timedelta(seconds=AdiCommands.CurrentTimezoneSecsDiff())

        dt_utc = datetime.datetime(dt_local.year, dt_local.month, dt_local.day, dt_local.hour, dt_local.minute, dt_local.second, dt_local.microsecond, datetime.timezone.utc)
        # diff = dt.timestamp() - dt_utc.timestamp()
        number = dt_utc.timestamp()
        return number

    @staticmethod
    def BuildDataToSendFromLines(desired_variables, dataset_variables, lines_to_write):
        try:
            data_bytes, blob_bytes, bit_test_bytes = b'', b'', b''
            for line in lines_to_write:
                # Reorganizing the data based on the expected order by the client
                line_to_send = []
                for v in desired_variables:
                    variable_in_dataset = next((variable for variable in dataset_variables if variable["Variable"].name == v["Variable"].name), None)
                    if variable_in_dataset is None:
                        line_to_send.append(None)
                    else:
                        data_value = line[dataset_variables.index(variable_in_dataset)]
                        # If unit options are different, perform conversion
                        if v["UnitOption"].id != variable_in_dataset["UnitOption"].id:
                            try:
                                ci = adi.AdiDefinitions.ConversionInfo(v["UnitOption"].function_type, v["UnitOption"].arg1, v["UnitOption"].arg2)
                                basic_value = AdiCommands.ConvertValueToBasicType(variable_in_dataset, data_value)
                                data_value = AdiCommands.ApplyConversionInfoToValue(ci, basic_value)
                                data_value = variable_in_dataset["UnitOption"].ConvertValueTo(data_value, v["UnitOption"])
                            except Exception as ex:
                                data_value = None
                        line_to_send.append(data_value)
                line_bytes = AdiCommands.BuildDataForBuffer(desired_variables, line_to_send)
                data_bytes += line_bytes["Data"]
                blob_bytes += line_bytes["Blob"]
                bit_test_bytes += line_bytes["BitTest"]
            return data_bytes, blob_bytes, bit_test_bytes
        except Exception as ex:
            raise Exception(f"Error building data to send: {str(ex)}")

    @staticmethod
    def BuildBytesForVariableValue(variable, value, blob_content_size=0):
        content_value = None
        content_data = b''
        blob_data = b''
        values_present = [value is not None]
        
        # Otherwise, evaluate type of data and read accordingly
        format_type = variable.GetStorageType()
        if format_type == adi.AdiEnums.StorageType.NUMBER:
            content_value = 0 if value is None else value
            format_data = "b" if variable.size == 1 else "h" if variable.size == 2 else "i" if variable.size == 4 else "q"
            content_data += struct.pack(f"<{format_data}", int(content_value))
        elif format_type == adi.AdiEnums.StorageType.NUMBER_UNSIGNED:
            content_value = 0 if value is None else value
            if value is not None and variable.special & adi.AdiEnums.VariableSpecialHandlings.OptionList.value != 0:
                if not isinstance(content_value, int) and variable.options_list is not None and len(variable.options_list.options) > 0 and content_value in variable.options_list.options:
                    content_value = variable.options_list.options.index(content_value)
            format_data = "B" if variable.size == 1 else "H" if variable.size == 2 else "I" if variable.size == 4 else "Q"
            content_data += struct.pack(f"<{format_data}", int(content_value))
        elif format_type == adi.AdiEnums.StorageType.NUMBER_DECIMAL:
            content_value = 0 if value is None else value
            if variable.size == 4: content_data += struct.pack("<f", content_value)
            elif variable.size == 8:
                if variable.special & adi.AdiEnums.VariableSpecialHandlings.DateFormat.value != 0:
                    if isinstance(content_value, datetime.datetime):
                        content_value = AdiCommands.DateToInsiteNumber(content_value)
                    elif isinstance(content_value, float) or isinstance(content_value, int):
                        pass
                    elif isinstance(content_value, str):
                        try:
                            dt_parsed = datetime.datetime.fromisoformat(content_value)
                            content_value = AdiCommands.DateToInsiteNumber(dt_parsed)
                        except:
                            content_value = 0
                            values_present[0] = False
                    else:
                        content_value = 0
                        values_present[0] = False
                content_data += struct.pack("<d", float(content_value))
        elif format_type == adi.AdiEnums.StorageType.TEXT:
            bytes_txt = b'' if value is None else toUTF8Array(value)
            length_text = variable.size    # Fixed size for this type
            content_data += struct.pack(f"<{length_text}s", bytes_txt)
        elif format_type == adi.AdiEnums.StorageType.TEXT_LONG:
            bytes_txt = b'' if value is None else toUTF8Array(value)
            length_text = len(bytes_txt) + 1
            
            # Place the offset within blob data for this data as the value
            format_data = "b" if variable.size == 1 else "h" if variable.size == 2 else "i" if variable.size == 4 else "q"
            content_data += struct.pack(f"<{format_data}", blob_content_size)
            
            # Add data into the blob area
            blob_data += struct.pack(f"<{length_text}s", bytes_txt)
        elif format_type == adi.AdiEnums.StorageType.BINARY_LONG:
            content_value = 0 if value is None else value

            # The value from this element will be the offset from
            # the BLOB area, after all values from normal variables
            # and before the bit test area

            # Place the offset within blob data for this data as the value
            format_data = "b" if variable.size == 1 else "h" if variable.size == 2 else "i" if variable.size == 4 else "q"
            content_data += struct.pack(f"<{format_data}", blob_content_size)

            binary_data = bytearray()
            if value is None:
                pass
            elif variable.special & adi.AdiEnums.VariableSpecialHandlings.WaveForm.value != 0:
                wave_data = value
                binary_data += struct.pack("<fHH", wave_data["Interval"], 0, wave_data["NumberOfElements"])
                # And finally... The data!
                if wave_data["NumberOfElements"] > 0:
                    binary_data += struct.pack(f"<{''.join(['f'] * wave_data['NumberOfElements'])}", *wave_data["Data"])
            elif variable.special & adi.AdiEnums.VariableSpecialHandlings.VectorData.value != 0:
                bin_data = value
                vt = bin_data["VectorType"]
                if vt is None: raise Exception(f"Vector attributes for variable {variable.name} not informed!")
                format_data = "I"
                # bin_value = bin_data["Data"][k]
                if vt == adi.AdiEnums.VectorVarType.UnsignedByteId:
                    format_data = "B"
                    # bin_value = int(bin_value)
                elif vt == adi.AdiEnums.VectorVarType.UnsignedShortId:
                    format_data = "H"
                    # bin_value = int(bin_value)
                elif vt == adi.AdiEnums.VectorVarType.UnsignedIntId:
                    format_data = "I"
                    # bin_value = int(bin_value)
                elif vt == adi.AdiEnums.VectorVarType.ByteId:
                    format_data = "b"
                    # bin_value = int(bin_value)
                elif vt == adi.AdiEnums.VectorVarType.ShortId:
                    format_data = "h"
                    # bin_value = int(bin_value)
                elif vt == adi.AdiEnums.VectorVarType.IntId:
                    format_data = "i"
                    # bin_value = int(bin_value)
                elif vt == adi.AdiEnums.VectorVarType.FloatId:
                    format_data = "f"
                    # bin_value = float(bin_value)
                elif vt == adi.AdiEnums.VectorVarType.DoubleId:
                    format_data = "d"
                    # bin_value = float(bin_value)
                else:
                    format_data = "I"
                    # bin_value = int(bin_value)
                # First comes the number of bins which will be written
                binary_data += struct.pack("<H", bin_data["NumberOfBins"])
                number_bytes_bit_test_bins = math.ceil(float(bin_data["NumberOfBins"]) / 8.0)
                # Now comes the bit test area
                ix_bit_test_bins = 2
                binary_data += bytearray([0] * number_bytes_bit_test_bins)
                for k in range(bin_data["NumberOfBins"]):
                    # Removing elements marked as missing
                    bin_value = bin_data["Data"][k]
                    value_present = bin_value is not None
                    if value_present:
                        binary_data[ix_bit_test_bins + math.floor(k / 8.0)] |= 1 << (k % 8)
                        try: binary_data += struct.pack(f"<{format_data}", bin_value)
                        except: print(f"Incompatible data on index {k} of variable \"{variable.name}\"")
            else:
                binary_data += value
                
            # To the blob we will add first the total length, then the data
            blob_data += struct.pack(f"<I", len(binary_data))
            blob_data += binary_data
        elif format_type == format_type and format_type in [adi.AdiEnums.StorageType.I1_ARRAY, adi.AdiEnums.StorageType.I2_ARRAY, adi.AdiEnums.StorageType.I4_ARRAY]:
            format_data = "b" if variable.size == 1 else "h" if variable.size == 2 else "i" if variable.size == 4 else "q"
            value_arr = value if value is not None else [None] * variable.number_of_elements
            values_present.pop()
            for k in range(variable.number_of_elements):
                values_present.append(value_arr[k] is not None)
                content_value = 0 if value_arr[k] else value_arr[k]
                try: content_data += struct.pack(f"<{format_data}", content_value)
                except: raise Exception(f"Data type incompatible at index {k} of variable \"{variable.name}\"")
        elif format_type == format_type and format_type in [adi.AdiEnums.StorageType.U1_ARRAY, adi.AdiEnums.StorageType.U2_ARRAY, adi.AdiEnums.StorageType.U4_ARRAY]:
            format_data = "B" if variable.size == 1 else "H" if variable.size == 2 else "I" if variable.size == 4 else "Q"
            value_arr = value if value is not None else [None] * variable.number_of_elements
            values_present.pop()
            for k in range(variable.number_of_elements):
                values_present.append(value_arr[k] is not None)
                content_value = 0 if value_arr[k] is None else value_arr[k]
                try: content_data += struct.pack(f"<{format_data}", content_value)
                except: raise Exception(f"Data type incompatible at index {k} of variable \"{variable.name}\"")

        return [values_present, content_data, blob_data]

    @staticmethod
    def BuildDataForBuffer(variables_list, data):
        values_present = []
        
        bit_test_data = b''
        blob_data = b''
        content_data = b''
        
        for j in range(len(variables_list)):
            v = variables_list[j]["Variable"]
            
            # Adjusting the content data based on next offset
            # Ex: if content now is [0 0] and offset is 4, then adding 2 more zeros
            if v.offset < len(content_data): raise Exception(f"Offset for variable {v.name} overlaps current array.")
            if v.offset > len(content_data): content_data += bytearray(v.offset - len(content_data))
            
            # Getting the bytes for the current data
            # [0] - Array of "values_present" for current value
            #       (if variable is array, then it will be multiple elements)
            # [1] - Content in bytes for the value
            # [2] - If this variable requires to add data to BLOB area, then
            #       blob data will be here
            result_data = AdiCommands.BuildBytesForVariableValue(v, data[j], len(blob_data))
            
            # Adding to the bit test array if the current value is present
            values_present += result_data[0]
            content_data += result_data[1]
            blob_data += result_data[2]

        number_bytes_bit_test_bins = math.ceil(float(len(values_present)) / 8.0)
        bit_test_data = bytearray(number_bytes_bit_test_bins)
        for k in range(len(values_present)):
            if values_present[k]: bit_test_data[math.floor(k / 8.0)] |= 1 << (k % 8)
        
        if len(content_data) > 0 and len(content_data) % 4 != 0:
            content_data += b'\x00' * (4 - (len(content_data) % 4))
        if len(blob_data) > 0 and len(blob_data) % 4 != 0:
            blob_data += b'\x00' * (4 - (len(blob_data) % 4))

        return { "Data": content_data, "Blob": blob_data, "BitTest": bit_test_data, "NumberValues": len(values_present) }

    @staticmethod
    def ExtractDataFromBuffer(buffer, ix_record, length_record, ix_bit_fields_test, variables_list, number_values):
        # If a variable is an array of 10, then just this
        # variable has 10 values, so number_values represents
        # every single value returned and we need to check its
        # presence on the bit_test area
        
        number_bytes_bit_test = math.ceil(float(number_values) / 8.0)
        result_record = [None] * len(variables_list)
        last_var = None if len(variables_list) == 0 else variables_list[-1]["Variable"]
        ix_blob = 0 if last_var is None else last_var.offset + last_var.size * last_var.number_of_elements
        ix_blob += 0 if ix_blob % 4 == 0 else 4 - (ix_blob % 4)
        ix_blob += ix_record
        
        ix_value = 0

        # Checking if record length or bit fields are within valid range in the buffer
        if ix_record + length_record > len(buffer) or ix_bit_fields_test + number_bytes_bit_test > len(buffer):
            return result_record

        for j in range(len(variables_list)):
            v = variables_list[j]["Variable"]
            field_present = buffer[ix_bit_fields_test + math.floor(ix_value / 8.0)] & (1 << (ix_value % 8)) != 0
            ix_value += 1
            ix_data = ix_record + v.offset

            # Otherwise, evaluate type of data and read accordingly
            format_type = v.GetStorageType()
            if format_type == adi.AdiEnums.StorageType.NUMBER:
                if not field_present: continue
                
                format_data = "b" if v.size == 1 else "h" if v.size == 2 else "i" if v.size == 4 else "q"
                [result_record[j]] = struct.unpack_from(f"<{format_data}", buffer, ix_data)
            elif format_type == adi.AdiEnums.StorageType.NUMBER_UNSIGNED:
                if not field_present: continue
                
                format_data = "B" if v.size == 1 else "H" if v.size == 2 else "I" if v.size == 4 else "Q"
                [value] = struct.unpack_from(f"<{format_data}", buffer, ix_data)
                if v.special & adi.AdiEnums.VariableSpecialHandlings.OptionList.value != 0 and v.options_list is not None and len(v.options_list.options) > value:
                    result_record[j] = v.options_list.options[value]
                else: result_record[j] = value
            elif format_type == adi.AdiEnums.StorageType.NUMBER_DECIMAL:
                if not field_present: continue
                
                if v.size == 4:
                    [result_record[j]] = struct.unpack_from(f"<f", buffer, ix_data)
                elif v.size == 8:
                    [value] = struct.unpack_from(f"<d", buffer, ix_data)
                    if v.special & adi.AdiEnums.VariableSpecialHandlings.DateFormat.value != 0:
                        dt = AdiCommands.DateFromInsiteNumber(value)
                        result_record[j] = dt
                    else: result_record[j] = value
            elif format_type == adi.AdiEnums.StorageType.TEXT:
                if not field_present: continue
                
                length_text = v.size    # fixed size
                result_record[j] = fromArrayToUTF8(buffer, ix_data, ix_data + length_text)
            elif format_type == adi.AdiEnums.StorageType.TEXT_LONG:
                if not field_present: continue
                
                format_data = "b" if v.size == 1 else "h" if v.size == 2 else "i" if v.size == 4 else "q"
                [offset_to_data] = struct.unpack_from(f"<{format_data}", buffer, ix_data)
                ix_start = ix_blob + offset_to_data
                ix_end = ix_record + length_record
                result_record[j] = fromArrayToUTF8(buffer, ix_start, ix_end)
            elif format_type == adi.AdiEnums.StorageType.BINARY_LONG:
                if not field_present: continue
                # The value from this element will be the offset from
                # the BLOB area, after all values from normal variables
                # and before the bit test area
                [blob_offset] = struct.unpack_from("<I", buffer, ix_data)
                ix = ix_blob + blob_offset
                [data_length] = struct.unpack_from("<I", buffer, ix)
                ix += 4

                if v.special & adi.AdiEnums.VariableSpecialHandlings.WaveForm.value != 0:
                    interval, unknown, number_elements = struct.unpack_from("<fHH", buffer, ix)
                    if unknown != 0: print(f"wave unknown={unknown}")
                    ix += 8
                    # And finally... The data!
                    arr_data = [None] * number_elements
                    min_value = None
                    max_value = None
                    for k in range(number_elements):
                        try:
                            [v_element] = struct.unpack_from(f"<f", buffer, ix + k * 4)
                            if min_value is None or v_element < min_value: min_value = v_element
                            if max_value is None or v_element > max_value: max_value = v_element
                            arr_data[k] = v_element
                        except Exception as ex:
                            print(ex)
                    ix += 4 * number_elements
                    result_record[j] = { "NumberOfElements": number_elements, "Interval": interval, "MinValue": min_value, "MaxValue": max_value, "Data": arr_data }
                elif v.special & adi.AdiEnums.VariableSpecialHandlings.VectorData.value != 0:
                    vt = v.vector_var_type
                    if vt is None: raise Exception("Vector attributes not loaded!")
                    format_data = "I"
                    size_element = 4
                    if vt == adi.AdiEnums.VectorVarType.UnsignedByteId:
                        format_data = "B"
                        size_element = 1
                    elif vt == adi.AdiEnums.VectorVarType.UnsignedShortId: 
                        format_data = "H"
                        size_element = 2
                    elif vt == adi.AdiEnums.VectorVarType.UnsignedIntId: 
                        format_data = "I"
                        size_element = 4
                    elif vt == adi.AdiEnums.VectorVarType.ByteId: 
                        format_data = "b"
                        size_element = 1
                    elif vt == adi.AdiEnums.VectorVarType.ShortId: 
                        format_data = "h"
                        size_element = 2
                    elif vt == adi.AdiEnums.VectorVarType.IntId: 
                        format_data = "i"
                        size_element = 4
                    elif vt == adi.AdiEnums.VectorVarType.FloatId: 
                        format_data = "f"
                        size_element = 4
                    elif vt == adi.AdiEnums.VectorVarType.DoubleId: 
                        format_data = "d"
                        size_element = 8
                    else:
                        format_data = "I"
                        size_element = 4
                    # Now, already on the location inside the BLOB area,
                    # the first value which comes is the size in bytes of
                    # the full variable data (including bit test area),
                    # followed by the number of bins which will be read
                    [number_bins] = struct.unpack_from("<H", buffer, ix)
                    ix += 2
                    number_bytes_bit_test_bins = math.ceil(float(number_bins) / 8.0)
                    # Now comes the bit test area
                    ix_bit_test_bins = ix
                    ix += number_bytes_bit_test_bins
                    # And finally... The data!
                    arr_data = [None] * number_bins
                    min_value = None
                    max_value = None
                    for k in range(number_bins):
                        # Removing elements marked as missing
                        value_present = buffer[ix_bit_test_bins + math.floor(k / 8.0)] & (1 << (k % 8)) != 0
                        if value_present:
                            try:
                                [v_bin] = struct.unpack_from(f"<{format_data}", buffer, ix)
                                if min_value is None or v_bin < min_value: min_value = v_bin
                                if max_value is None or v_bin > max_value: max_value = v_bin
                                arr_data[k] = v_bin
                            except Exception as ex:
                                print(ex)
                        ix += size_element
                    result_record[j] = { "NumberOfBins": number_bins, "BinStart": v.vector_bin_start, "BinEnd": v.vector_bin_end, "BinMin": min_value, "BinMax": max_value, "VectorType": vt, "XAxisUnit": v.vector_unit_type, "YAxisUnit": v.unit_type, "Data": arr_data }
                else:
                    data = buffer[ix_data:ix_data + data_length]
                    result_record[j] = data
            elif format_type == format_type and format_type in [adi.AdiEnums.StorageType.I1_ARRAY, adi.AdiEnums.StorageType.I2_ARRAY, adi.AdiEnums.StorageType.I4_ARRAY]:
                format_data = "b" if v.size == 1 else "h" if v.size == 2 else "i" if v.size == 4 else "q"
                value_arr = [None] * v.number_of_elements
                ix_value -= 1
                for k in range(v.number_of_elements):
                    field_present = buffer[ix_bit_fields_test + math.floor(ix_value / 8.0)] & (1 << (ix_value % 8)) != 0
                    if field_present: value_arr[k] = struct.unpack_from(f"<{format_data}", buffer, v.offset + ix_record + k * v.size)
                    ix_value += 1
                result_record[j] = value_arr
            elif format_type == format_type and format_type in [adi.AdiEnums.StorageType.U1_ARRAY, adi.AdiEnums.StorageType.U2_ARRAY, adi.AdiEnums.StorageType.U4_ARRAY]:
                format_data = "B" if v.size == 1 else "H" if v.size == 2 else "I" if v.size == 4 else "Q"
                value_arr = [None] * v.number_of_elements
                ix_value -= 1
                for k in range(v.number_of_elements):
                    field_present = buffer[ix_bit_fields_test + math.floor(ix_value / 8.0)] & (1 << (ix_value % 8)) != 0
                    if field_present: [value_arr[k]] = struct.unpack_from(f"<{format_data}", buffer, v.offset + ix_record + k * v.size)
                    ix_value += 1
                result_record[j] = value_arr
    
        return result_record

    @staticmethod
    def ApplyConversionInfoToValue(ci, value, read_from_db=True):
        if value is None: return value
        
        # Funtion types:
        #   0:   no conversion
        #   1:   Alt = Std * Arg1
        #   2:   Alt = Std + Arg1
        #   3:   Alt = Std * Arg1 + Arg2
        if read_from_db:
            if ci.function_type == 0: return value
            elif ci.function_type == 1: return value * ci.arg1
            elif ci.function_type == 2: return value + ci.arg1
            elif ci.function_type == 3: return value * ci.arg1 + ci.arg2
        else:
            if ci.function_type == 0: return value
            elif ci.function_type == 1: return value / ci.arg1
            elif ci.function_type == 2: return value - ci.arg1
            elif ci.function_type == 3: return (value - ci.arg2) / ci.arg1

    @staticmethod
    def ConvertValueToBasicType(variable, value):
        if value is None: return None

        # Otherwise, evaluate type of data and read accordingly
        content_value = None
        format_type = variable.GetStorageType()
        if format_type == adi.AdiEnums.StorageType.NUMBER:
            content_value = int(value)
        elif format_type == adi.AdiEnums.StorageType.NUMBER_UNSIGNED:
            if variable.special & adi.AdiEnums.VariableSpecialHandlings.OptionList.value != 0 and variable.options_list is not None:
                if value in variable.options_list.options:
                    content_value = variable.options_list.options.index(value)
                elif (isinstance(value, int) or isinstance(value, float)) and value.is_integer() and len(variable.options_list.options) > int(value):
                    content_value = int(value)
                else: content_value = 0
            else: content_value = int(value)
        elif format_type == adi.AdiEnums.StorageType.NUMBER_DECIMAL:
            if variable.size == 4: content_value = float(value)
            elif variable.size == 8:
                if variable.special & adi.AdiEnums.VariableSpecialHandlings.DateFormat.value != 0:
                    # content_value = AdiCommands.DateToInsiteNumber(value)
                    content_value = value

                    if isinstance(content_value, datetime.datetime):
                        content_value = AdiCommands.DateToInsiteNumber(content_value)
                    elif isinstance(content_value, float) or isinstance(content_value, int):
                        pass
                    elif isinstance(content_value, str):
                        try:
                            dt_parsed = datetime.datetime.fromisoformat(content_value)
                            content_value = AdiCommands.DateToInsiteNumber(dt_parsed)
                        except:
                            content_value = 0
                    else:
                        content_value = 0

                else: content_value = float(value)
        elif format_type == adi.AdiEnums.StorageType.TEXT:
            content_value = str(value)
        elif format_type == adi.AdiEnums.StorageType.TEXT_LONG:
            content_value = str(value)
        elif format_type == adi.AdiEnums.StorageType.BINARY_LONG:
            content_value = value
        elif format_type == format_type and format_type in [adi.AdiEnums.StorageType.I1_ARRAY, adi.AdiEnums.StorageType.I2_ARRAY, adi.AdiEnums.StorageType.I4_ARRAY]:
            content_value = value if value is not None else [None] * variable.number_of_elements
            for k in range(variable.number_of_elements):
                content_value[k] = None if value[k] is None else int(value[k])
        elif format_type == format_type and format_type in [adi.AdiEnums.StorageType.U1_ARRAY, adi.AdiEnums.StorageType.U2_ARRAY, adi.AdiEnums.StorageType.U4_ARRAY]:
            content_value = value if value is not None else [None] * variable.number_of_elements
            for k in range(variable.number_of_elements):
                content_value[k] = None if value[k] is None else int(value[k])
        return content_value

    class AdiCommand:
        @staticmethod
        def GetCode(): return 0x0000
        
        @staticmethod
        def CreateCommandFromBinaryData(client:adi.AdiClient.AdiClient=None, header:adi.AdiDefinitions.MessageHeader=None, data:bytearray=None):
            return None

        def __init__(self, name="CMD_UNKNOWN", code=0x00, output_format=adi.AdiEnums.OutputFormat.DEFAULT, response_expected=True, client=None, header=None, data=None):
            self.response_expected = response_expected
            self.name = name
            self.code = code
            self.output_format = output_format
            self.is_valid = False
            self.client:adi.AdiClient.AdiClient = client
            self.client_local:adi.AdiClientToLocal.AdiClientToLocal = None if type(client).__name__ != "AdiClientToLocal" else client
            self.header:adi.AdiDefinitions.MessageHeader = header
            self.data:bytearray = data

        def IsValid(self):
            return self.is_valid

        async def ExecuteCommand(self):
            return  # Do nothing in a default command

        def ProcessReceivedCommand(self):
            return

        async def GetResponseBytes(self) -> adi.AdiDefinitions.AdiResponse:
            if self.response_expected: return adi.AdiDefinitions.AdiResponse(param=0x01)
            else: return None

        def BuildCommandBinaryData(self):
            bytes_header = b'' if self.header is None else self.header.BuildCommandBinaryData()
            bytes_data = b'' if self.data is None else self.data
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, _):
            return {"Success": True}

    # 0x1001 - CMD_SHUTDOWN
    class Shutdown(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x1001

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.Shutdown(client)

        def __init__(self, client=None):
            super().__init__(name="CMD_SHUTDOWN", code=self.GetCode(), client=client, response_expected=False)
            self.is_valid = True

        async def ExecuteCommand(self):
            await self.client.ChangeConnectionStatus(adi.AdiEnums.ConnectionState.CLOSING)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

    # 0x1002 - CMD_HANDSHAKE
    class Handshake(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x1002

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.Handshake(client, param_id=header.param)

        def __init__(self, client=None, param_id=0):
            super().__init__(name="CMD_HANDSHAKE", code=self.GetCode(
            ), client=client)
            self.param_id = param_id
            self.is_valid = True

        async def GetResponseBytes(self, result=None):
            return adi.AdiDefinitions.AdiResponse(value=0x01 if not self.is_valid else 0x0b)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.param_id)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            return {"Success": response.value == 0x0b}

    # 0x100c - CMD_DELETE_DATASET
    class DeleteDataSet(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x100c

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            fields_present = 0
            well = None
            run_number = None
            record = None
            description = None
            if header.length == 68:
                fields_present, run_number, record, well, description = struct.unpack_from("<HH16s16s32s", data, 16)
                well = None if fields_present & adi.AdiEnums.QueryFilterModes.WELL.value == 0 else fromArrayToUTF8(well)
                run_number = None if fields_present & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value) == 0 else fromArrayToUTF8(run_number)
                record = None if fields_present & adi.AdiEnums.QueryFilterModes.RECORD.value == 0 else fromArrayToUTF8(record)
                description = None if fields_present & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value == 0 else fromArrayToUTF8(description)
                
            return AdiCommands.DeleteDataSet(client=client, fields_present=fields_present, well=well, run_number=run_number, record=record, description=description)

        def __init__(self, client=None, fields_present = 0x1d, well=None, run_number=None, record=None, description=None):
            super().__init__(name="CMD_DELETE_DATASET", code=self.GetCode(), client=client)
            self.fields_present = fields_present
            self.well = None if fields_present & adi.AdiEnums.QueryFilterModes.WELL.value == 0 else well
            self.run_number = None if fields_present & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value) == 0 else run_number
            self.record = None if fields_present & adi.AdiEnums.QueryFilterModes.RECORD.value == 0 else record
            self.description = None if fields_present & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value == 0 else description
            self.is_valid = self.well is not None and self.run_number is not None and self.record is not None and self.description is not None

        async def GetLocalResult(self):
            success = await self.client_local.server.DatasetDelete(self.well, self.run_number, self.record, self.description)
            return { "Success": success }

        async def GetResponseBytes(self, result=None):
            if self.is_valid and result is None: result = await self.GetLocalResult()
            if not self.is_valid or not result["Success"]:
                return adi.AdiDefinitions.AdiResponse(param=0x01)
            else: return adi.AdiDefinitions.AdiResponse()

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<HH16s16s32s", self.fields_present, self.run_number, toUTF8Array(self.record),
                                     toUTF8Array(self.well), toUTF8Array(self.description))
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            result = {"Success": response.param == 0x00}
            return result

    # 0x100d - CMD_RENAME_DATASET
    class RenameDataset(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x100d

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            from_fields_present = 0
            from_well = None
            from_run_number = None
            from_record = None
            from_description = None
            from_fields_present, run_number, record, well, description = struct.unpack_from("<HH16s16s32s", data, 16)
            from_well = None if from_fields_present & adi.AdiEnums.QueryFilterModes.WELL.value == 0 else fromArrayToUTF8(well)
            from_run_number = None if from_fields_present & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value) == 0 else fromArrayToUTF8(run_number)
            from_record = None if from_fields_present & adi.AdiEnums.QueryFilterModes.RECORD.value == 0 else fromArrayToUTF8(record)
            from_description = None if from_fields_present & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value == 0 else fromArrayToUTF8(description)
            from_key = adi.AdiDefinitions.AdiDataSetPrimaryKey(well=from_well, run_number=from_run_number, record=from_record, description=from_description)

            to_fields_present = 0
            to_well = None
            to_run_number = None
            to_record = None
            to_description = None
            to_fields_present, run_number, record, well, description = struct.unpack_from("<HH16s16s32s", data, 68)
            to_well = None if to_fields_present & adi.AdiEnums.QueryFilterModes.WELL.value == 0 else fromArrayToUTF8(well)
            to_run_number = None if to_fields_present & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value) == 0 else fromArrayToUTF8(run_number)
            to_record = None if to_fields_present & adi.AdiEnums.QueryFilterModes.RECORD.value == 0 else fromArrayToUTF8(record)
            to_description = None if to_fields_present & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value == 0 else fromArrayToUTF8(description)
            to_key = adi.AdiDefinitions.AdiDataSetPrimaryKey(well=to_well, run_number=to_run_number, record=to_record, description=to_description)

            return AdiCommands.RenameDataset(client=client, from_key=from_key, to_key=to_key)

        def __init__(self, client=None, from_key:adi.AdiDefinitions.AdiDataSetPrimaryKey=None, to_key:adi.AdiDefinitions.AdiDataSetPrimaryKey=None):
            super().__init__(name="CMD_RENAME_DATASET", code=self.GetCode(), client=client)
            self.from_key = from_key
            self.to_key = to_key
            self.is_valid = self.from_key is not None and self.to_key is not None and \
                self.from_key.well is not None and self.from_key.run_number is not None and self.from_key.run is not None and self.from_key.record is not None and self.from_key.description is not None and \
                self.to_key.well is not None and self.to_key.run_number is not None and self.to_key.run is not None and self.to_key.record is not None and self.to_key.description is not None

        async def GetLocalResult(self):
            if not self.is_valid: return {"Success": False}
            result = await self.client_local.server.DatasetRename(self.from_key.well, self.from_key.run_number, self.from_key.record, self.from_key.description,
                self.to_key.well, self.to_key.run_number, self.to_key.record, self.to_key.description)
            return {"Success": result}

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            return adi.AdiDefinitions.AdiResponse(param=0x00 if result["Success"] else 0x01)

        def BuildCommandBinaryData(self):
            from_values_present = 0
            if self.from_key.well is not None: from_values_present |= adi.AdiEnums.QueryFilterModes.WELL.value
            if self.from_key.run_number is not None: from_values_present |= adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value
            if self.from_key.run is not None: from_values_present |= adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value
            if self.from_key.record is not None: from_values_present |= adi.AdiEnums.QueryFilterModes.RECORD.value
            if self.from_key.description is not None: from_values_present |= adi.AdiEnums.QueryFilterModes.DESCRIPTION.value
            to_values_present = 0
            if self.to_key.well is not None: to_values_present |= adi.AdiEnums.QueryFilterModes.WELL.value
            if self.to_key.run_number is not None: to_values_present |= adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value
            if self.to_key.run is not None: to_values_present |= adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value
            if self.to_key.record is not None: to_values_present |= adi.AdiEnums.QueryFilterModes.RECORD.value
            if self.to_key.description is not None: to_values_present |= adi.AdiEnums.QueryFilterModes.DESCRIPTION.value

            from_bytes_data = struct.pack(f"<HH16s16s32s", from_values_present, self.from_key.run_number, toUTF8Array(self.from_key.record),
                toUTF8Array(self.from_key.well), toUTF8Array(self.from_key.description))
            to_bytes_data = struct.pack(f"<HH16s16s32s", to_values_present, self.to_key.run_number, toUTF8Array(self.to_key.record),
                toUTF8Array(self.to_key.well), toUTF8Array(self.to_key.description))
            bytes_data = from_bytes_data + to_bytes_data
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            return {"Success": response.param == 0x00}

    # 0x100e - CMD_COPY_DATASET
    class CopyDataset(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x100e

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            from_fields_present = 0
            from_well = None
            from_run_number = None
            from_record = None
            from_description = None
            from_fields_present, run_number, record, well, description = struct.unpack_from("<HH16s16s32s", data, 16)
            from_well = None if from_fields_present & adi.AdiEnums.QueryFilterModes.WELL.value == 0 else fromArrayToUTF8(well)
            from_run_number = None if from_fields_present & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value) == 0 else fromArrayToUTF8(run_number)
            from_record = None if from_fields_present & adi.AdiEnums.QueryFilterModes.RECORD.value == 0 else fromArrayToUTF8(record)
            from_description = None if from_fields_present & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value == 0 else fromArrayToUTF8(description)
            from_key = adi.AdiDefinitions.AdiDataSetPrimaryKey(well=from_well, run_number=from_run_number, record=from_record, description=from_description)

            to_fields_present = 0
            to_well = None
            to_run_number = None
            to_record = None
            to_description = None
            to_fields_present, run_number, record, well, description = struct.unpack_from("<HH16s16s32s", data, 68)
            to_well = None if to_fields_present & adi.AdiEnums.QueryFilterModes.WELL.value == 0 else fromArrayToUTF8(well)
            to_run_number = None if to_fields_present & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value) == 0 else fromArrayToUTF8(run_number)
            to_record = None if to_fields_present & adi.AdiEnums.QueryFilterModes.RECORD.value == 0 else fromArrayToUTF8(record)
            to_description = None if to_fields_present & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value == 0 else fromArrayToUTF8(description)
            to_key = adi.AdiDefinitions.AdiDataSetPrimaryKey(well=to_well, run_number=to_run_number, record=to_record, description=to_description)

            return AdiCommands.CopyDataset(client=client, from_key=from_key, to_key=to_key)

        def __init__(self, client=None, from_key:adi.AdiDefinitions.AdiDataSetPrimaryKey=None, to_key:adi.AdiDefinitions.AdiDataSetPrimaryKey=None):
            super().__init__(name="CMD_COPY_DATASET", code=self.GetCode(), client=client)
            self.from_key = from_key
            self.to_key = to_key
            self.is_valid = self.from_key is not None and self.to_key is not None and \
                self.from_key.well is not None and self.from_key.run_number is not None and self.from_key.run is not None and self.from_key.record is not None and self.from_key.description is not None and \
                self.to_key.well is not None and self.to_key.run_number is not None and self.to_key.run is not None and self.to_key.record is not None and self.to_key.description is not None

        async def GetLocalResult(self):
            if not self.is_valid: return {"Success": False}
            result = await self.client_local.server.DatasetCopy(self.from_key.well, self.from_key.run_number, self.from_key.record, self.from_key.description,
                self.to_key.well, self.to_key.run_number, self.to_key.record, self.to_key.description)
            return {"Success": result}

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            return adi.AdiDefinitions.AdiResponse(param=0x00 if result["Success"] else 0x01)

        def BuildCommandBinaryData(self):
            from_values_present = 0
            if self.from_key.well is not None: from_values_present |= adi.AdiEnums.QueryFilterModes.WELL.value
            if self.from_key.run_number is not None: from_values_present |= adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value
            if self.from_key.run is not None: from_values_present |= adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value
            if self.from_key.record is not None: from_values_present |= adi.AdiEnums.QueryFilterModes.RECORD.value
            if self.from_key.description is not None: from_values_present |= adi.AdiEnums.QueryFilterModes.DESCRIPTION.value
            to_values_present = 0
            if self.to_key.well is not None: to_values_present |= adi.AdiEnums.QueryFilterModes.WELL.value
            if self.to_key.run_number is not None: to_values_present |= adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value
            if self.to_key.run is not None: to_values_present |= adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value
            if self.to_key.record is not None: to_values_present |= adi.AdiEnums.QueryFilterModes.RECORD.value
            if self.to_key.description is not None: to_values_present |= adi.AdiEnums.QueryFilterModes.DESCRIPTION.value

            from_bytes_data = struct.pack(f"<HH16s16s32s", from_values_present, self.from_key.run_number, toUTF8Array(self.from_key.record),
                toUTF8Array(self.from_key.well), toUTF8Array(self.from_key.description))
            to_bytes_data = struct.pack(f"<HH16s16s32s", to_values_present, self.to_key.run_number, toUTF8Array(self.to_key.record),
                toUTF8Array(self.to_key.well), toUTF8Array(self.to_key.description))
            bytes_data = from_bytes_data + to_bytes_data
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            return {"Success": response.param == 0x00}

    # 0x101f - CMD_IDENTIFY
    class Identification(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x101f

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            id_client = None
            exec_name = None
            host_name = None
            user_name = None
            if header.length > 8:
                bytesData = bytes(data)
                ix = 16
                id_client, exec_len = struct.unpack_from("<II", bytesData, ix)
                ix += 8
                if len(data) < ix + exec_len + 4:
                    return
                exec_name, host_len = struct.unpack_from(
                    f"<{exec_len}sI", bytesData, ix)
                ix += exec_len + 4
                if len(data) < ix + host_len + 4:
                    return
                host_name, user_len = struct.unpack_from(
                    f"<{host_len}sI", bytesData, ix)
                ix += host_len + 4
                if len(data) < ix + user_len:
                    return
                [user_name] = struct.unpack_from(
                    f"<{user_len}s", bytesData, ix)
            return AdiCommands.Identification(client=client, id_client=id_client, exec_name=fromArrayToUTF8(exec_name),
                                              host_name=fromArrayToUTF8(host_name), user_name=fromArrayToUTF8(user_name))

        def __init__(self, client=None, id_client=None, exec_name=None, host_name=None, user_name=None, param=0):
            super().__init__(name="CMD_IDENTIFY", code=self.GetCode(), client=client)
            # print(f"Params: id_client\"{id_client}\", exec_name\"{exec_name}\", host_name\"{host_name}\", user_name\"{user_name}\"")
            self.id_client = id_client
            self.exec_name = exec_name
            self.host_name = host_name
            self.user_name = user_name
            self.param = param
            self.is_valid = id_client > 0 and exec_name is not None and host_name is not None and user_name is not None

        def GetDetails(self):
            if not self.is_valid: return "Invalid query"
            return f"ID Client: {self.id_client}, Exec Name: {self.exec_name}, Host Name: {self.host_name}, User Name: {self.user_name}"

        async def ExecuteCommand(self):
            # maybe check if is a banned user?
            if self.client_local is not None:
                self.client_local.user = adi.AdiDefinitions.AdiUser(id_client=self.id_client, exec_name=self.exec_name, host_name=self.host_name, user_name=self.user_name)
            print(f"User: {self.host_name}\\{self.user_name}, {self.exec_name}")

        async def GetResponseBytes(self, result=None):
            if self.is_valid:
                return adi.AdiDefinitions.AdiResponse(value=0x2134)
            else: return adi.AdiDefinitions.AdiResponse(param=0x01)

        def BuildCommandBinaryData(self):
            exec_name = toUTF8Array(self.exec_name)
            len_exec = len(exec_name) + 1
            host_name = toUTF8Array(self.host_name)
            len_host = len(host_name) + 1
            user_name = toUTF8Array(self.user_name)
            len_user = len(user_name) + 1
            bytes_data = struct.pack(f"<II{len_exec}sI{len_host}sI{len_user}s", self.id_client, len_exec, exec_name, len_host, host_name, len_user, user_name)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.param, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            return {"Success": response.value == 0x2134}

    # 0x1016 - CMD_QUERY_SERVER_STATS
    class GetServerStatistics(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x1016

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.GetServerStatistics(client)

        def __init__(self, client=None, param_id=0):
            super().__init__(name="CMD_QUERY_SERVER_STATS", code=self.GetCode(), client=client)
            self.is_valid = True

        async def GetLocalResult(self):
            return {
                    "Connections": 1,
                    "RtConnections": 2,
                    "DataSets": 3,
                    "Files": 0,
                    "IndexObjects": 0,
                    "BytesReceived": 4,
                    "BytesSent": 5,
                    "RtBytesSent": 6,
                    "MessagesReceived": 7,
                    "MessagesSent": 8,
                    "RtMessagesSent": 9,
                    "CoercionObjects": 0,
                    "NotificationObjects": 0,
                    "LockInfoObjects": 0,
                    "LockTypeInfoObjects": 0,
                    "ExchangeAllowed": False,
                    "ExchangeActive": False,
                    "SecurityEnabled": False
            }

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            
            if result is None: result = await self.GetLocalResult()
            flags = 1 if result["ExchangeAllowed"] else 0
            flags += 2 if result["ExchangeActive"] else 0
            flags += 4 if result["SecurityEnabled"] else 0
            data = struct.pack("<IIIIIIIIIIIIIIIIIIII",
                result["Connections"], result["Datasets"], result["Files"], result["IndexObjects"], result["BytesReceived"],
                result["BytesSent"], result["MessagesReceived"], result["MessagesSent"], result["CoercionObjects"],
                result["NotificationObjects"], result["LockInfoObjects"], result["LockTypeInfoObjects"], result["RtConnections"],
                result["RtMessagesSent"], result["RtBytesSent"], 0, 0, 0, 0, flags)
            return adi.AdiDefinitions.AdiResponse(length=len(data), data=data)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            [connections, datasets, files, index_objects, bytes_received, bytes_sent,
            messages_received, messages_sent, coercion_objects, notification_objects,
            lock_info_objects, lock_type_info_objects, rt_connections, rt_messages_sent,
            rt_bytes_sent, z1, z2, z3, z4, flags] = struct.unpack_from("<IIIIIIIIIIIIIIIIIIII", response.data)
            exchange_allowed = flags & 0x01 != 0
            exchange_active = flags & 0x02 != 0
            security_enabled = flags & 0x04 != 0
        
            return {
                    "Connections": connections,
                    "RtConnections": rt_connections,
                    "DataSets": datasets,
                    "Files": files,
                    "IndexObjects": index_objects,
                    "BytesReceived": bytes_received,
                    "BytesSent": bytes_sent,
                    "RtBytesSent": rt_bytes_sent,
                    "MessagesReceived": messages_received,
                    "MessagesSent": messages_sent,
                    "RtMessagesSent": rt_messages_sent,
                    "CoercionObjects": coercion_objects,
                    "NotificationObjects": notification_objects,
                    "LockInfoObjects": lock_info_objects,
                    "LockTypeInfoObjects": lock_type_info_objects,
                    "ExchangeAllowed": exchange_allowed,
                    "ExchangeActive": exchange_active,
                    "SecurityEnabled": security_enabled
            }

    # 0x1017 - CMD_IDENTIFY_2
    class Identification2(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x1017

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            id_client = None
            exec_name = None
            host_name = None
            user_name = None
            if header.length > 8:
                bytesData = bytes(data)
                ix = 16
                id_client, exec_len = struct.unpack_from("<II", bytesData, ix)
                ix += 8
                if len(data) < ix + exec_len + 4:
                    return
                exec_name, host_len = struct.unpack_from(
                    f"<{exec_len}sI", bytesData, ix)
                ix += exec_len + 4
                if len(data) < ix + host_len + 4:
                    return
                host_name, user_len = struct.unpack_from(
                    f"<{host_len}sI", bytesData, ix)
                ix += host_len + 4
                if len(data) < ix + user_len:
                    return
                [user_name] = struct.unpack_from(
                    f"<{user_len}s", bytesData, ix)
            return AdiCommands.Identification2(client=client, id_client=id_client, exec_name=fromArrayToUTF8(exec_name),
                                               host_name=fromArrayToUTF8(host_name), user_name=fromArrayToUTF8(user_name))

        def __init__(self, client=None, id_client=None, exec_name=None, host_name=None, user_name=None):
            super().__init__(name="CMD_IDENTIFY_2", code=self.GetCode(), client=client)
            # print(f"Params: id_client\"{id_client}\", exec_name\"{exec_name}\", host_name\"{host_name}\", user_name\"{user_name}\"")
            self.id_client = id_client
            self.exec_name = exec_name
            self.host_name = host_name
            self.user_name = user_name
            self.is_valid = id_client > 0 and exec_name and host_name and user_name
            
        async def ExecuteCommand(self):
            # maybe check if is a banned user?
            self.client_local.user = adi.AdiDefinitions.AdiUser(id_client=self.id_client, exec_name=self.exec_name, host_name=self.host_name, user_name=self.user_name)
            print(f"User: {self.host_name}\\{self.user_name}, {self.exec_name}")

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            else: return adi.AdiDefinitions.AdiResponse(value=0x2134)

        def BuildCommandBinaryData(self):
            exec_name = toUTF8Array(self.exec_name)
            len_exec = len(exec_name) + 1
            host_name = toUTF8Array(self.host_name)
            len_host = len(host_name) + 1
            user_name = toUTF8Array(self.user_name)
            len_user = len(user_name) + 1
            bytes_data = struct.pack(f"<II{len_exec}sI{len_host}sI{len_user}s", self.id_client, len_exec, exec_name, len_host, host_name, len_user, user_name)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            return {"Success": response.value == 0x2134}

    # 0x101c - CMD_QUERY_ACTIVE_CONNECTIONS
    class GetActiveConnections(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x101c

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.GetActiveConnections(client)

        def __init__(self, client=None):
            super().__init__(name="CMD_QUERY_ACTIVE_CONNECTIONS", code=self.GetCode(), client=client)
            self.is_valid = True

        async def GetLocalResult(self):
            success = True
            result = {}
            try:
                users = []
                if self.client is not None and self.client_local.server is not None:
                    for client in self.client_local.server.clients:
                        users.append({"User": client, "RT": client.realtime, "DS": len(client.opened_datasets), "DC": 0, "TD": 0})
                result["Users"] = users
            except:
                success = False
            result["Success"] = success
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            users = result["Users"]
            data = struct.pack("<I", len(users))
            for client in users:
                u = client["User"]
                length_host = len(u.host_name) + 1
                length_exec = len(u.exec_name) + 1
                length_user = len(u.user_name) + 1
                data += struct.pack(f"<H{length_host}sH{length_exec}sH{length_user}sBBBB",
                    length_host,
                    toUTF8Array(u.host_name),
                    length_exec,
                    toUTF8Array(u.exec_name),
                    length_user,
                    toUTF8Array(u.user_name),
                    1 if client["RT"] else 0,
                    client["DS"], client["DC"], client["TD"])
            return adi.AdiDefinitions.AdiResponse(data=data)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0 and response.length >= 4
            result = {}
            if success:
                try:
                    users = []
                    [number_users] = struct.unpack_from("<I", response.data)
                    ix = 4
                    for _ in range(number_users):
                        [length] = struct.unpack_from("<H", response.data, ix)
                        ix += 2
                        [host_name] = struct.unpack_from(f"<{length}s", response.data, ix)
                        host_name = fromArrayToUTF8(host_name)
                        ix += length
                        [length] = struct.unpack_from("<H", response.data, ix)
                        ix += 2
                        [exec_name] = struct.unpack_from(f"<{length}s", response.data, ix)
                        exec_name = fromArrayToUTF8(exec_name)
                        ix += length
                        [length] = struct.unpack_from("<H", response.data, ix)
                        ix += 2
                        [user_name] = struct.unpack_from(f"<{length}s", response.data, ix)
                        user_name = fromArrayToUTF8(user_name)
                        ix += length
                        [rt, ds, dc, td] = struct.unpack_from("<BBBB", response.data, ix)
                        ix += 4
                        user = adi.AdiDefinitions.AdiUser(host_name=host_name, exec_name=exec_name, user_name=user_name)
                        # print(f"{1 if rt else 0} {ds} {1 if dc else 0} {1 if td else 0} {exec_name}")
                        users.append({"User": user, "RT": rt == 1, "DS": ds, "DC": dc, "TD": td})
                    result["Users"] = users
                except Exception as ex:
                    success = False
            result["Success"] = success
            return result

    # 0x2001 - CMD_QUERY_VARIABLE
    class QueryVariable(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2001

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            bytesData = bytes(data[16:])
            [var_name] = struct.unpack_from(f"<{header.length}s", bytesData)
            var_name = fromArrayToUTF8(var_name)
            return AdiCommands.QueryVariable(client=client, var_name=var_name, output_format=adi.AdiEnums.OutputFormat(header.format))

        def __init__(self, client=None, var_name=None, output_format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE):
            super().__init__(name="CMD_QUERY_VARIABLE", code=self.GetCode(), client=client, output_format=output_format)
            # print(f"Params: var_name\"{var_name}\"")
            self.var_name = var_name
            if self.var_name is not None and "[" in self.var_name:
                pattern = re.compile(r"^[^\[]+\[[0-9]+\]")
                if not pattern.match(self.var_name): self.var_name = None
            self.is_valid = var_name is not None and len(var_name) <= 16

        def GetDetails(self):
            if not self.is_valid: return "Invalid query"
            return f"{self.var_name}"

        async def GetLocalResult(self):
            v = await self.client_local.server.GetVariable(self.var_name)
            
            result = {"Success": v is not None}
            if v is not None: result["Variable"] = v

            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            
            if result is None: result = await self.GetLocalResult()
            param = 0x01 if not result["Success"] else 0x08 if result["Variable"] is None else 0x00
            response = adi.AdiDefinitions.AdiResponse(param=param)
            if param == 0x00:
                try:
                    v = result["Variable"]
                    data = b''
                    if adi.AdiEnums.OutputFormat.BINARY_SIMPLE in self.output_format:
                        bytes_name = toUTF8Array(v.name)
                        bytes_mnemonic = toUTF8Array(v.mnemonic)
                        bytes_curve_label = toUTF8Array(v.curve_label)
                        data = struct.pack(f"<16s5s27sHHHHI", bytes_name, bytes_mnemonic, bytes_curve_label, v.GetStorageType().value, v.size, v.unit_type_id, v.special, v.number_of_decimals)
                    else:
                        bytes_name = toUTF8Array(v.name)
                        data = struct.pack(f"<II16sIIH16s", v.size, v.GetStorageType().value, bytes_name, v.unit_type_id, v.special, v.number_of_decimals, bytes_name)
                    response.data = data
                except Exception as ex:
                    param = 0x01
            
            return response

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<16s", toUTF8Array(self.var_name))
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data), format=self.output_format.value)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.value == 0x00 and response.param == 0x00
            result = {}
            if success:
                var = None
                try:
                    if adi.AdiEnums.OutputFormat.BINARY_SIMPLE in self.output_format:
                        name, mnemonic, curve_label, storage_type, size, unit_type, special, number_of_decimals = struct.unpack_from(f"<16s5s27sHHHHI", response.data)
                        name = fromArrayToUTF8(name)
                        mnemonic = fromArrayToUTF8(mnemonic)
                        curve_label = fromArrayToUTF8(curve_label)
                        ut = None
                        if self.client is not None and self.client.unit_types is not None and len(self.client.unit_types) > unit_type: ut = self.client.unit_types[unit_type]
                        elif self.client_local is not None and self.client_local.server is not None and self.client_local.server.unit_types is not None and len(self.client_local.server.unit_types) > unit_type - 1: ut = self.client_local.server.unit_types[unit_type - 1]
                        var = adi.AdiDefinitions.AdiVariable(name=name, mnemonic=mnemonic, curve_label=curve_label, format=adi.AdiEnums.StorageType(storage_type), size=size, unit_type_id=unit_type, special=special, number_of_decimals=number_of_decimals, unit_type=ut)
                    else:
                        size, storage_type, name, unit_type, special, number_of_decimals, name2 = struct.unpack_from(f"<II16sIIH16s", response.data)
                        name = fromArrayToUTF8(name)
                        name2 = fromArrayToUTF8(name2)
                        # if u1 != 0: print(f"== VAR {name} u1={u1} (expected 0)")
                        # if u2 != 0: print(f"== VAR {name} u2={u2} (expected 0)")
                        ut = None
                        if self.client is not None and self.client.unit_types is not None and len(self.client.unit_types) > unit_type: ut = self.client.unit_types[unit_type]
                        elif self.client_local is not None and self.client_local.server is not None and self.client_local.server.unit_types is not None and len(self.client_local.server.unit_types) > unit_type - 1: ut = self.client_local.server.unit_types[unit_type - 1]
                        var = adi.AdiDefinitions.AdiVariable(name=name, size=size, unit_type_id=unit_type, special=special, number_of_decimals=number_of_decimals, unit_type=ut, format=adi.AdiEnums.StorageType(storage_type))
                    result["Variable"] = var
                except Exception as ex:
                    success = False
            
            result["Success"] = success
            return result

    # 0x2003 - CMD_QUERY_UNIT_TYPES
    class QueryUnitTypes(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2003

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.QueryUnitTypes(client)

        def __init__(self, client=None):
            super().__init__(name="CMD_QUERY_UNIT_TYPES", code=self.GetCode(), client=client)
            self.is_valid = True

        async def GetLocalResult(self):
            unit_types = await self.client_local.server.GetUnitTypes()
            return { "Success": unit_types is not None, "UnitTypes": unit_types }

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            unit_types = result["UnitTypes"]
            data = b''
            for unit_type in unit_types:
                data += struct.pack(f"<16s", toUTF8Array(unit_type.name))
            return adi.AdiDefinitions.AdiResponse(value=len(unit_types), data=data)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.value > 0 and response.length == 16 * response.value
            unit_types = []
            if success:
                for i in range(response.value):
                    [name] = struct.unpack_from(f"<16s", response.data, i * 16)
                    if name[0] == 0: break
                    unit_types.append(
                        adi.AdiDefinitions.UnitType(name="" if len(name) == 0 else fromArrayToUTF8(name)))
                for i in range(len(unit_types)):
                    unit_types[i].id = i
            return {"Success": success, "UnitTypes": unit_types}

    # 0x2004 - CMD_QUERY_UNIT_TYPE_NAME
    class QueryUnitTypeName(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2004

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.QueryUnitTypeName(client=client, unit_type_index=header.param)

        def __init__(self, client=None, unit_type_index=None):
            super().__init__(name="CMD_QUERY_UNIT_TYPE_NAME", code=self.GetCode(), client=client)
            try: self.unit_type_index = int(unit_type_index)
            except: self.unit_type_index = None
            # print(f"Params: unit_type_index={unit_type_index}")
            self.is_valid = self.unit_type_index is not None

        def GetDetails(self):
            if not self.is_valid: return "Invalid query"
            return f"{self.unit_type_index}"

        async def GetLocalResult(self):
            name = await self.client_local.server.GetUnitTypeName(self.unit_type_index)
            return {"Success": name is not None, "Name": name}

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            elif result["Name"] is None: return adi.AdiDefinitions.AdiResponse(param=0x08)
            try:
                data = struct.pack(f"@16s", toUTF8Array(result["Name"]))
                return adi.AdiDefinitions.AdiResponse(data=data)
            except: return adi.AdiDefinitions.AdiResponse(param=0x01)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.unit_type_index)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.value == 0x00 and response.param == 0x00 and response.length > 0
            name = None
            if success:
                [name] = struct.unpack_from(f"<{response.length}s", response.data)
                name = fromArrayToUTF8(name)
            return {"Success": success, "Name": name}

    # 0x2005 - CMD_QUERY_UNIT_TYPE_BY_NAME
    class QueryUnitTypeByName(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2005

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            [name] = struct.unpack_from(f"<{header.length}s", data, 16)
            name = fromArrayToUTF8(name)
            return AdiCommands.QueryUnitTypeByName(client=client, name=name)

        def __init__(self, client=None, name=None):
            super().__init__(name="CMD_QUERY_UNIT_TYPE_BY_NAME", code=self.GetCode(), client=client)
            self.name = name
            # print(f"Params: name=\"{name}\"")
            self.is_valid = self.name is not None

        async def GetLocalResult(self):
            unit_type = await self.client_local.server.GetUnitTypeByName(self.name)
            return {"Success": unit_type is not None, "UnitType": unit_type}

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            elif result["UnitType"] is None: return adi.AdiDefinitions.AdiResponse(param=0x08)
            return adi.AdiDefinitions.AdiResponse(value=result["UnitType"])

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<16s", toUTF8Array("" if self.name is None else self.name))
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            if success: return {"Success": success, "UnitType": response.value}
            else: return {"Success": success}

    # 0x2006 - CMD_QUERY_UNIT_OPTIONS_BY_TYPE_SHORT_LONG
    class QueryUnitOptionsByUnitType(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2006

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            unit_type_index = None
            is_long = False
            if header.param == 0 and header.length == 8:
                unit_type_index, is_long = struct.unpack_from("<II", data, 16)
            return AdiCommands.QueryUnitOptionsByUnitType(client=client, unit_type_index=unit_type_index, is_long=is_long == 1)

        def __init__(self, client=None, unit_type_index=None, is_long=False):
            super().__init__(name="CMD_QUERY_UNIT_OPTIONS_BY_TYPE_SHORT_LONG", code=self.GetCode(), client=client)
            self.unit_type_index = unit_type_index
            self.is_long = is_long
            self.is_valid = self.unit_type_index is not None

        async def GetLocalResult(self):
            unit_options = await self.client_local.server.GetUnitOptionsByUnitType(self.unit_type_index)
            result = {"Success": unit_options is not None}
            if unit_options is not None:
                names_list = [unit.long_name if self.is_long else unit.short_name for unit in unit_options]
                result["UnitOptions"] = names_list
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            
            value = 0
            param = 0x00 if result["Success"] else 0x01
            data = b''
            
            if result["Success"]:
                unit_options = result["UnitOptions"]
                value = len(unit_options)
                try:
                    data = b''
                    for name in unit_options: data += struct.pack(f"<16s", toUTF8Array(name))
                except Exception as ex:
                    data = b''
                    param = 0x01
            
            return adi.AdiDefinitions.AdiResponse(param=param, value=value, data=data)

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<II", self.unit_type_index, 1 if self.is_long else 0)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length == response.value * 16
            unit_options = []
            if success:
                for i in range(response.value):
                    [unit_option] = struct.unpack_from(f"@16s", response.data, i * 16)
                    unit_options.append(fromArrayToUTF8(unit_option))
            return {"Success": success, "UnitOptions": unit_options}

    # 0x2007 - CMD_QUERY_UNIT_CONVERSION_INFO
    class QueryUnitConversionInfo(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2007

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            bytesData = bytes(data)
            unit_type_index, unit_option = struct.unpack_from(
                "<II", bytesData, 16)
            return AdiCommands.QueryUnitConversionInfo(client=client, unit_type_index=unit_type_index, unit_option=unit_option)

        def __init__(self, client=None, unit_type_index=None, unit_option=None):
            super().__init__(name="CMD_QUERY_UNIT_CONVERSION_INFO", code=self.GetCode(), client=client)
            self.unit_type_index = unit_type_index
            self.unit_option = unit_option
            # print(f"Params: unit_type_index={self.unit_type_index}, unit_option={self.unit_option}")
            self.is_valid = self.unit_type_index is not None and self.unit_option is not None and self.unit_type_index >= 0 and self.unit_option >= 0

        async def GetLocalResult(self):
            conversion_info = await self.client_local.server.GetUnitConversionInfo(self.unit_type_index, self.unit_option)
            result = {"Success": conversion_info is not None}
            if conversion_info is not None: result["ConversionInfo"] = conversion_info
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            elif result["ConversionInfo"] is None: return adi.AdiDefinitions.AdiResponse(param=0x08)
            c = result["ConversionInfo"]
            data = struct.pack(f"<Idd", c.function_type, c.arg1, c.arg2)
            response = adi.AdiDefinitions.AdiResponse(data=data)
            return response

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(
                f"<II", self.unit_type_index, self.unit_option)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length == 20
            result = {"Success": success}
            if success:
                fn_type, arg1, arg2 = struct.unpack_from(f"<Idd", response.data)
                result["ConversionInfo"] = adi.AdiDefinitions.ConversionInfo(fn_type, arg1, arg2)
            return result

    # 0x2009 - CMD_QUERY_OPTIONS_LISTS
    class QueryOptionsFromOptionsList(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2009

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            name = None
            if header.length > 0:
                [name] = struct.unpack_from(f"<{header.length}s", data, 16)
                name = fromArrayToUTF8(name)
            return AdiCommands.QueryOptionsFromOptionsList(client=client, name=name)

        def __init__(self, client=None, name=None):
            super().__init__(name="CMD_QUERY_OPTIONS_LISTS", code=self.GetCode(), client=client)
            self.name = name
            # print(f"Params: name\"{self.name}\"")
            self.is_valid = self.name is not None

        def GetDetails(self):
            if not self.is_valid: return "Invalid query"
            return f"{self.name}"

        async def GetLocalResult(self):
            options_list = await self.client_local.server.GetOptionsListByName(self.name)
            result = {"Success": options_list is not None}
            if options_list is not None: result["OptionsList"] = options_list
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            elif len(result["OptionsList"].options) == 0: return adi.AdiDefinitions.AdiResponse(param=0x08)

            options_list = []
            for o in result["OptionsList"].options: options_list.append(toUTF8Array(o))

            data = b''
            # First the length of every string is added (including the 0 ending)
            for bytes_name in options_list:
                data += struct.pack("<I", len(bytes_name) + 1)
            # Then add the bytes of each option
            for bytes_name in options_list:
                data += struct.pack(f"<{len(bytes_name) + 1}s", bytes_name)
            response = adi.AdiDefinitions.AdiResponse(value=len(options_list), data=data)
            return response

        def BuildCommandBinaryData(self):
            bytes_name = toUTF8Array(self.name)
            length = len(bytes_name) + 1
            if length < 16: length = 16
            bytes_data = struct.pack(f"<{length}s", bytes_name)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=length)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.value > 0 and response.length > response.value * 4
            result = {"Success": success}
            if success:
                options_list = adi.AdiDefinitions.OptionsList(self.name)
                options_lengths = struct.unpack_from(''.join(['I'] * response.value), response.data)
                ix = response.value * 4
                for i in range(response.value):
                    length = options_lengths[i]
                    [name] = struct.unpack_from(f"{length}s", response.data, ix)
                    options_list.options.append(fromArrayToUTF8(name))
                    ix += length
                result["OptionsList"] = options_list
            return result

    # 0x2010 - CMD_QUERY_DATASET_EXISTS
    class QueryDatasetExists(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2010

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            active_filters = None
            well = None
            run_number = None
            record = None
            description = None
            try:
                active_filters, run_number, record, well, description = struct.unpack_from(
                    "<HH16s16s32s", bytes(data[16:]))
                if active_filters & adi.AdiEnums.QueryFilterModes.WELL.value:
                    well = fromArrayToUTF8(well).strip()
                else:
                    well = None
                if active_filters & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value):
                    run_number = run_number
                else:
                    run_number = None
                if active_filters & adi.AdiEnums.QueryFilterModes.RECORD.value:
                    record = fromArrayToUTF8(record).strip()
                else:
                    record = None
                if active_filters & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value:
                    description = fromArrayToUTF8(description).strip()
                else:
                    description = None
            except:
                active_filters = None
            return AdiCommands.QueryDatasetExists(client=client, active_filters=active_filters, well=well, run_number=run_number, record=record, description=description)

        def __init__(self, client=None, active_filters=0x00, well=None, run_number=None, record=None, description=None):
            super().__init__(name="CMD_QUERY_DATASET_EXISTS", code=self.GetCode(), client=client)
            self.active_filters = active_filters
            self.well = well
            self.run_number = run_number
            self.record = record
            self.description = description
            self.is_valid = True

        def GetDetails(self):
            if not self.is_valid: return "Invalid query"
            details = []
            if self.well is not None and len(self.well) > 0: details.append(f"Well=\"{self.well}\"")
            if self.run_number is not None: details.append(f"RunNumber={self.run_number}")
            if self.record is not None and len(self.record) > 0: details.append(f"Record=\"{self.record}\"")
            if self.description is not None and len(self.description) > 0: details.append(f"Description=\"{self.description}\"")
            return ", ".join(details)

        async def GetLocalResult(self):
            # This command seems to return if the dataset exists in the database or not
            success = True
            exists = False
            try:
                exists = await self.client_local.server.DatasetExists(well=self.well, run_number=self.run_number, record=self.record, description=self.description)
            except:
                success = False
            return {"Success": success, "Exists": exists}

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            return adi.AdiDefinitions.AdiResponse(param=0x00, value=0x01 if result["Exists"] else 0x00)

        def BuildCommandBinaryData(self):
            bytes_well = toUTF8Array("" if self.well is None else self.well)
            bytes_record = toUTF8Array("" if self.record is None else self.record)
            bytes_description = toUTF8Array("" if self.description is None else self.description)
            active_filters = 0
            if self.well is not None and len(self.well) > 0: active_filters |= adi.AdiEnums.QueryFilterModes.WELL.value
            if self.run_number is not None: active_filters |= adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value
            if self.record is not None and len(self.record) > 0: active_filters |= adi.AdiEnums.QueryFilterModes.RECORD.value
            if self.description is not None and len(self.description) > 0: active_filters |= adi.AdiEnums.QueryFilterModes.DESCRIPTION.value
            bytes_data = struct.pack(f"<HH16s16s32s", active_filters, self.run_number if self.run_number is not None else 0, bytes_record, bytes_well, bytes_description)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length == 0
            exists = False
            if success and response.value == 0x01: exists = True
            return {"Success": success, "Exists": exists}

    # 0x200d - CMD_QUERY_WELL_LIST
    class QueryWellsList(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x200d

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.QueryWellsList(client)

        def __init__(self, client=None):
            super().__init__(name="CMD_QUERY_WELL_LIST", code=self.GetCode(), client=client)
            self.is_valid = True

        async def GetLocalResult(self):
            wells = await self.client_local.server.GetWellsList()
            result = {"Success": wells is not None}
            if wells is not None: result["Wells"] = wells
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            elif len(result["Wells"]) == 0: return adi.AdiDefinitions.AdiResponse(param=0x08)

            data = struct.pack(f"<I", len(result["Wells"]))
            for well in result["Wells"]:
                data += struct.pack(f"<16s", toUTF8Array(well))
            response = adi.AdiDefinitions.AdiResponse(data=data)
            return response

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length > 4
            result = {"Success": success}
            if success:
                wells = []
                [length] = struct.unpack_from('<I', response.data)
                for i in range(length):
                    [name] = struct.unpack_from(f"<16s", response.data, 4 + i * 16)
                    wells.append(fromArrayToUTF8(name))
                result["Wells"] = wells
            return result

    # 0x2012 - CMD_QUERY_RUN_RECORD_VARIABLES
    class QueryRunRecordsVariables(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2012

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            active_filters = None
            well = None
            run_number = None
            record = None
            description = None
            try:
                active_filters, run_number, record, well, description = struct.unpack_from("<HH16s16s32s", data, 16)
                if active_filters & adi.AdiEnums.QueryFilterModes.WELL.value:
                    well = fromArrayToUTF8(well).strip()
                else:
                    well = None
                if active_filters & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value):
                    run_number = run_number
                else:
                    run_number = None
                if active_filters & adi.AdiEnums.QueryFilterModes.RECORD.value:
                    record = fromArrayToUTF8(record).strip()
                else:
                    record = None
                if active_filters & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value:
                    description = fromArrayToUTF8(description).strip()
                else:
                    description = None
            except:
                active_filters = None
            output_format = adi.AdiEnums.OutputFormat(header.format)
            return AdiCommands.QueryRunRecordsVariables(client, active_filters, well, run_number, record, description, output_format)

        def __init__(self, client=None, active_filters=0x00, well=None, run_number=None, record=None, description=None, output_format=adi.AdiEnums.OutputFormat.XML_SIMPLE):
            super().__init__(name="CMD_QUERY_RUN_RECORD_VARIABLES", code=self.GetCode(), client=client)
            self.active_filters = active_filters
            self.well = well
            self.run_number = run_number
            self.record = record
            self.description = description
            self.output_format = output_format
            self.is_valid = self.active_filters is not None and self.record is not None

        def GetDetails(self):
            if not self.is_valid: return "Invalid query"
            str_details = ""
            if self.active_filters & adi.AdiEnums.QueryFilterModes.WELL.value != 0: str_details += ('' if len(str_details) == 0 else ' \\ ') + self.well
            if self.active_filters & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value) != 0: str_details += ('' if len(str_details) == 0 else ' \\ ') + str(self.run_number)
            if self.active_filters & adi.AdiEnums.QueryFilterModes.RECORD.value != 0: str_details += ('' if len(str_details) == 0 else ' \\ ') + self.record
            if self.active_filters & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value != 0: str_details += ('' if len(str_details) == 0 else ' \\ ') + self.description
            return str_details

        async def GetLocalResult(self):
            variables = await self.client_local.server.GetRecordVariablesFromTable(
                well=self.well if self.active_filters & adi.AdiEnums.QueryFilterModes.WELL.value else None,
                run_number=self.run_number if self.active_filters & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value) else None,
                record=self.record if self.active_filters & adi.AdiEnums.QueryFilterModes.RECORD.value else None,
                description=self.description if self.active_filters & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value else None
            )
            result = {"Success": variables is not None}
            if variables is not None: result["Variables"] = variables
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            elif len(result["Variables"]) == 0: return adi.AdiDefinitions.AdiResponse(param=0x08)

            data = b''
            variables = result["Variables"]
            for v in variables:
                rv = v.record_variable_data
                if adi.AdiEnums.OutputFormat.XML_SIMPLE in self.output_format:
                    str_data = toUTF8Array("<?xml version=1.0?>" + \
                        "<ServerVariable>" + \
                        f"<InternalName>{v.name}</InternalName>" + \
                        f"<Mnemonic>{'' if rv.mnemonic is None else rv.mnemonic}</Mnemonic>" + \
                        f"<CurveLabel>{'' if rv.curve_label is None else rv.curve_label}</CurveLabel>" + \
                        f"<Format>{v.GetStorageType().value}</Format>" + \
                        f"<NumberOfBytes>{v.size}</NumberOfBytes>" + \
                        f"<UnitType>{v.unit_type_id}</UnitType>" + \
                        f"<SpecialHandling>{v.special}</SpecialHandling>" + \
                        f"<NumberOfDecimalPlaces>{v.number_of_decimals}</NumberOfDecimalPlaces>" + \
                        f"<OffsetInRecord>{v.offset}</OffsetInRecord>" + \
                        f"<Mnemonic32>{'' if rv.mnemonic32 is None else rv.mnemonic32}</Mnemonic32>" + \
                        f"<Algorithm>{rv.algorithm}</Algorithm>" + \
                        f"<Ref Variable>{'' if rv.ref_variable is None else rv.ref_variable}</Ref Variable>" + \
                        f"<Coeff1>{rv.coeff1:.3f}</Coeff1>" + \
                        f"<Coeff2>{rv.coeff2:.3f}</Coeff2>" + \
                        f"<Coeff3>{rv.coeff3:.3f}</Coeff3>" + \
                        "</ServerVariable>")
                    length = len(str_data)
                    data += struct.pack(f"<I{length}s", length, str_data)
                else:
                    data += struct.pack(f"<16s5s27sHHHHHH",
                                        toUTF8Array(v.name),
                                        toUTF8Array(rv.mnemonic),
                                        toUTF8Array(rv.curve_label),
                                        v.GetStorageType().value, v.size, v.unit_type_id, v.special, v.number_of_decimals, v.offset)
                response = adi.AdiDefinitions.AdiResponse(value=len(variables), data=data)

            return response

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<HH16s16s32s", self.active_filters, self.run_number,
                                     toUTF8Array(self.record),
                                     toUTF8Array(self.well),
                                     toUTF8Array(self.description))
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=self.output_format.value, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.value > 0
            result = {"Success": success}
            if success:
                try:
                    variables = []
                    ix = 0
                    for _ in range(response.value):
                        variable = None
                        if adi.AdiEnums.OutputFormat.XML_SIMPLE in self.output_format:
                            [length] = struct.unpack_from("<I", response.data, ix)
                            ix += 4
                            [xml] = struct.unpack_from(f"{length}s", response.data, ix)
                            ix += length
                            xml = fromArrayToUTF8(xml)
                            def GetXMLTagValue(tag):
                                start = xml.find(f"<{tag}>")
                                end = xml.find(f"</{tag}>")
                                length = end - (start + len(tag) + 2)
                                if start > 0 and end > start: return "" if length == 0 else xml[start + len(tag) + 2:end]
                                return None
                            rv = adi.AdiDefinitions.AdiRecordVariable(
                                mnemonic=GetXMLTagValue("Mnemonic"),
                                curve_label=GetXMLTagValue("CurveLabel"),
                                mnemonic32=GetXMLTagValue("Mnemonic32"),
                                algorithm=GetXMLTagValue("Algorithm"),
                                ref_variable=GetXMLTagValue("RefVariable"),
                                coeff1=float(GetXMLTagValue("Coeff1").zfill(1)),
                                coeff2=float(GetXMLTagValue("Coeff2").zfill(1)),
                                coeff3=float(GetXMLTagValue("Coeff3").zfill(1)))
                            variable = adi.AdiDefinitions.AdiVariable(
                                name=GetXMLTagValue("InternalName"),
                                format=adi.AdiEnums.StorageType(int(GetXMLTagValue("Format").zfill(1))),
                                size=int(GetXMLTagValue("NumberOfBytes").zfill(1)),
                                unit_type_id=int(GetXMLTagValue("UnitType").zfill(1)),
                                special=int(GetXMLTagValue("SpecialHandling").zfill(1)),
                                number_of_decimals=int(GetXMLTagValue("NumberOfDecimalPlaces").zfill(1)),
                                offset=int(GetXMLTagValue("OffsetInRecord").zfill(1)),
                                record_variable_data=rv)
                        else:
                            name, mnemonic, curve_label, format, size, unit_type_id, special, number_of_decimals, offset = struct.unpack_from("<16s5s27sHHHHHH", response.data, ix)
                            ix += 60
                            ut = None
                            if self.client is not None and type(self.client).__name__ == 'AdiClientToRemote' and self.client.unit_types is not None and len(self.client.unit_types) > unit_type_id - 1: ut = self.client.unit_types[unit_type_id - 1]
                            elif self.client is not None and type(self.client).__name__ == 'AdiClient' and self.client_local.server is not None and self.client_local.server.unit_types is not None and len(self.client_local.server.unit_types) > unit_type_id - 1: ut = self.client_local.server.unit_types[unit_type_id - 1]
                            rv = adi.AdiDefinitions.AdiRecordVariable(
                                mnemonic=fromArrayToUTF8(mnemonic),
                                curve_label=fromArrayToUTF8(curve_label))
                            variable = adi.AdiDefinitions.AdiVariable(
                                name=fromArrayToUTF8(name),
                                format=adi.AdiEnums.StorageType(int(format)),
                                size=int(size),
                                unit_type=ut,
                                unit_type_id=int(unit_type_id),
                                special=int(special),
                                number_of_decimals=int(number_of_decimals),
                                offset=int(offset),
                                record_variable_data=rv)
                    
                        # Adding a reference to the unit type object, if exists
                        unit_types = None
                        if self.client and self.client.unit_types: unit_types = self.client.unit_types
                        elif self.client and self.client_local.server and self.client_local.server.unit_types: unit_types = self.client_local.server.unit_types
                        if unit_types is not None and len(unit_types) > variable.unit_type_id: variable.unit_type = unit_types[variable.unit_type_id]
                        
                        variables.append(variable)
                    result["Variables"] = variables
                except Exception as ex:
                    result["Success"] = False
            return result

    # 0x2013 - CMD_QUERY_RECORD_VARIABLES
    class QueryRecordVariables(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2013

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            [record_name] = struct.unpack_from(f"<{header.length}s", data, 16)
            record_name = fromArrayToUTF8(record_name)
            return AdiCommands.QueryRecordVariables(client=client, record_name=record_name, output_format=adi.AdiEnums.OutputFormat(header.format))

        def __init__(self, client=None, record_name=None, output_format=adi.AdiEnums.OutputFormat.BINARY_FULL):
            super().__init__(name="CMD_QUERY_RECORD_VARIABLES", code=self.GetCode(), client=client)
            self.record_name = record_name
            self.output_format = output_format
            # print(f"Params: record_name=\"{self.record_name}\", output_format=\"{self.output_format}\"")
            self.is_valid = self.record_name is not None

        async def GetLocalResult(self):
            variables = await self.client_local.server.GetRecordVariables(self.record_name)
            result = {"Success": variables is not None}
            if variables is not None: result["Variables"] = variables
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)

            variables = result["Variables"]
            data = b''
            for v in variables:
                rv = v.record_variable_data
                try:
                    if adi.AdiEnums.OutputFormat.BINARY_FULL in self.output_format:
                        str_data = toUTF8Array("<?xml version=1.0?>" + \
                            "<ServerVariable>" + \
                            f"<InternalName>{v.name}</InternalName>" + \
                            f"<Mnemonic>{rv.mnemonic}</Mnemonic>" + \
                            f"<CurveLabel>{rv.curve_label}</CurveLabel>" + \
                            f"<Format>{v.GetStorageType().value}</Format>" + \
                            f"<NumberOfBytes>{v.size}</NumberOfBytes>" + \
                            f"<UnitType>{v.unit_type_id}</UnitType>" + \
                            f"<SpecialHandling>{v.special}</SpecialHandling>" + \
                            f"<NumberOfDecimalPlaces>{v.number_of_decimals}</NumberOfDecimalPlaces>" + \
                            f"<OffsetInRecord>{v.offset}</OffsetInRecord>" + \
                            f"<Mnemonic32>{rv.mnemonic32}</Mnemonic32>" + \
                            f"<Algorithm>{rv.algorithm}</Algorithm>" + \
                            f"<Ref Variable>{'' if rv.ref_variable is None else rv.ref_variable}</Ref Variable>" + \
                            f"<Coeff1>{rv.coeff1:.3f}</Coeff1>" + \
                            f"<Coeff2>{rv.coeff2:.3f}</Coeff2>" + \
                            f"<Coeff3>{rv.coeff3:.3f}</Coeff3>" + \
                            "</ServerVariable>")
                        length = len(str_data)
                        data += struct.pack(f"<I{length}s", length, str_data)
                    else:
                        data += struct.pack(f"<16s5s27sHHHHHH",
                                            toUTF8Array(v.name),
                                            toUTF8Array(rv.mnemonic),
                                            toUTF8Array(rv.curve_label),
                                            v.GetStorageType().value, v.size, v.unit_type_id, v.special, v.number_of_decimals, v.offset)
                except Exception as ex:
                    print(f"Error packing variable {v.name}: {ex}")
            response = adi.AdiDefinitions.AdiResponse(value=len(variables), data=data, length=len(data))

            return response

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<16s", toUTF8Array(self.record_name))
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=self.output_format.value, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            if success:
                try:
                    variables = []
                    ix = 0
                    for _ in range(response.value):
                        variable = None
                        if adi.AdiEnums.OutputFormat.BINARY_FULL in self.output_format:
                            [length] = struct.unpack_from("<I", response.data, ix)
                            ix += 4
                            [xml] = struct.unpack_from(f"{length}s", response.data, ix)
                            ix += length
                            xml = fromArrayToUTF8(xml)
                            def GetXMLTagValue(tag):
                                start = xml.find(f"<{tag}>")
                                end = xml.find(f"</{tag}>")
                                length = end - (start + len(tag) + 2)
                                if start > 0 and end > start: return "" if length == 0 else xml[start + len(tag) + 2:end]
                                return None
                            unit_type=int(GetXMLTagValue("UnitType").zfill(1))
                            ut = None
                            if self.client is not None and type(self.client).__name__ == 'AdiClientToRemote' and self.client.unit_types is not None and len(self.client.unit_types) > unit_type - 1: ut = self.client.unit_types[unit_type - 1]
                            elif self.client is not None and type(self.client).__name__ == 'AdiClient' and self.client_local.server is not None and self.client_local.server.unit_types is not None and len(self.client_local.server.unit_types) > unit_type - 1: ut = self.client_local.server.unit_types[unit_type - 1]
                            rv = adi.AdiDefinitions.AdiRecordVariable(
                                mnemonic=GetXMLTagValue("Mnemonic"),
                                curve_label=GetXMLTagValue("CurveLabel"),
                                mnemonic32=GetXMLTagValue("Mnemonic32"),
                                algorithm=GetXMLTagValue("Algorithm"),
                                ref_variable=GetXMLTagValue("RefVariable"),
                                coeff1=float(GetXMLTagValue("Coeff1").zfill(1)),
                                coeff2=float(GetXMLTagValue("Coeff2").zfill(1)),
                                coeff3=float(GetXMLTagValue("Coeff3").zfill(1)))
                            variable = adi.AdiDefinitions.AdiVariable(
                                name=GetXMLTagValue("InternalName"),
                                format=adi.AdiEnums.StorageType(int(GetXMLTagValue("Format").zfill(1))),
                                size=int(GetXMLTagValue("NumberOfBytes").zfill(1)),
                                unit_type=ut,
                                unit_type_id=int(GetXMLTagValue("UnitType").zfill(1)),
                                special=int(GetXMLTagValue("SpecialHandling").zfill(1)),
                                number_of_decimals=int(GetXMLTagValue("NumberOfDecimalPlaces").zfill(1)),
                                offset=int(GetXMLTagValue("OffsetInRecord").zfill(1)),
                                record_variable_data=rv)
                        else:
                            name, mnemonic, curve_label, format, size, unit_type_id, special, number_of_decimals, offset = struct.unpack_from("<16s5s27sHHHHHH", response.data, ix)
                            ix += 60
                            rv = adi.AdiDefinitions.AdiRecordVariable(
                                mnemonic=fromArrayToUTF8(mnemonic),
                                curve_label=fromArrayToUTF8(curve_label))
                            variable = adi.AdiDefinitions.AdiVariable(
                                name=fromArrayToUTF8(name),
                                format=adi.AdiEnums.StorageType(int(format)),
                                size=int(size),
                                unit_type_id=int(unit_type_id),
                                special=int(special),
                                number_of_decimals=int(number_of_decimals),
                                offset=int(offset),
                                record_variable_data=rv)

                        # Adding a reference to the unit type object, if exists
                        unit_types = None
                        if self.client and self.client.unit_types: unit_types = self.client.unit_types
                        elif self.client and self.client_local.server and self.client_local.server.unit_types: unit_types = self.client_local.server.unit_types
                        if unit_types is not None and len(unit_types) > variable.unit_type_id: variable.unit_type = unit_types[variable.unit_type_id]
                        
                        variables.append(variable)
                    result["Variables"] = variables
                except Exception as ex:
                    result["Success"] = False
            return result

    # 0x2014 - CMD_QUERY_STATISTICS_OPERATIONS - List of operations (None, Max, Min, Smoothed, etc.)
    class QueryStatisticsOperations(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2014

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.QueryStatisticsOperations(client)

        def __init__(self, client=None):
            super().__init__(name="CMD_QUERY_STATISTICS_OPERATIONS", code=self.GetCode(), client=client)
            self.is_valid = True

        async def GetLocalResult(self):
            success = True
            result = {}
            try:
                operations = [
                    ["None", 0x00, 0x1f],
                    ["Max", 0x00, 0x03],
                    ["Min", 0x00, 0x03],
                    ["Mean", 0x00, 0x03],
                    ["StDev", 0x00, 0x03],
                    ["Smoothed", 0x01, 0x03],
                    ["Last", 0x00, 0x1f],
                    ["Next", 0x00, 0x1f],
                    ["Last In Intervl", 0x00, 0x1f],
                    ["Mean Windowed", 0x01, 0x03],
                    ["CTI", 0x00, 0x1f]
                ]
                result["Operations"] = operations
            except:
                success = False
            result["Success"] = success
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            operations = result["Operations"]
            data = b''
            for op in operations:
                data += struct.pack(f"<16sII", toUTF8Array(op[0]), op[1], op[2])
            return adi.AdiDefinitions.AdiResponse(value=len(operations), data=data)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0 and response.length >= response.value * 24
            result = {}
            if success:
                try:
                    operations = []
                    for i in range(response.value):
                        [op, arg1, arg2] = struct.unpack_from("<16sII", response.data, i * 24)
                        op = fromArrayToUTF8(op)
                        operations.append([op, arg1, arg2])
                    result["Operations"] = operations
                except Exception as ex:
                    success = False
            result["Success"] = success
            return result

    # 0x2015 - CMD_QUERY_RECORD_ATTRIBUTES
    class QueryRecordAttributes(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2015

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            [record_name] = struct.unpack_from(f"<{header.length}s", data, 16)
            record_name = fromArrayToUTF8(record_name)
            return AdiCommands.QueryRecordAttributes(client=client, record_name=record_name)

        def __init__(self, client=None, record_name=None):
            super().__init__(name="CMD_QUERY_RECORD_ATTRIBUTES", code=self.GetCode(), client=client)
            self.record_name = record_name
            self.is_valid = self.record_name is not None

        def GetDetails(self):
            if not self.is_valid: return "Invalid query"
            return f"{self.record_name}"

        async def GetLocalResult(self):
            record = await self.client_local.server.GetRecordAttributes(self.record_name)
            result = {"Success": record is not None}
            if record is not None: result["Record"] = record
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)

            record:adi.AdiDefinitions.AdiRecord = result["Record"]
            pks = record.primary_keys
            pk_well = pks & adi.AdiDefinitions.RecordPrimaryKeys.Well.value != 0
            pk_run = pks & adi.AdiDefinitions.RecordPrimaryKeys.BitRun.value != 0
            pk_description = pks & adi.AdiDefinitions.RecordPrimaryKeys.Description.value != 0
            data = struct.pack(f"<16sHHHHBBBB", toUTF8Array(record.name), record.record_type_id, record.index_types,
                                record.number_variables, record.category_id,
                                2 if pk_well else 0, 2 if pk_run else 0, 0, 2 if pk_description else 0)
            response = adi.AdiDefinitions.AdiResponse(length=len(data), data=data)
            return response

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<16s", toUTF8Array(self.record_name))
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.value == 0 and response.length == 28
            result = {"Success": success}
            if success:
                try:
                    name, record_type_id, index_types, number_variables, category_id, pk_well, pk_run, _, pk_description = struct.unpack_from("<16sHHHHBBBB", response.data)
                    pks = 0
                    if pk_well != 0: pks += adi.AdiDefinitions.RecordPrimaryKeys.Well.value
                    if pk_run != 0: pks += adi.AdiDefinitions.RecordPrimaryKeys.BitRun.value
                    if pk_description != 0: pks += adi.AdiDefinitions.RecordPrimaryKeys.Description.value
                    record = adi.AdiDefinitions.AdiRecord(
                        name=fromArrayToUTF8(name),
                        record_type_id=record_type_id,
                        index_types=index_types,
                        number_variables=number_variables,
                        category_id=category_id,
                        primary_keys=pks)
                    result["Record"] = record
                except Exception as ex:
                    result["Success"] = False
            return result

    # 0x2017 - CMD_QUERY_UNITSET_NAMES
    class QueryUnitsets(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2017

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.QueryUnitsets(client)

        def __init__(self, client=None):
            super().__init__(name="CMD_QUERY_UNITSET_NAMES", code=self.GetCode(), client=client)
            self.is_valid = True

        async def GetLocalResult(self):
            unitsets = await self.client_local.server.GetUnitsets()
            result = {"Success": unitsets is not None}
            if unitsets is not None: result["Unitsets"] = unitsets
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            elif len(result["Unitsets"]) == 0: return adi.AdiDefinitions.AdiResponse(param=0x08)
        
            data = b''
            for unitset in result["Unitsets"]:
                u = toUTF8Array(unitset)
                length = len(u) + 1
                data += struct.pack(f"<H{length}s", length, u)
            response = adi.AdiDefinitions.AdiResponse(value=len(result["Unitsets"]), data=data)
            return response

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.value > 0
            result = {"Success": success}
            if success:
                unitsets = []
                ix = 0
                for i in range(response.value):
                    [length] = struct.unpack_from("<H", response.data, ix)
                    ix += 2
                    [name] = struct.unpack_from(f"<{length}s", response.data, ix)
                    ix += length
                    unitsets.append(fromArrayToUTF8(name))
                result["Unitsets"] = unitsets
            return result

    # 0x2018 - CMD_LOAD_UNITSET
    class QueryUnitsetDetails(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2018

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            bytes_data = bytes(data[16:])
            _, unitset = struct.unpack_from(
                f"<H{header.length - 2}s", bytes_data)
            unitset = fromArrayToUTF8(unitset).strip()
            return AdiCommands.QueryUnitsetDetails(client=client, unitset=unitset)

        def __init__(self, client=None, unitset=None):
            super().__init__(name="CMD_LOAD_UNITSET", code=self.GetCode(), client=client)
            self.unitset = unitset
            # print(f"Params: unitset=\"{self.unitset}\"")
            self.is_valid = self.unitset is not None

        def GetDetails(self):
            if not self.is_valid: return "Invalid query"
            return f"{self.unitset}"

        async def GetLocalResult(self):
            unit_types = await self.client_local.server.GetUnitsetOptions(self.unitset)
            result = {"Success": unit_types is not None}
            if unit_types is not None: result["UnitTypes"] = unit_types
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            elif len(result["UnitTypes"]) == 0: return adi.AdiDefinitions.AdiResponse(param=0x08)
        
            length = len(result["UnitTypes"])
            # counter = 0
            data = struct.pack("<I", length)
            for i in range(length):
                ut = result["UnitTypes"][i]
                data += struct.pack("<16sI16s16s",
                                    toUTF8Array(ut.name),
                                    0,
                                    toUTF8Array(ut.unit_option.long_name),
                                    toUTF8Array(ut.unit_option.short_name))
                # counter += 1
            response = adi.AdiDefinitions.AdiResponse(value=length, data=data)
            return response

        def BuildCommandBinaryData(self):
            bytes_us = toUTF8Array(self.unitset)
            length = len(bytes_us) + 1
            bytes_data = struct.pack(f"<H{length}s", length, bytes_us)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.length >= 4
            units = []
            if success:
                [number] = struct.unpack_from(f"<I", response.data)
                if response.length != number * 52 + 4:
                    success = False
                else:
                    for i in range(number):
                        name, _, long_name, short_name = struct.unpack_from(
                            f"<16sI16s16s", response.data, 4 + i * 52)
                        name = fromArrayToUTF8(name)
                        long_name = fromArrayToUTF8(long_name)
                        short_name = fromArrayToUTF8(short_name)
                        units.append(
                            adi.AdiDefinitions.UnitType(name=name, unit_option=adi.AdiDefinitions.UnitOption(short_name=short_name, long_name=long_name)))
            return {"Success": success, "UnitTypes": units}

    # 0x2019 - CMD_QUERY_VARIABLE_DECIMALS_PER_OPTION
    class QueryVariableDecimalsPerUnitOption(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2019

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            [var_name, unit_option] = struct.unpack_from(f"<16sI", data, 16)
            var_name = fromArrayToUTF8(var_name)
            return AdiCommands.QueryVariableDecimalsPerUnitOption(client=client, var_name=var_name, unit_option=unit_option)

        def __init__(self, client=None, var_name=None, unit_option=None):
            super().__init__(name="CMD_QUERY_VARIABLE_DECIMALS_PER_OPTION", code=self.GetCode(), client=client)
            self.var_name = var_name
            self.unit_option = unit_option
            self.is_valid = self.var_name is not None and self.unit_option is not None

        def GetDetails(self):
            if not self.is_valid: return "Invalid query"
            return f"{self.var_name}, {self.unit_option}"

        async def GetLocalResult(self):
            cmd = AdiCommands.QueryVariablesDecimalsPerUnitOption(client=self.client, variables=[{"var_name": self.var_name, "unit_option": self.unit_option}])
            result = cmd.GetLocalResult()
            if not result["Success"]: return result
            result["NumberDecimals"] = result["NumberDecimals"][0]
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            return adi.AdiDefinitions.AdiResponse(value=result["NumberDecimals"])

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<16sI", toUTF8Array("" if self.var_name is None else self.var_name), self.unit_option)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            if success: result["NumberDecimals"] = response.value
            return result

    # 0x2020 - CMD_QUERY_STRING_VALUE
    class QueryStringValue(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2020

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            query_type = adi.AdiEnums.QueryValueType(header.param)
            return AdiCommands.QueryStringValue(client=client, query_type=query_type)

        def __init__(self, client=None, query_type=None):
            super().__init__(name="CMD_QUERY_STRING_VALUE", code=self.GetCode(), client=client)
            self.query_type = query_type
            # print(f"Params: query_type={self.query_type}")
            self.is_valid = True

        async def GetLocalResult(self):
            success = True
            value = None
            if self.query_type == adi.AdiEnums.QueryValueType.BitDepth: value = f"{self.client_local.server._v_current.bit_depth:.2f}"
            elif self.query_type == adi.AdiEnums.QueryValueType.HoleDepth: value = f"{self.client_local.server._v_current.hole_depth:.2f}"
            elif self.query_type == adi.AdiEnums.QueryValueType.RunNumber: value = f"{self.client_local.server._v_current.run:04}"
            elif self.query_type == adi.AdiEnums.QueryValueType.WellId: value = self.client_local.server._v_current.well
            elif self.query_type == adi.AdiEnums.QueryValueType.DrillModelDescriptor: value = self.client_local.server._v_current.drill_model_desc
            elif self.query_type == adi.AdiEnums.QueryValueType.LithologyDescriptor: value = self.client_local.server._v_current.lithology_desc
            elif self.query_type == adi.AdiEnums.QueryValueType.SurveyDescriptor: value = self.client_local.server._v_current.survey_desc
            else: success = False
            return {"Success": success, "Value": value}

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            value = result["Value"]
            if value is None: value = ""
            bytes_value = toUTF8Array(value)
            length = len(bytes_value) + 1
            if length < 32: length = 32
            data = struct.pack(f"<{length}s", bytes_value)
            return adi.AdiDefinitions.AdiResponse(data=data)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.query_type.value)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.length > 0
            value = None
            if success:
                [value] = struct.unpack_from(f"<{response.length}s", response.data)
                value = "" if len(value) == 0 else fromArrayToUTF8(value)
            return {"Success": success, "Value": value}

    # 0x2021 - CMD_QUERY_INT_VALUE
    class QueryIntValue(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2021

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            query_type = adi.AdiEnums.QueryValueType(header.param)
            return AdiCommands.QueryIntValue(client=client, query_type=query_type)

        def __init__(self, client=None, query_type=None):
            super().__init__(name="CMD_QUERY_INT_VALUE", code=self.GetCode(), client=client)
            self.query_type = query_type
            # print(f"Params: query_type={self.query_type}")
            self.is_valid = True

        def GetDetails(self):
            if not self.is_valid: return "Invalid query"
            return f"{self.query_type}"

        async def GetLocalResult(self):
            success = True
            value = 0
            if self.query_type == adi.AdiEnums.QueryValueType.RunNumber:
                value = int(self.client_local.server._v_current.run)
            elif self.query_type == adi.AdiEnums.QueryValueType.BitDepth:
                value = int(self.client_local.server._v_current.bit_depth)
            elif self.query_type == adi.AdiEnums.QueryValueType.HoleDepth:
                value = int(self.client_local.server._v_current.bit_depth)
            elif self.query_type == adi.AdiEnums.QueryValueType.TimeDepthActivity:
                value = self.client_local.server._v_current.activity
            else: success = False
            return {"Success": success, "Value": value}

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            value = result["Value"]
            return adi.AdiDefinitions.AdiResponse(value=value)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.query_type.value)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0
            value = None
            if success:
                value = response.value
            return {"Success": success, "Value": value}

    # 0x2022 - CMD_QUERY_DOUBLE_VALUE
    class QueryDoubleValue(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2022

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            query_type = adi.AdiEnums.QueryValueType(header.param)
            return AdiCommands.QueryDoubleValue(client=client, query_type=query_type)

        def __init__(self, client=None, query_type=None):
            super().__init__(name="CMD_QUERY_DOUBLE_VALUE", code=self.GetCode(), client=client)
            self.query_type = query_type
            # print(f"Params: query_type={self.query_type}")
            self.is_valid = True

        async def GetLocalResult(self):
            success = True
            value = 0.0
            if self.query_type == adi.AdiEnums.QueryValueType.RunNumber:
                value = self.client_local.server._v_current.run
            elif self.query_type == adi.AdiEnums.QueryValueType.BitDepth:
                value = self.client_local.server._v_current.bit_depth
            elif self.query_type == adi.AdiEnums.QueryValueType.HoleDepth:
                value = self.client_local.server._v_current.bit_depth
            elif self.query_type == adi.AdiEnums.QueryValueType.TimeDepthActivity:
                value = float(self.client_local.server._v_current.activity)
            else: success = False
            return {"Success": success, "Value": value}

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            value = result["Value"]
            data = struct.pack("<d", value)
            return adi.AdiDefinitions.AdiResponse(value=value, data=data)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.query_type.value)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.length == 8
            value = None
            if success:
                [value] = struct.unpack_from("<d", bytes(response.data))
            return {"Success": success, "Value": value}

    # 0x203e - CMD_QUERY_RUN_NUMBER
    class QueryRunNumber(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x203e

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            number_queries, run_alias = struct.unpack_from(f"<I{header.length - 4}s", data, 16)
            run_alias = fromArrayToUTF8(run_alias)
            return AdiCommands.QueryRunNumber(client=client, run_alias=run_alias)

        def __init__(self, client=None, well=None, run_alias=None):
            super().__init__(name="CMD_QUERY_RUN_NUMBER", code=self.GetCode(), client=client)
            self.well = well
            self.run_alias = run_alias
            self.is_valid = self.run_alias is not None

        async def GetLocalResult(self):
            run_number = await self.client_local.server.GetRunNumberByAlias(self.run_alias)
            result = {"Success": run_number is not None}
            if run_number is not None: result["RunNumber"] = run_number
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            elif result["RunNumber"] is None: return adi.AdiDefinitions.AdiResponse(param=0x08)
            bytes_data = struct.pack(f"<H", result["RunNumber"])
            return adi.AdiDefinitions.AdiResponse(length=len(bytes_data), data=bytes_data)

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<I65s", 1, toUTF8Array("" if self.run_alias is None else self.run_alias))
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length == 2
            result = {"Success": success}
            if success: [result["RunNumber"]] = struct.unpack_from("<H", response.data)
            return result

    # 0x2043 - CMD_QUERY_DATASETS
    class QueryWellRunRecordDesc(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2043

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            active_filters = None
            well = None
            run_number = None
            run_alias = None
            record = None
            description = None
            index_types = None
            unknown2 = None
            try:
                _, active_filters, run_number, record, well, description, run_alias, index_types, unknown1, unknown2 = struct.unpack_from(
                    "<IHH16s16s402s66sIII", bytes(data[16:]))
                if active_filters & adi.AdiEnums.QueryFilterModes.WELL.value:
                    well = fromArrayToUTF8(well).strip()
                else:
                    well = None
                if active_filters & adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value:
                    run_number = run_number
                else:
                    run_number = None
                if active_filters & adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value:
                    run_alias = fromArrayToUTF8(run_alias)
                else:
                    run_alias = None
                if active_filters & adi.AdiEnums.QueryFilterModes.RECORD.value:
                    record = fromArrayToUTF8(record).strip()
                else:
                    record = None
                if active_filters & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value:
                    description = fromArrayToUTF8(description).strip()
                else:
                    description = None
            except:
                active_filters = None
            return AdiCommands.QueryWellRunRecordDesc(client, active_filters=active_filters, well=well, run_number=run_number, run_alias=run_alias, record=record, description=description, index_types=index_types, unknown1=unknown1, unknown2=unknown2)

        def __init__(self, client=None, active_filters=0x00, well=None, run_number=None, run_alias=None, record=None, description=None, index_types=0x00, show_hidden=False, unknown1=1, output_format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE):
            super().__init__(name="CMD_QUERY_DATASETS", code=self.GetCode(), client=client)
            self.active_filters = active_filters
            self.well = well
            self.run_number = run_number
            self.run_alias = run_alias
            self.record = record
            self.description = description
            self.index_types = index_types
            self.show_hidden = show_hidden
            self.unknown1 = unknown1
            self.output_format = output_format
            self.is_valid = self.active_filters is not None
            if self.index_types % 0x10 == 0: self.is_valid = False

        async def GetLocalResult(self):
            datasets = await self.client_local.server.GetDatasets(
                well = self.well if self.active_filters & adi.AdiEnums.QueryFilterModes.WELL.value else None,
                run_number = self.run_number if self.active_filters & adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value else None,
                run_alias = self.run_alias if self.active_filters & adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value else None,
                record = self.record if self.active_filters & adi.AdiEnums.QueryFilterModes.RECORD.value else None,
                description = self.description if self.active_filters & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value else None
            )
            result = {"Success": datasets is not None}
            if datasets is not None: result["DataSets"] = datasets
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            datasets = result["DataSets"]

            data = struct.pack(f"<I", len(datasets))
            counter = 1
            for ds in datasets:
                bits_presence = 2
                if ds.well is not None: bits_presence |= adi.AdiEnums.QueryFilterModes.WELL.value
                if ds.run_number is not None: bits_presence |= adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value
                if ds.record is not None: bits_presence |= adi.AdiEnums.QueryFilterModes.RECORD.value
                if ds.description is not None and ds.description != "": bits_presence |= adi.AdiEnums.QueryFilterModes.DESCRIPTION.value
                data += struct.pack(f"<IHH16s16s32sII362s66s", 0x01, bits_presence, ds.run_number,
                                    toUTF8Array(ds.record),
                                    toUTF8Array(ds.well),
                                    toUTF8Array(ds.description),
                                    counter, 0, b'',
                                    toUTF8Array(ds.run_alias))
                counter += 1
            response = adi.AdiDefinitions.AdiResponse(data=data)
            return response

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<IHH16s16s402s66sIII", 1, self.active_filters,
                                    0 if self.run_number is None else self.run_number,
                                    toUTF8Array(self.record),
                                    toUTF8Array(self.well),
                                    toUTF8Array(self.description),
                                    toUTF8Array(self.run_alias),
                                    self.index_types, self.unknown1, 0 if self.show_hidden else 1)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=self.output_format.value, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.length > 0
            datasets = []
            if success:
                # try:
                [length] = struct.unpack_from(f"<I", response.data)
                if response.length != 4 + length * (8 + 64 + 8 + 362 + 66):
                    success = False
                else:
                    for i in range(length):
                        u1, bits_presence, run_number, record, well, description, counter, u3, u4, run_alias = struct.unpack_from(
                            "<IHH16s16s32sII362s66s", response.data, 4 + i * 508)
                        if bits_presence & adi.AdiEnums.QueryFilterModes.WELL.value == 0: raise Exception("Well should be present!!!")
                        if bits_presence & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value) == 0: raise Exception("Well should be present!!!")
                        if bits_presence & adi.AdiEnums.QueryFilterModes.RECORD.value == 0: raise Exception("Well should be present!!!")
                        if bits_presence & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value == 0: description = b''
                        new_line = adi.AdiDefinitions.AdiDataSetPrimaryKey(fromArrayToUTF8(well), fromArrayToUTF8(run_alias),
                            run_number, fromArrayToUTF8(record), fromArrayToUTF8(description))
                        if u1 != 1: print(f"({counter - 1}) === U1 = {hex(u1)}; should be 0x01")
                        # if bits_presence != 0x1f: print(f"({counter - 1}) === bits_presence = {hex(bits_presence)}; should be 0x1f; {new_line}")
                        # if u3 != 0x64bb6d57: print(f"({counter - 1}) === U3 = {hex(u3)}; should be 0x64bb6d57")
                        if u4[0] != 0: print(f"({counter - 1}) === U4 has some value (first is {u4[0]})!!!")
                        datasets.append(new_line)
                # except:
                #     success = False
                #     datasets = []
            return {"Success": success, "DataSets": datasets}

    # 0x2044 - CMD_QUERY_NUMBER_DATASETS
    class QueryDataSetExists(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2044

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            active_filters = None
            well = None
            run_number = None
            run_alias = None
            record = None
            description = None
            index_types = None
            unknown2 = None
            try:
                _, active_filters, run_number, record, well, description, run_alias, index_types, unknown1, unknown2 = struct.unpack_from("<IHH16s16s402s66s", data, 16)
                if active_filters & adi.AdiEnums.QueryFilterModes.WELL.value:
                    well = fromArrayToUTF8(well).strip()
                else:
                    well = None
                if active_filters & adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value:
                    run_number = run_number
                else:
                    run_number = None
                if active_filters & adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value:
                    run_alias = fromArrayToUTF8(run_alias)
                else:
                    run_alias = None
                if active_filters & adi.AdiEnums.QueryFilterModes.RECORD.value:
                    record = fromArrayToUTF8(record).strip()
                else:
                    record = None
                if active_filters & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value:
                    description = fromArrayToUTF8(description).strip()
                else:
                    description = None
            except:
                active_filters = None
            return AdiCommands.QueryDataSetExists(client, active_filters=active_filters, well=well, run_number=run_number, run_alias=run_alias, record=record, description=description, index_types=index_types, unknown1=unknown1, unknown2=unknown2)

        def __init__(self, client=None, active_filters=None, well=None, run_number=None, run_alias=None, record=None, description=None):
            super().__init__(name="CMD_QUERY_NUMBER_DATASETS", code=self.GetCode(), client=client)
            self.active_filters = active_filters
            self.well = well
            self.run_number = run_number
            self.run_alias = run_alias
            self.record = record
            self.description = description
            if self.active_filters is None:
                self.active_filters = 0
                if self.well is not None: self.active_filters |= adi.AdiEnums.QueryFilterModes.WELL.value
                if self.run_number is not None: self.active_filters |= adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value
                if self.run_alias is not None: self.active_filters |= adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value
                if self.record is not None: self.active_filters |= adi.AdiEnums.QueryFilterModes.RECORD.value
                if self.description is not None: self.active_filters |= adi.AdiEnums.QueryFilterModes.DESCRIPTION.value

            self.is_valid = self.active_filters is not None

        async def GetLocalResult(self):
            result = await self.client_local.server.QueryNumberDatasets(
                well = self.well if self.active_filters & adi.AdiEnums.QueryFilterModes.WELL.value else None,
                run_number = self.run_number if self.active_filters & adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value else None,
                run_alias = self.run_alias if self.active_filters & adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value else None,
                record = self.record if self.active_filters & adi.AdiEnums.QueryFilterModes.RECORD.value else None,
                description = self.description if self.active_filters & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value else None
            )
            result = {"Success": result is not None}
            if result is not None: result["NumberDatasets"] = result
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            return adi.AdiDefinitions.AdiResponse(value=0x01 if result["NumberDatasets"] else 0x00)

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<IHH16s16s402s66s", 1, self.active_filters,
                                    0 if self.run_number is None else self.run_number,
                                    toUTF8Array(self.record),
                                    toUTF8Array(self.well),
                                    toUTF8Array(self.description),
                                    toUTF8Array(self.run_alias))
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            number_datasets = response.value
            result = { "Success": success }
            if success: result["NumberDatasets"] = number_datasets
            return result

    # 0x2045 - CMD_UNKNOWN_02
    class Unknown02(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2045

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            param = 0
            if header.param == 0 and header.length == 4:
                [param] = struct.unpack_from("<I", data, 16)
            return AdiCommands.Unknown02(client=client, param=param)

        def __init__(self, client=None, param=0):
            super().__init__(name="CMD_UNKNOWN_02", code=self.GetCode(), client=client)
            self.param = param
            self.is_valid = True

        async def GetLocalResult(self):
            return { "Success": False }

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            data = struct.pack("<IIIII", result["U1"], result["U2"], result["U3"], result["U4"], result["U5"])
            return adi.AdiDefinitions.AdiResponse(data=data)

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack("<I", self.param)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length > 0
            result = {"Success": success}
            if success:
                u1, u2, u3, u4, u5 = struct.unpack_from("<IIIII", response.data)
                result = {"Success": True, "U1": u1, "U2": u2, "U3": u3, "U4": u4, "U5": u5}
            return result

    # 0x2049 - CMD_QUERY_UDNOTIBYNAME
    class QueryUDNotiByName(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2049

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            bytes_data = bytes(data[16:])
            length, name = struct.unpack_from(
                f"<I{len(bytes_data) - 4}s", bytes_data)
            return AdiCommands.QueryUDNotiByName(client=client, name=fromArrayToUTF8(name))

        def __init__(self, client=None, name=None):
            super().__init__(name="CMD_QUERY_UDNOTIBYNAME", code=self.GetCode(), client=client)
            self.name = name
            # print(f"Params: name=\"{self.name}\"")
            self.is_valid = self.name is not None

        async def GetLocalResult(self):
            return { "Success": False }

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            data = struct.pack("<IIIII", result["U1"], result["U2"], result["U3"], result["U4"], result["U5"])
            return adi.AdiDefinitions.AdiResponse(data=data)

        def BuildCommandBinaryData(self):
            bytes_name = toUTF8Array(self.name)
            length = len(bytes_name) + 1
            bytes_data = struct.pack(f"<I{length}s", length, bytes_name)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length > 0
            result = {"Success": success}
            if success:
                u1, u2, u3, u4, u5 = struct.unpack_from("<IIIII", response.data)
                result = {"Success": True, "U1": u1, "U2": u2, "U3": u3, "U4": u4, "U5": u5}
            return result

    # 0x2051 - CMD_QUERY_RECORDS_BY_PSL_TYPES
    class QueryAllRecords(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2051

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            filter1 = 0x00
            filter2 = 0x01
            psl_types = 0x00
            filter4 = 0x00
            cmd = AdiCommands.QueryAllRecords(client, psl_types=psl_types)
            if header.length == 16:
                [filter1, filter2, psl_types, filter4] = struct.unpack_from("<IIII", data, 16)
                cmd.filter1 = filter1
                cmd.filter2 = filter2
                cmd.psl_types = psl_types
                cmd.filter4 = filter4
            else: cmd.is_valid = False
            return cmd

        def __init__(self, client=None, psl_types=0):
            super().__init__(name="CMD_QUERY_RECORDS_BY_PSL_TYPES", code=self.GetCode(), client=client)
            self.filter1 = 0x00
            self.filter2 = 0x01
            self.psl_types = psl_types
            self.filter4 = 0x00
            self.is_valid = True

        async def GetLocalResult(self):
            records = await self.client_local.server.GetRecordsListByPslTypes(self.psl_types)
            result = {"Success": records is not None}
            if records is not None: result["Records"] = records
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            records = result["Records"]
            data = b''
            for record in records:
                data += struct.pack(f"<16s", toUTF8Array(record))
            return adi.AdiDefinitions.AdiResponse(value=len(records), data=data)

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack("<IIII", self.filter1, self.filter2, self.psl_types, self.filter4)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0 and response.length >= response.value * 16
            result = {}
            if success:
                try:
                    records = []
                    for i in range(response.value):
                        [record] = struct.unpack_from("<16s", response.data, i * 16)
                        record = fromArrayToUTF8(record)
                        records.append(record)
                    result["Records"] = records
                except Exception as ex:
                    success = False
            result["Success"] = success
            return result

    # 0x2052 - CMD_QUERY_RECORD_LIST
    class QueryRecordsList(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2052

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            active_filters = None
            well = None
            run_number = None
            record = None
            description = None
            show_hidden = None
            unknown1 = None
            unknown2 = None
            unknown3 = None
            try:
                active_filters, run_number, record, well, description, unknown1, unknown2, unknown3, show_hidden = struct.unpack_from(
                    "<HH16s16s32sIIII", bytes(data[16:]))
                if active_filters & adi.AdiEnums.QueryFilterModes.WELL.value:
                    well = fromArrayToUTF8(well).strip()
                else:
                    well = None
                if active_filters & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value):
                    run_number = run_number
                else:
                    run_number = None
                if active_filters & adi.AdiEnums.QueryFilterModes.RECORD.value:
                    record = fromArrayToUTF8(record).strip()
                else:
                    record = None
                if active_filters & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value:
                    description = fromArrayToUTF8(description).strip()
                else:
                    description = None
                show_hidden = show_hidden == 0
            except:
                active_filters = None
            return AdiCommands.QueryRecordsList(client, active_filters, well, run_number, record, description, show_hidden, unknown1, unknown2, unknown3)

        def __init__(self, client=None, active_filters=0x00, well=None, run_number=None, record=None, description=None, show_hidden=False, unknown1=0x00, unknown2=0x01, unknown3=0x00, output_format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE):
            super().__init__(name="CMD_QUERY_RECORD_LIST", code=self.GetCode(), client=client)
            self.active_filters = active_filters
            self.well = well
            self.run_number = run_number
            self.record = record
            self.description = description
            self.show_hidden = show_hidden
            self.unknown1 = unknown1
            self.unknown2 = unknown2
            self.unknown3 = unknown3
            self.output_format = output_format
            # print(f"Params: active_filters={self.active_filters}, well={self.well}, run_number={self.run_number}, record={self.record}, description={self.description}, show_hidden={self.show_hidden}, unknown1={unknown1}, unknown2={unknown2}, unknown3={unknown3}, output_format={self.output_format}")
            # print(f"== {hex(self.GetCode())} - {self.name}")
            # print(f"Params: show_hidden={self.show_hidden}, unknown1={self.unknown1}, unknown2={self.unknown2}, unknown3={unknown3}")
            self.is_valid = self.active_filters is not None

        async def GetLocalResult(self):
            records = await self.client_local.server.GetRecordsList(
                well = self.well if self.active_filters & adi.AdiEnums.QueryFilterModes.WELL.value else None,
                run_number = self.run_number if self.active_filters & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value) else None,
                record = self.record if self.active_filters & adi.AdiEnums.QueryFilterModes.RECORD.value else None,
                description = self.description if self.active_filters & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value else None,
            )
            result = {"Success": records is not None}
            if records is not None: result["Records"] = records
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)

            data = struct.pack(f"<I", len(result["Records"]))
            for record in result["Records"]:
                data += struct.pack(f"<16s", toUTF8Array(record))
            response = adi.AdiDefinitions.AdiResponse(data=data)
            return response

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<HH16s16s32sIIII", self.active_filters, 0 if self.run_number is None else self.run_number,
                                    toUTF8Array(self.record),
                                    toUTF8Array(self.well),
                                    toUTF8Array(self.description),
                                    self.unknown1, self.unknown2, self.unknown3, 0 if self.show_hidden else 0x04)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=self.output_format.value, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length >= 4
            result = {"Success": success}
            if success:
                [length] = struct.unpack_from(f"<I", response.data)
                if length * 16 + 4 == response.length:
                    records = []
                    for i in range(length):
                        [name] = struct.unpack_from(f"<16s", response.data, 4 + i * 16)
                        name = fromArrayToUTF8(name)
                        records.append(name)
                    result["Records"] = records
                else: result["Success"] = False
            return result

    # 0x205a - CMD_QUERY_RECORD_ATTRIBUTES_XML
    class QueryRecordAttributesEx(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x205a

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            [record_name] = struct.unpack_from(f"<{header.length}s", data, 16)
            record_name = fromArrayToUTF8(record_name)
            return AdiCommands.QueryRecordAttributesEx(client=client, record_name=record_name)

        def __init__(self, client=None, record_name=None, output_format=adi.AdiEnums.OutputFormat.BINARY_FULL):
            super().__init__(name="CMD_QUERY_RECORD_ATTRIBUTES", code=self.GetCode(), client=client, output_format=output_format)
            self.record_name = record_name
            self.is_valid = self.record_name is not None

        async def GetLocalResult(self):
            record = await self.client_local.server.GetRecordAttributes(self.record_name)
            result = {"Success": record is not None}
            if record is not None: result["Record"] = record
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)

            record:adi.AdiDefinitions.AdiRecord = result["Record"]
            str_data = toUTF8Array("<?xml version=1.0?>" + \
                "<RecordAttributeInfoEx>" + \
                f"<RecordName>{record.name}</RecordName>" + \
                f"<RecordType>{record.record_type_id}</RecordType>" + \
                f"<RecordIndexTypes>{record.index_types}</RecordIndexTypes>" + \
                f"<NumberOfVariables>{record.number_variables}</NumberOfVariables>" + \
                f"<RecordDisplayGroup>{record.category_id}</RecordDisplayGroup>" + \
                f"<PKWellIdFlag>{2 if record.primary_keys & adi.AdiDefinitions.RecordPrimaryKeys.Well.value != 0 else 0}</PKWellIdFlag>" + \
                f"<PKBitRunFlag>{2 if record.primary_keys & adi.AdiDefinitions.RecordPrimaryKeys.BitRun.value != 0 else 0}</PKBitRunFlag>" + \
                f"<Unused>0</Unused>" + \
                f"<PKDescriptionFlag>{2 if record.primary_keys & adi.AdiDefinitions.RecordPrimaryKeys.Description.value != 0 else 0}</PKDescriptionFlag>" + \
                f"<PSLTypes>{record.psl_types}</PSLTypes>" + \
                f"<Hidden>{1 if record.attributes & adi.AdiEnums.RecordAttributes.Hidden.value != 0 else 0}</Hidden>" + \
                f"<ReadOnly>{1 if record.attributes & adi.AdiEnums.RecordAttributes.ReadOnly.value != 0 else 0}</ReadOnly>" + \
                f"<DefinitionLock>{1 if record.attributes & adi.AdiEnums.RecordAttributes.Locked.value != 0 else 0}</DefinitionLock>" + \
                "</RecordAttributeInfoEx>")
            length = len(str_data)
            data = struct.pack(f"<{length}s", str_data)

            response = adi.AdiDefinitions.AdiResponse(length=len(data), data=data)
            return response

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<16s", toUTF8Array(self.record_name))
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.value == 0 and response.length > 0
            result = {"Success": success}
            if success:
                try:
                    length = response.length
                    [xml] = struct.unpack_from(f"{length}s", response.data)
                    xml = fromArrayToUTF8(xml)
                    def GetXMLTagValue(tag):
                        start = xml.find(f"<{tag}>")
                        end = xml.find(f"</{tag}>")
                        length = end - (start + len(tag) + 2)
                        if start > 0 and end > start: return "" if length == 0 else xml[start + len(tag) + 2:end]
                        return None
                    primary_keys = 0
                    if GetXMLTagValue("PKWellIdFlag") == "1": primary_keys += adi.AdiDefinitions.RecordPrimaryKeys.Well.value
                    if GetXMLTagValue("PKBitRunFlag") == "1": primary_keys += adi.AdiDefinitions.RecordPrimaryKeys.BitRun.value
                    if GetXMLTagValue("PKDescriptionFlag") == "1": primary_keys += adi.AdiDefinitions.RecordPrimaryKeys.Description.value
                    attributes = 0
                    if GetXMLTagValue("Hidden") == "1": attributes += adi.AdiEnums.RecordAttributes.Hidden.value
                    if GetXMLTagValue("ReadOnly") == "1": attributes += adi.AdiEnums.RecordAttributes.ReadOnly.value
                    if GetXMLTagValue("DefinitionLock") == "1": attributes += adi.AdiEnums.RecordAttributes.Locked.value
                    record = adi.AdiDefinitions.AdiRecord(
                        name=GetXMLTagValue("RecordName"),
                        record_type_id=int(GetXMLTagValue("RecordType")),
                        index_types=int(GetXMLTagValue("RecordIndexTypes")),
                        number_variables=int(GetXMLTagValue("NumberOfVariables")),
                        category_id=int(GetXMLTagValue("RecordDisplayGroup")),
                        psl_types=int(GetXMLTagValue("PSLTypes")),
                        primary_keys=primary_keys,
                        attributes=attributes)
                    result["Record"] = record
                except Exception as ex:
                    result["Success"] = False
            return result

    # 0x205e - CMD_QUERY_VARS_INFO
    class QueryVariablesInfo(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x205e

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            variables = None
            output_format = adi.AdiEnums.OutputFormat(header.format)
            if adi.AdiEnums.OutputFormat.BINARY_SIMPLE in output_format and header.length == 16:
                [var_name] = struct.unpack_from(f"<16s", data, 16)
                var_name = fromArrayToUTF8(var_name)
                variables = [var_name]
            elif adi.AdiEnums.OutputFormat.BINARY_FULL in output_format and header.length > 16:
                [number_variables] = struct.unpack_from("<I", data, 16)
                if header.length == 4 + 16 * number_variables:
                    variables = []
                    for i in range(number_variables):
                        [var_name] = struct.unpack_from(f"<16s", data, 20 + i * 16)
                        variables.append(fromArrayToUTF8(var_name))
            return AdiCommands.QueryVariablesInfo(client=client, variables=variables, output_format=adi.AdiEnums.OutputFormat(header.format))

        def __init__(self, client=None, variables=None, output_format=adi.AdiEnums.OutputFormat.BINARY_FULL):
            super().__init__(name="CMD_QUERY_VARS_INFO", code=self.GetCode(), client=client, output_format=output_format)
            self.variables = variables
            if self.variables is not None:
                pattern = re.compile(r"^[^\[]+\[[0-9]+\]")
                for v in self.variables:
                    if v is not None and "[" in v and not pattern.match(v):
                        self.variables = None
                        break
            self.is_valid = self.variables is not None and (
                (adi.AdiEnums.OutputFormat.BINARY_SIMPLE in output_format and len(self.variables) == 1)
                or
                adi.AdiEnums.OutputFormat.BINARY_FULL in output_format
            )

        async def GetLocalResult(self):
            variables = []
            for variable in self.variables:
                variables.append(await self.client_local.server.GetVariable(variable))
            result = { "Success": True, "Variables": variables }
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            try:
                def GetVariableXMLUTF8Array(v, rv):
                    str_data = toUTF8Array("<?xml version=1.0?>" + \
                        "<ServerVariable>" + \
                        f"<InternalName>{v.name}</InternalName>" + \
                        f"<Mnemonic>{'' if rv.mnemonic is None else rv.mnemonic}</Mnemonic>" + \
                        f"<CurveLabel>{'' if rv.curve_label is None else rv.curve_label}</CurveLabel>" + \
                        f"<Format>{v.GetStorageType().value}</Format>" + \
                        f"<NumberOfBytes>{v.size if v.number_of_elements == 1 else v.number_of_elements}</NumberOfBytes>" + \
                        f"<UnitType>{v.unit_type_id}</UnitType>" + \
                        f"<SpecialHandling>{v.special}</SpecialHandling>" + \
                        f"<NumberOfDecimalPlaces>{v.number_of_decimals}</NumberOfDecimalPlaces>" + \
                        f"<OffsetInRecord>{v.offset}</OffsetInRecord>" + \
                        f"<Mnemonic32>{'' if rv.mnemonic32 is None else rv.mnemonic32}</Mnemonic32>" + \
                        f"<Algorithm></Algorithm>" + \
                        f"<Ref Variable></Ref Variable>" + \
                        f"<Coeff1></Coeff1>" + \
                        f"<Coeff2></Coeff2>" + \
                        f"<Coeff3></Coeff3>" + \
                        "</ServerVariable>")
                    return str_data
                header_value = 0 if adi.AdiEnums.OutputFormat.BINARY_SIMPLE in self.output_format else len(result["Variables"])
                data = b''
                for v in result["Variables"]:
                    bytes_xml = b''
                    if v is not None:
                        rv = v.record_variable_data
                        bytes_xml = GetVariableXMLUTF8Array(v, rv)
                    length = len(bytes_xml)
                    if adi.AdiEnums.OutputFormat.BINARY_SIMPLE in self.output_format:
                        data += struct.pack(f"<{length}s", bytes_xml)
                    else:
                        data += struct.pack(f"<I{length}s", length, bytes_xml)
                return adi.AdiDefinitions.AdiResponse(length=len(data), value=header_value, data=data)
            except Exception as ex:
                return adi.AdiDefinitions.AdiResponse(param=0x01)

        def BuildCommandBinaryData(self):
            bytes_data = b''
            if self.variables is not None:
                if adi.AdiEnums.OutputFormat.BINARY_SIMPLE in self.output_format:
                    bytes_data += struct.pack("<16s", toUTF8Array(self.variables[0]))
                elif adi.AdiEnums.OutputFormat.BINARY_FULL in self.output_format:
                    bytes_data += struct.pack("I", len(self.variables))
                    for v in self.variables:
                        bytes_data += struct.pack("<16s", toUTF8Array(v))
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=self.output_format.value, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            # If the output format type is set to 1 (BINARY_SIMPLE),
            # then response data comes only XML, being its length
            # the one presented in the header (response.length).
            #
            # If the output is format type 2 (BINARY_FULL), then
            # response data comes for multiple variables, being formatted
            # as "<I{length}s", with I being the length of XML and the
            # XML right after.
            success = response.param == 0x00 and response.length > 4
            result = { "Success": True }
            if success:
                try:
                    number_variables = 1 if adi.AdiEnums.OutputFormat.BINARY_SIMPLE in self.output_format else response.value
                    xml_length = response.length if adi.AdiEnums.OutputFormat.BINARY_SIMPLE in self.output_format else struct.unpack_from("<I", response.data)[0]
                    ix = 0 if adi.AdiEnums.OutputFormat.BINARY_SIMPLE in self.output_format else 4
                    variables = []
                    v = None
                    for i in range(number_variables):
                        v = None
                        rv = None
                        if xml_length > 0:
                            [xml] = struct.unpack_from(f"{xml_length}s", response.data, ix)
                            xml = fromArrayToUTF8(xml)
                            def GetXMLTagValue(tag):
                                start = xml.find(f"<{tag}>")
                                end = xml.find(f"</{tag}>")
                                length = end - (start + len(tag) + 2)
                                if start > 0 and end > start: return "" if length == 0 else xml[start + len(tag) + 2:end]
                                return None
                            coeff1 = GetXMLTagValue("Coeff1")
                            coeff1 = 0 if coeff1 == "" else float(coeff1)
                            coeff2 = GetXMLTagValue("Coeff2")
                            coeff2 = 0 if coeff2 == "" else float(coeff2)
                            coeff3 = GetXMLTagValue("Coeff3")
                            coeff3 = 0 if coeff3 == "" else float(coeff3)
                            rv = adi.AdiDefinitions.AdiRecordVariable(
                                mnemonic=GetXMLTagValue("Mnemonic"),
                                curve_label=GetXMLTagValue("CurveLabel"),
                                mnemonic32=GetXMLTagValue("Mnemonic32"),
                                algorithm=GetXMLTagValue("Algorithm"),
                                ref_variable=GetXMLTagValue("RefVariable"),
                                coeff1=coeff1,
                                coeff2=coeff2,
                                coeff3=coeff3)
                            v = adi.AdiDefinitions.AdiVariable(
                                name=GetXMLTagValue("InternalName"),
                                format=adi.AdiEnums.StorageType(int(GetXMLTagValue("Format"))),
                                size=int(GetXMLTagValue("NumberOfBytes")),
                                unit_type_id=int(GetXMLTagValue("UnitType")),
                                special=int(GetXMLTagValue("SpecialHandling")),
                                number_of_decimals=int(GetXMLTagValue("NumberOfDecimalPlaces")),
                                offset=int(GetXMLTagValue("OffsetInRecord")),
                                record_variable_data=rv)
                            
                            # Adding a reference to the unit type object, if exists
                            unit_types = None
                            if self.client is not None and hasattr(self.client, 'unit_types') and self.client.unit_types is not None: unit_types = self.client.unit_types
                            elif self.client is not None and self.client_local.server is not None and self.client_local.server.unit_types is not None: unit_types = self.client_local.server.unit_types
                            if unit_types is not None and len(unit_types) > v.unit_type_id: v.unit_type = unit_types[v.unit_type_id]
                            
                        variables.append(v)
                        ix += xml_length
                        if i < number_variables - 1:
                            # Getting data for the next variable
                            # This is very messy, just to accomodate both possibilities
                            # of BINARY_SIMPLE and BINARY_FULL output types
                            xml_length = struct.unpack_from("<I", response.data, ix)[0]
                            ix += 4
                    result["Variables"] = variables
                except Exception as ex:
                    result["Success"] = False
            return result

    # 0x2065 - CMD_QUERY_UNIT_TYPES_OPTIONS (multiple)
    class QueryUnitTypesOptions(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2065

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            unit_type_indexs = []
            if header.param == 0 and header.length >= 4:
                [length] = struct.unpack_from("<I", data, 16)
                if header.length == 4 + length * 4:
                    unit_type_indexs = struct.unpack_from(f"<{''.join(['I'] * length)}", data[20:])
            return AdiCommands.QueryUnitTypesOptions(client=client, unit_type_indexs=unit_type_indexs)

        def __init__(self, client=None, unit_type_indexs=[]):
            super().__init__(name="CMD_QUERY_UNIT_TYPES_OPTIONS", code=self.GetCode(), client=client)
            self.unit_type_indexs = unit_type_indexs
            self.is_valid = type(self.unit_type_indexs).__name__ == 'tuple'

        def GetDetails(self):
            if not self.is_valid: return "Invalid query"
            return f"{', '.join(map(str, self.unit_type_indexs))}"

        async def GetLocalResult(self):
            unit_types = []
            for unit_type_index in self.unit_type_indexs:
                unit_options = await self.client_local.server.GetUnitOptionsByUnitType(unit_type_index)
                unit_types.append(adi.AdiDefinitions.UnitType(id=unit_type_index, unit_options=unit_options))
            return { "Success": True, "UnitTypes": unit_types }

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if len(result["UnitTypes"]) == 0: return adi.AdiDefinitions.AdiResponse(param=0x08)
            
            bytes_data = b''
            for ut in result["UnitTypes"]:
                bytes_data += struct.pack("<I", len(ut.unit_options))
                for uo in ut.unit_options:
                    bytes_data += struct.pack("<16s16s", toUTF8Array(uo.long_name), toUTF8Array(uo.short_name))
            result = adi.AdiDefinitions.AdiResponse(value=len(self.unit_type_indexs), data=bytes_data)
            return result

        def BuildCommandBinaryData(self):
            length = len(self.unit_type_indexs)
            bytes_data = struct.pack("<I", length)
            if length > 0:
                bytes_data += struct.pack(f"<{''.join(['I'] * length)}", *self.unit_type_indexs)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data), format=3)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.value > 0 and response.length > 4
            result = {"Success": success}
            if success:
                try:
                    unit_types = []
                    if success:
                        ix = 0
                        for i in range(response.value):
                            unit_options = []
                            [number_options] = struct.unpack_from("<I", response.data, ix)
                            ix += 4
                            for j in range(number_options):
                                name_long, name_short = struct.unpack_from(f"<16s16s", response.data, ix)
                                ix += 32
                                unit_options.append(adi.AdiDefinitions.UnitOption(short_name=fromArrayToUTF8(name_short), long_name=fromArrayToUTF8(name_long)))
                            unit_type = adi.AdiDefinitions.UnitType(id=self.unit_type_indexs[i], unit_options=unit_options)
                            unit_types.append(unit_type)
                        result["UnitTypes"] = unit_types
                except Exception as ex:
                    result = {"Success": False}
            return result

    # 0x2066 - CMD_QUERY_UNIT_TYPE_OPTIONS (single)
    class QueryUnitTypeOptions(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2066

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            unit_type_index = header.param
            if header.length == 4:
                [unit_type_index] = struct.unpack_from("<I", data, 16)
            elif header.length == 0:
                print("Check this out!")
            else:
                print("DEFINITELY check this out!")
            return AdiCommands.QueryUnitTypeOptions(client=client, unit_type_index=unit_type_index)

        def __init__(self, client=None, unit_type_index=None):
            super().__init__(name="CMD_QUERY_UNIT_TYPE_OPTIONS", code=self.GetCode(), client=client)
            self.unit_type_index = unit_type_index
            self.is_valid = self.unit_type_index is not None

        def GetDetails(self):
            if not self.is_valid: return "Invalid query"
            return f"{self.unit_type_index}"

        async def GetLocalResult(self):
            unit_options = await self.client_local.server.GetUnitOptionsByUnitType(self.unit_type_index)
            result = {"Success": unit_options is not None}
            if unit_options is not None:
                result["UnitType"] = adi.AdiDefinitions.UnitType(id=self.unit_type_index, unit_options=unit_options)
            return result
        
        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            
            ut = result["UnitType"]
            bytes_data = b''
            for uo in ut.unit_options:
                bytes_data += struct.pack("<16s16s", toUTF8Array(uo.long_name), toUTF8Array(uo.short_name))
            result = adi.AdiDefinitions.AdiResponse(value=len(ut.unit_options), data=bytes_data)
            return result

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.unit_type_index)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length == response.value * 32
            result = {}
            if success:
                try:
                    if success:
                        unit_options = []
                        for i in range(response.value):
                            name_long, name_short = struct.unpack_from(f"<16s16s", response.data, i * 32)
                            unit_options.append(adi.AdiDefinitions.UnitOption(short_name=fromArrayToUTF8(name_short), long_name=fromArrayToUTF8(name_long)))
                        result["UnitType"] = adi.AdiDefinitions.UnitType(id=self.unit_type_index, unit_options=unit_options)
                except:
                    success = False
            result["Success"] = success
            return result

    # 0x206d - CMD_QUERY_VARIABLES_DECIMALS_PER_OPTION (multiple)
    class QueryVariablesDecimalsPerUnitOption(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x206d

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            variables = []
            if header.param == 0 and header.length >= 4:
                [length] = struct.unpack_from("<I", data, 16)
                if header.length == 4 + length * 20:
                    for i in range(length):
                        name, uo = struct.unpack_from(f"<16sI", data, 20 + i * 20)
                        name = fromArrayToUTF8(name)
                        variables.append({ "var_name": name, "unit_option": uo })
            return AdiCommands.QueryVariablesDecimalsPerUnitOption(client=client, variables=variables)

        def __init__(self, client=None, variables=[]):
            super().__init__(name="CMD_QUERY_VARIABLES_DECIMALS_PER_OPTION", code=self.GetCode(), client=client)
            self.variables = variables
            self.is_valid = len(self.variables) > 0

        async def GetLocalResult(self):
            try:
                number_decimals = []
                for v in self.variables:
                    number_decimals.append(await self.client_local.server.GetVariableDecimalsByUnitOption(v["var_name"], v["unit_option"]))
                return { "Success": True, "NumberDecimals": number_decimals }
            except:
                return {"Success": False}

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            
            bytes_data = b''
            for number_decimals in result["NumberDecimals"]:
                bytes_data += struct.pack("<I", number_decimals)
            result = adi.AdiDefinitions.AdiResponse(data=bytes_data)
            return result

        def BuildCommandBinaryData(self):
            length = len(self.variables)
            bytes_data = struct.pack("<I", length)
            if length > 0:
                for i in range(length):
                    bytes_data += struct.pack(f"<16sI", toUTF8Array(self.variables[i]["var_name"]), self.variables[i]["unit_option"])
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.value == 0 and response.length == 4 * len(self.variables)
            result = {"Success": success}
            if success:
                try:
                    number_decimals = []
                    if success:
                        for i in range(len(self.variables)):
                            [number] = struct.unpack_from("<I", response.data, i * 4)
                            number_decimals.append(number)
                        result["NumberDecimals"] = number_decimals
                except: result = {"Success": False}
            return result

    # 0x2071 - CMD_QUERY_UNITSET
    class QueryUnitSet(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2071

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.QueryUnitSet(client)

        def __init__(self, client=None):
            super().__init__(name="CMD_QUERY_UNITSET", code=self.GetCode(), client=client)
            self.is_valid = True

        async def GetLocalResult(self):
            return {"Success": True, "Value": self.client_local.server._v_current.unitset}

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            unitset = result["Value"]
            bytes_us = toUTF8Array(unitset)
            length = len(bytes_us) + 1
            data = struct.pack(f"<H{len(unitset) + 1}s", length, bytes_us)
            return adi.AdiDefinitions.AdiResponse(data=data)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0 and response.value == 0 and response.length > 2
            value = None
            if success:
                _, value = struct.unpack_from(
                    f"<H{response.length - 2}s", response.data)
                value = "" if len(value) == 0 else fromArrayToUTF8(value)
            return {"Success": success, "Value": value}

    # 0x2072 - CMD_QUERY_RUN_LIST
    class QueryRunList(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x2072

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            active_filters = 0
            well = None
            run_number = None
            run_alias = None
            record = None
            description = None
            index_types = 0xffffffff
            run_zero = False
            try:
                ix = 16
                u1, active_filters, run_number, record, well, description, run_alias, index_types, u2, u3, run_zero = struct.unpack_from("<IHH16s16s402s66sIIII", data, ix)
                well = None if active_filters & adi.AdiEnums.QueryFilterModes.WELL.value == 0 else fromArrayToUTF8(well)
                run_number = None if active_filters & adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value == 0 else run_number
                run_alias = None if active_filters & adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value == 0 else fromArrayToUTF8(run_alias)
                record = None if active_filters & adi.AdiEnums.QueryFilterModes.RECORD.value == 0 else fromArrayToUTF8(record)
                description = None if active_filters & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value == 0 else fromArrayToUTF8(description)
            except Exception as ex:
                active_filters = adi.AdiEnums.QueryFilterModes.WELL.value
                well = None
            
            return AdiCommands.QueryRunList(client=client, active_filters=active_filters, well=well, run_number=run_number, run_alias=run_alias, record=record, description=description, index_types=index_types, run_zero=run_zero == 1)

        def __init__(self, client=None, active_filters=0, well=None, run_number=None, run_alias=None, record=None, description=None, index_types=0xffffffff, run_zero=False):
            super().__init__(name="CMD_QUERY_RUN_LIST", code=self.GetCode(), client=client)
            self.active_filters = active_filters
            self.well = None if active_filters & adi.AdiEnums.QueryFilterModes.WELL.value == 0 else well
            self.run_number = None if active_filters & adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value == 0 else run_number
            self.run_alias = None if active_filters & adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value == 0 else run_alias
            self.record = None if active_filters & adi.AdiEnums.QueryFilterModes.RECORD.value == 0 else record
            self.description = None if active_filters & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value == 0 else description
            self.index_types = index_types
            self.run_zero = run_zero
            self.is_valid = True
            if self.active_filters & adi.AdiEnums.QueryFilterModes.WELL.value != 0 and self.well is None: self.is_valid = False
            if self.active_filters & adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value != 0 and self.run_number is None: self.is_valid = False
            if self.active_filters & adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value != 0 and self.run_alias is None: self.is_valid = False
            if self.index_types % 0x10 == 0: self.is_valid = False

        async def GetLocalResult(self):
            runs = await self.client_local.server.GetRunsList(
                well = self.well if self.active_filters & adi.AdiEnums.QueryFilterModes.WELL.value else None,
                run_number = self.run_number if self.active_filters & adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value else None,
                run_alias = self.run_alias if self.active_filters & adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value else None,
                record = self.record if self.active_filters & adi.AdiEnums.QueryFilterModes.RECORD.value else None,
                description = self.description if self.active_filters & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value else None
            )
            result = {"Success": runs is not None}
            if runs is not None:
                if not self.run_zero: runs = list(filter(lambda x: x != 0, runs))
                result["Runs"] = runs
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)

            try:
                data = struct.pack("<I", len(result["Runs"]))
            except Exception as ex:
                print(repr(ex))
            for run in result["Runs"]:
                data += struct.pack(f"<65s", toUTF8Array(run))
            response = adi.AdiDefinitions.AdiResponse(data=data)
            return response

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<IHH16s16s402s66sIIII",
                1,
                self.active_filters,
                0 if self.run_number is None else self.run_number,
                toUTF8Array(self.record),
                toUTF8Array(self.well),
                toUTF8Array(self.description),
                toUTF8Array(self.run_alias),
                self.index_types, 1, 0, 1 if self.run_zero else 0)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {}
            if success:
                try:
                    runs = []
                    [number_runs] = struct.unpack_from('<I', response.data)
                    for i in range(number_runs):
                        [run_alias] = struct.unpack_from("<65s", response.data, 4 + i * 65)
                        runs.append(fromArrayToUTF8(run_alias))
                    result["Runs"] = runs
                except Exception as ex:
                    success = False
            result["Success"] = success
            return result

    # 0x3011 - CMD_QUERY_TABLE_DEFINITIONS
    class QueryTableDefinitions(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x3011

        @staticmethod
        def CreateCommandFromBinaryData(client, *_):
            return AdiCommands.QueryTableDefinitions(client=client)

        def __init__(self, client=None):
            super().__init__(name="CMD_QUERY_TABLE_DEFINITIONS", code=self.GetCode(), client=client)
            self.is_valid = True

        async def GetLocalResult(self):
            raise Exception("Not implemented!")

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            raise Exception("Not implemented!")

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length >= 16
            result = {"Success": success}
            if success:
                try:
                    measurement_classes: dict[int, adi.AdiDefinitions.MeasurementClass] = {}
                    unit_types: dict[int, adi.AdiDefinitions.UnitType] = {}
                    variables: dict[str, adi.AdiDefinitions.AdiVariable] = {}
                    variables_by_id: dict[int, adi.AdiDefinitions.AdiVariable] = {}
                    var_ids_in_order = []   # List of variable IDs in order they appear
                    options_lists: dict[int, list[str]] = {}
                    records: dict[int, adi.AdiDefinitions.AdiRecord] = {}
                    rec_vars_wire_order = []

                    mv = memoryview(response.data)

                    # Performance note:
                    # --- tiny, fast decoders for fixed-size, null-terminated fields ---
                    def _cstr(b: bytes) -> str:
                        # split at first NUL, decode ASCII/UTF-8 (most of your text is ASCII)
                        i = b.find(0)
                        if i != -1:
                            b = b[:i]
                        # .strip() trims stray spaces your format pads with
                        return b.decode('utf-8', 'ignore').strip()

                    # Measurement Classes
                    # Format: 0x12345678 ? number_classes
                    #   followed by all classes with this format:
                    #   name, number_of_unit_types
                    #     followed by all unit types with this format:
                    #     short_name, long_name, arg1, arg2, function_type
                    [u1, u2, u3, number_classes] = struct.unpack_from("<IIII", response.data)
                    ix = 16
                    try:
                        for _ in range(number_classes):
                            name, number_units, id = struct.unpack_from(f"<16sHH", response.data, ix)
                            ix += 20
                            meas_class = adi.AdiDefinitions.MeasurementClass(id=id, name=fromArrayToUTF8(name))
                            for _ in range(number_units):
                                short_unit, long_unit, arg1, arg2, function_type, a1, a2, a3, a4 = struct.unpack_from(f"<16s16sddHBBBB", response.data, ix)
                                ix += 56
                                long_unit = fromArrayToUTF8(long_unit)
                                short_unit = fromArrayToUTF8(short_unit)
                                uo = adi.AdiDefinitions.UnitOption(short_name=short_unit, long_name=long_unit, function_type=function_type, arg1=arg1, arg2=arg2)
                                meas_class.unit_options.append(uo)
                            measurement_classes[meas_class.id] = meas_class
                    except Exception as ex:
                        print(repr(ex))
                        raise ex

                    # Units types
                    [number_units] = struct.unpack_from("<I", response.data, ix)
                    ix += 4
                    try:
                        _REC = struct.Struct("<16sHH")  # size = 20
                        block = mv[ix:ix + number_units * _REC.size]
                        _iter_unpack = struct.iter_unpack
                        for name_b, id_class, id_unit in _iter_unpack(_REC.format, block):
                            name  = _cstr(name_b)
                            ut = adi.AdiDefinitions.UnitType(id=id_unit, name=name, id_class=id_class, measurement_class=measurement_classes[id_class])
                            unit_types[id_unit] = ut
                    except Exception as ex:
                        print(repr(ex))
                        raise ex
                    ix += 20 * number_units
                    
                    # Variables
                    def parse_variables_block(mv: memoryview, ix: int, unit_types, variables, variables_by_id):
                        # Precompile struct once
                        _REC = struct.Struct("<16s5s27sHHHHHHI")  # size = 64
    
                        # 1) number of vars
                        number_variables, = struct.unpack_from("<I", mv, ix)
                        ix += 4

                        # 2) slice the exact block once (no per-row offset math in Python)
                        total = _REC.size * number_variables
                        block = mv[ix:ix + total]

                        # 3) bind locals (micro-optimizations)
                        _iter_unpack = struct.iter_unpack
                        _decode = _cstr
                        Var = adi.AdiDefinitions.AdiVariable
                        set_by_name = variables.__setitem__
                        set_by_id   = variables_by_id.__setitem__

                        # NOTE: skip enum + unit_type lookups here; link later
                        # StorageType_map = adi.AdiEnums.StorageType._value2member_map_  # if you insist on Enum

                        # 4) tight loop in C with minimal Python work
                        for name_b, mnem_b, label_b, fmt_code, size, unit_type_id, special, ndec, offset, vid in _iter_unpack(_REC.format, block):
                            name  = _decode(name_b)
                            mnem  = _decode(mnem_b)
                            label = _decode(label_b)

                            # Create the object with cheap primitives only
                            v = Var(
                                id=vid,
                                name=name,
                                mnemonic=mnem,
                                curve_label=label,
                                # format=StorageType_map.get(fmt_code) if you really need Enum now else:
                                format=fmt_code,                   # keep int; map to Enum later in one pass
                                size=size,
                                unit_type_id=unit_type_id,
                                unit_type=None,                    # link after the loop
                                special=special,
                                number_of_decimals=ndec,
                                offset=offset,
                            )

                            set_by_name(name, v)
                            set_by_id(vid, v)
                            var_ids_in_order.append(vid)

                        # 5) single linking pass (outside the hot loop)
                        # If you *need* unit_type objects on variables now:
                        get_ut = unit_types.get
                        for v in variables_by_id.values():
                            v.unit_type = get_ut(v.unit_type_id)

                        # If you *need* Enum objects:
                        # st_map = adi.AdiEnums.StorageType._value2member_map_
                        # for v in variables_by_id.values():
                        #     v.format = st_map.get(v.format, v.format)
                        
                        return ix + total  # new ix after the block
                    ix = parse_variables_block(mv, ix, unit_types, variables, variables_by_id)

                    # Options Lists (by variable name)
                    def parse_options_lists_block(mv: memoryview, ix: int,
                                                variables: dict,            # name -> AdiVariable
                                                options_lists: dict):       # keeps your int-keyed dict
                        # number of lists
                        n = int.from_bytes(mv[ix:ix+4], 'little'); ix += 4

                        OptionsList = adi.AdiDefinitions.OptionsList
                        variables_get = variables.get
                        options_lists_set = options_lists.__setitem__
                        _decode_name = _cstr

                        # optional: intern strings if many repeats (saves RAM, faster compares)
                        intern = sys.intern

                        # keep an integer key like your original code
                        k = len(options_lists)

                        for _ in range(n):
                            # header: 16s name + uint16 num_options
                            name_b = mv[ix:ix+16]
                            num_opts = int.from_bytes(mv[ix+16:ix+18], 'little')
                            ix += 18

                            name = intern(_decode_name(name_b.tobytes()))
                            var = variables_get(name)  # assume present; if not, skip or handle
                            ol = OptionsList(name=name)
                            if var is not None:
                                var.options_list = ol

                            # collect options
                            opts = ol.options
                            append = opts.append
                            for _ in range(num_opts):
                                ln = int.from_bytes(mv[ix:ix+2], 'little'); ix += 2
                                # decode directly from the slice; variable-length, no NUL terminator
                                s = intern(_decode_name(mv[ix:ix+ln].tobytes()))
                                ix += ln
                                append(s)

                            options_lists_set(k, ol)
                            k += 1

                        return ix
                    ix = parse_options_lists_block(mv, ix, variables, options_lists)

                    # Records
                    total_records = 0
                    total_vars = 0
                    def parse_records_block(mv: memoryview, ix: int,
                                            variables_by_id: dict,   # id -> AdiVariable
                                            records: dict):          # int -> AdiRecord

                        # Precompile once
                        _REC_HDR = struct.Struct("<16sHHHHBBBB")   # 28 bytes
                        _REC_VAR = struct.Struct("<HH5s27s")       # 36 bytes

                        # number of records
                        n = int.from_bytes(mv[ix:ix+4], 'little'); ix += 4
                        nonlocal total_records
                        total_records = n

                        # bind hot locals
                        Record     = adi.AdiDefinitions.AdiRecord
                        RecordVar  = adi.AdiDefinitions.AdiRecordVariable
                        rec_set    = records.__setitem__
                        v_getitem  = variables_by_id.__getitem__  # faster than get (assumes valid ids)
                        _decode    = _cstr
                        hdr_unpack = _REC_HDR.unpack_from
                        iter_vars  = struct.iter_unpack
                        VAR_fmt    = _REC_VAR.format
                        VAR_size   = _REC_VAR.size

                        PK_WELL = adi.AdiDefinitions.RecordPrimaryKeys.Well.value
                        PK_RUN  = adi.AdiDefinitions.RecordPrimaryKeys.BitRun.value
                        PK_DESC = adi.AdiDefinitions.RecordPrimaryKeys.Description.value

                        nonlocal total_vars
                        for i in range(n):
                            # header (28 bytes)
                            name_b, record_type_id, index_types, number_variables, category_id, pk_well, pk_run, _, pk_desc = hdr_unpack(mv, ix)
                            ix += _REC_HDR.size

                            if category_id > 2:  # keep your clamp
                                category_id = 0

                            # keep track of total variables for upcoming blocks
                            total_vars += number_variables

                            name = _decode(name_b)
                            pks = (PK_WELL if pk_well else 0) | (PK_RUN if pk_run else 0) | (PK_DESC if pk_desc else 0)

                            rec = Record(
                                name=name,
                                record_type_id=record_type_id,
                                index_types=index_types,
                                number_variables=number_variables,
                                category_id=category_id,
                                primary_keys=pks
                            )

                            # variables block for this record: use iter_unpack over a contiguous slice
                            if number_variables:
                                block_len = number_variables * VAR_size
                                block = mv[ix:ix+block_len]
                                ix += block_len

                                append_rv = rec.variables.append
                                for var_id, calculated, mnem_b, label_b in iter_vars(VAR_fmt, block):
                                    v = v_getitem(var_id)
                                    rv = RecordVar(
                                        variable=v,
                                        mnemonic=_decode(mnem_b),
                                        curve_label=_decode(label_b),
                                        calculated=calculated
                                    )
                                    append_rv(rv)
                                    rec_vars_wire_order.append(rv) 
                            rec_set(i, rec)

                        return ix
                    ix = parse_records_block(mv, ix, variables_by_id, records)

                    # Still records, apparentely empty data for all variables,
                    # confirming only the name of the record, and full of zeros
                    # Skipping this block:
                    ix += 20 * total_records + total_vars * 168

                    # Unit Types = Check of data
                    # Here it is the association with id_unit and id_class
                    # all the rest is zeroed
                    # try:
                    #     for _ in range(number_units):
                    #         n_20, z1, z2, z3, z4, z5, name, u1, id_class, id_unit = struct.unpack_from("<QQQIHB16sBHH", response.data, ix)
                    #         name = fromArrayToUTF8(name)
                    #         ut = unit_types[id_unit]
                    #         ut.unit_options = ut.measurement_class.unit_options
                    #         ix += 52
                    # except Exception as ex:
                    #     print(repr(ex))
                    #     raise ex
                    ix += number_units * 52  # skipping this block

                    # Block 1 - Records - Attributes and PSL types
                    def parse_record_attrs_psl(mv, start, length):
                        _REC_ATTR = struct.Struct("<II")  # psl_types, attributes
                        n_pairs = length // _REC_ATTR.size
                        block   = mv[start:start + n_pairs * _REC_ATTR.size]

                        RA_RO = adi.AdiEnums.RecordAttributes.ReadOnly.value
                        RA_HI = adi.AdiEnums.RecordAttributes.Hidden.value

                        # iterate aligned with your records insertion order
                        for rec, (psl, attrs) in zip(records.values(), struct.iter_unpack(_REC_ATTR.format, block)):
                            rec.psl_types  = psl
                            rec.attributes = ((RA_RO if (attrs & 0x100) else 0) |
                                            (RA_HI if (attrs & 0x01)  else 0))
                        # return None ⇒ caller will set ix = end

                    # Block 2 - Variables - mnemonic32
                    def parse_variables_mnemonics32(mv, start, length):
                        _MN32 = struct.Struct("33s")  # one mnemonic32 = 33 bytes
                        # how many entries are actually present in the payload?
                        n_payload = length // _MN32.size

                        # bind locals (fast)
                        _decode = _cstr
                        v_by_id = variables_by_id          # dict or list (both work with [] if dense)
                        order   = var_ids_in_order         # list of vids in wire order

                        # limit to what we have
                        n = min(n_payload, len(order))
                        if n == 0:
                            return

                        block = mv[start : start + n * _MN32.size]

                        # C-level iteration; each item is a tuple (bytes33,)
                        it = struct.iter_unpack(_MN32.format, block)

                        # fast loop: resolve vid in wire order, set field
                        for vid, (b_mn32,) in zip(order, it):
                            v = v_by_id[vid]
                            v.mnemonic32 = _decode(b_mn32)

                    # Block 3 - Records - mnemonic32
                    def parse_records_variables_mnemonics32(mv, start, length):
                        _MN32 = struct.Struct("33s")
                        # how many payload entries we actually got
                        n = min(length // _MN32.size, len(rec_vars_wire_order))
                        if n <= 0:
                            return

                        block   = mv[start : start + n * _MN32.size]
                        it      = struct.iter_unpack(_MN32.format, block)
                        _decode = _cstr

                        # C-level bytes iterator zipped with our object refs
                        for rv, (b_mn32,) in zip(rec_vars_wire_order, it):
                            # only set if not all-zero (first byte nonzero)
                            if b_mn32[0] != 0:
                                rv.mnemonic32 = _decode(b_mn32)

                    # Block 4 - Unit Options - PSL Types
                    def parse_unit_options_psl_types(mv, start, length):
                        unit_options_wire_order = [uo for mc in measurement_classes.values() for uo in mc.unit_options]
                        _U32 = struct.Struct("<I")  # 4 bytes per PSL value
                        n = min(length // _U32.size, len(unit_options_wire_order))
                        if n <= 0:
                            return
                        block = mv[start : start + n * _U32.size]
                        it = struct.iter_unpack(_U32.format, block)

                        # C-fast bytes -> zip with our objects
                        for uo, (psl,) in zip(unit_options_wire_order, it):
                            uo.psl_types = psl

                    # Block 5 - Options Lists - Read Only
                    def parse_options_lists_read_only(mv, start, length):
                        _U32 = struct.Struct("<I")  # 4 bytes per flag
                        # how many flags are actually present
                        n = min(length // _U32.size, len(options_lists))
                        if n <= 0:
                            return

                        block = mv[start : start + n * _U32.size]
                        it    = struct.iter_unpack(_U32.format, block)

                        # iterate options lists in the same wire order they were created
                        for ol, (ro,) in zip(options_lists.values(), it):
                            ol.read_only = (ro != 0)   # treat any nonzero as True

                    # Block 6 - Records Variables - RefVariables
                    def parse_records_variables_refvariables(mv, start, length):
                        _REC_REF = struct.Struct("<I26sddd")   # algorithm:uint32, ref_name:26s, coeff1..3:float64

                        # how many entries are present vs how many RVs we have
                        n = min(length // _REC_REF.size, len(rec_vars_wire_order))
                        if n <= 0:
                            return

                        block   = mv[start : start + n * _REC_REF.size]
                        it      = struct.iter_unpack(_REC_REF.format, block)
                        _decode = _cstr

                        # fast name lookup; if your 'variables' dict is name->AdiVariable:
                        get_var_by_name = variables.get
                        # If you keyed by canonical name instead, swap in: lambda s: all_variables.get(canon_key(s))

                        for rv, (algo, ref_b, c1, c2, c3) in zip(rec_vars_wire_order, it):
                            # set fields
                            rv.algorithm = algo
                            rv.coeff1 = c1; rv.coeff2 = c2; rv.coeff3 = c3

                            # resolve reference only if algo != 0 and name is non-empty
                            if algo != 0 and ref_b[0] != 0:
                                ref_name = _decode(ref_b)
                                ref_var  = get_var_by_name(ref_name)
                                if ref_var is not None:
                                    rv.ref_variable = ref_var

                    # Block 7 - Records - Locked attribute
                    def parse_records_locked(mv, start, length):
                        _U32 = struct.Struct("<I")  # 4 bytes per lock flag
                        n = min(length // _U32.size, len(records))
                        if n <= 0:
                            return
                        block   = mv[start : start + n * _U32.size]
                        it      = struct.iter_unpack(_U32.format, block)

                        RA_LOCK = adi.AdiEnums.RecordAttributes.Locked.value

                        for rec, (flag,) in zip(records.values(), it):
                            if flag & 1:                 # treat any LSB set as "locked"
                                rec.attributes |= RA_LOCK
                            # (optional) else: rec.attributes &= ~RA_LOCK  # only if you want to explicitly clear

                    # Block 8 - Variables - IDs
                    def parse_variables_ids(mv, start, length):
                        # _U32 = struct.Struct("<I")
                        # # how many ids present vs how many we have
                        # n = min(length // _U32.size, len(var_ids_in_order))
                        # if n <= 0:
                        #     return

                        # block = mv[start : start + n * _U32.size]

                        # # fast validation against known wire order
                        # it = struct.iter_unpack(_U32.format, block)
                        # mismatched = False
                        # for expected_vid, (wire_vid,) in zip(var_ids_in_order, it):
                        #     if wire_vid != expected_vid:
                        #         mismatched = True
                        #         break

                        # if mismatched:
                        #     # Rare server variant: rebuild wire order from payload
                        #     # (Only makes sense if later blocks depend on it. If this
                        #     #  block comes *after* all var-related blocks you care about,
                        #     #  you can just log and ignore.)
                        #     var_ids_in_order[:] = [vid for (vid,) in struct.iter_unpack(_U32.format, block)]
                        #     # If you also keep a dense list index by id:
                        #     # variables_by_id_list[:] = [variables_by_id[vid] for vid in var_ids_in_order]
                        return  # noop; outer dispatcher advances ix by `length`

                    # Block 9 - Records Variables - IDs
                    def parse_records_variables_ids(mv, start, length):
                        # Probably legacy system did not expect the amount of vars to fit more than
                        # in two bytes, so the previous record block points to variable_id with two
                        # bytes and here we fix it using a 4-byte ID number
                        _U32 = struct.Struct("<I")  # one uint32 id per record-variable
                        # how many ids we can actually read
                        n = min(length // _U32.size, len(rec_vars_wire_order))
                        if n <= 0:
                            return

                        block      = mv[start : start + n * _U32.size]
                        it         = struct.iter_unpack(_U32.format, block)
                        get_by_id  = variables_by_id.__getitem__   # list or dict both support []
                        mismatches = 0  # optional debug counter

                        for rv, (vid,) in zip(rec_vars_wire_order, it):
                            base = rv.variable
                            if base is None or base.id != vid:
                                try:
                                    rv.variable = get_by_id(vid)
                                    mismatches += 1
                                except (KeyError, IndexError):
                                    # Unknown ID; leave as-is (or set to None if you prefer)
                                    pass

                        # optional: log if you ever see remapping
                        # if mismatches:
                        #     print(f"Records var IDs: remapped {mismatches} of {n}")

                    # Now, parsing all the blocks with specific data
                    # Each block has a header with:
                    # [block_id, length_block, is_present] = struct.unpack_from("<III", response.data, ix)
                    # if is_present == 0, the block is not present
                    # length_block is the length of the block, including the header
                    def parse_blocks(mv, ix, handlers):
                        """mv: memoryview(response.data); ix: current offset; handlers: {block_id: fn(mv, start, length) -> None or new_ix}"""
                        mv_len = len(mv)
                        get_handler = handlers.get
                        _HDR = struct.Struct("<III")  # block_id, length, is_present  (12 bytes)

                        while ix + 4 <= mv_len:
                            # Peek ID
                            block_id = int.from_bytes(mv[ix:ix+4], 'little')

                            # Block 0: only the ID (no length/present)
                            if block_id == 0:
                                ix += 4
                                continue

                            # Need full header
                            if ix + 12 > mv_len:
                                break  # incomplete header at end

                            # Read header fast
                            _, length_blk, is_present = _HDR.unpack_from(mv, ix)
                            start = ix + 12
                            end   = ix + length_blk
                            if end > mv_len:
                                # corrupt/truncated block; stop cleanly
                                # (or log and break)
                                break

                            # Advance past header (payload is [start:end])
                            ix = start

                            if not is_present or length_blk == 0:
                                ix = end
                                continue

                            # Dispatch (handlers must not over-read; they can return a new ix if they consume partially)
                            fn = get_handler(block_id)
                            if fn is not None:
                                new_ix = fn(mv, start, length_blk)
                                ix = end if new_ix is None else new_ix
                            else:
                                # Unknown block: skip payload
                                print(f"Skipping unknown block ID {block_id} of length {length_blk}")
                                ix = end

                        return ix

                    handlers = {
                        1: parse_record_attrs_psl,
                        2: parse_variables_mnemonics32,
                        3: parse_records_variables_mnemonics32,
                        4: parse_unit_options_psl_types,
                        5: parse_options_lists_read_only,
                        6: parse_records_variables_refvariables,
                        7: parse_records_locked,
                        8: parse_variables_ids,
                        9: parse_records_variables_ids
                    }
                    parse_blocks(mv, ix, handlers)

                    result["DatabaseDefinitions"] = adi.AdiDefinitions.AdiDatabaseDefinitions(measurement_classes, unit_types, variables, None, records)
                except Exception as ex:
                    result["Success"] = False

            return result

    # 0x9000 - ADI_DATASET_PREPARE
    class DataSetPrepare(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9000

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            fields_present = 0
            well = None
            run_number = None
            record = None
            description = None
            final_open_mode = adi.AdiEnums.RecordOpenModes(0)
            open_full_mode = 0
            open_simple_mode = 0
            if header.length == 70 and adi.AdiEnums.OutputFormat.BINARY_SIMPLE in adi.AdiEnums.OutputFormat(header.format):
                fields_present, run_number, record, well, description, open_simple_mode, index_desc = struct.unpack_from("<HH16s16s32sBB", data, 16)
                if index_desc & 1 != 0: final_open_mode |= adi.AdiEnums.RecordOpenModes.DescriptorMode
                if index_desc & 2 != 0: final_open_mode |= adi.AdiEnums.RecordOpenModes.DepthIndex
                if index_desc & 4 != 0: final_open_mode |= adi.AdiEnums.RecordOpenModes.TimeIndex
                if open_simple_mode & 1 != 0: final_open_mode = adi.AdiEnums.RecordOpenModes.ReadWrite
                elif open_simple_mode & 2 != 0: final_open_mode = adi.AdiEnums.RecordOpenModes.Write
                else: final_open_mode = adi.AdiEnums.RecordOpenModes.Read
                if open_simple_mode & 0x10: final_open_mode |= adi.AdiEnums.RecordOpenModes.NoTruncate | adi.AdiEnums.RecordOpenModes.Create
                elif open_simple_mode & 0x20: final_open_mode |= adi.AdiEnums.RecordOpenModes.Create
            elif header.length == 72 and adi.AdiEnums.OutputFormat.BINARY_FULL in adi.AdiEnums.OutputFormat(header.format):
                fields_present, run_number, record, well, description, open_full_mode, open_simple_mode, index_desc = struct.unpack_from("<HH16s16s32sHBB", data, 16)
                if open_simple_mode & 1 != 0: final_open_mode = adi.AdiEnums.RecordOpenModes.ReadWrite
                elif open_full_mode & 0x811 != 0: final_open_mode = adi.AdiEnums.RecordOpenModes.Write
                else: final_open_mode = adi.AdiEnums.RecordOpenModes.Read
                if open_simple_mode & 0x10: final_open_mode |= adi.AdiEnums.RecordOpenModes.NoTruncate | adi.AdiEnums.RecordOpenModes.Create
                elif open_simple_mode & 0x20: final_open_mode |= adi.AdiEnums.RecordOpenModes.Create
            fields_present = adi.AdiEnums.QueryFilterModes(fields_present)
            well = None if fields_present & adi.AdiEnums.QueryFilterModes.WELL.value == 0 else fromArrayToUTF8(well)
            run_number = 0 if fields_present & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value) == 0 else run_number
            record = None if fields_present & adi.AdiEnums.QueryFilterModes.RECORD.value == 0 else fromArrayToUTF8(record)
            description = None if fields_present & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value == 0 else fromArrayToUTF8(description)

            return AdiCommands.DataSetPrepare(client=client, fields_present=fields_present, well=well, run_number=run_number, record=record, description=description, open_mode_value=final_open_mode, format=header.format)

        def __init__(self, client=None, fields_present = 0x1d, well=None, run_number=None, record=None, description=None, open_mode_value=adi.AdiEnums.RecordOpenModes.Read, record_variables_on_create=None, format=None):
            if format is None: format = adi.AdiEnums.OutputFormat.BINARY_FULL if adi.AdiEnums.RecordOpenModes.Create not in open_mode_value else adi.AdiEnums.OutputFormat.BINARY_SIMPLE

            super().__init__(name="ADI_DATASET_PREPARE", code=self.GetCode(), client=client, output_format=format)
            self.fields_present = fields_present
            self.well = well
            # if self.well is None and self.client is not None: self.well = self.client.well
            self.run_number = run_number
            # if self.run_number is None and self.client is not None: self.run_number = self.client.run_number
            self.record = record
            self.description = description
            
            self.open_mode_value = open_mode_value
            self.record_variables_on_create = record_variables_on_create
            self.is_valid = self.well is not None and self.run_number is not None and self.record is not None and self.description is not None

        def GetDetails(self):
            if not self.is_valid: return "Invalid query"
            return f"{self.well} \\ {self.run_number} \\ {self.record} \\ {self.description}"

        async def GetLocalResult(self):
            adi_dataset:adi.AdiDefinitions.AdiDataSetReader = await self.client_local.server.DatasetPrepare(
                well=self.well,
                run_number=self.run_number,
                record=self.record,
                description=self.description,
                truncate_data=adi.AdiEnums.RecordOpenModes.NoTruncate not in self.open_mode_value,
                create_if_not_exists=adi.AdiEnums.RecordOpenModes.Create in self.open_mode_value
            )
            result = { "Success": adi_dataset is not None }

            if adi_dataset is not None:
                adi_dataset.open_mode_value = self.open_mode_value
                self.client_local.AddDataSetReader(adi_dataset)
                result["AdiDataSet"] = adi_dataset
                
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            elif not "AdiDataSet" in result: return adi.AdiDefinitions.AdiResponse(param=0x08)
            else: return adi.AdiDefinitions.AdiResponse(value=result["AdiDataSet"].id)

        def BuildCommandBinaryData(self):
            open_full_mode = 0
            open_simple_mode = 0
            if adi.AdiEnums.OutputFormat.BINARY_SIMPLE in self.output_format:
                if adi.AdiEnums.RecordOpenModes.Read in self.open_mode_value:
                    open_simple_mode = 0
                if adi.AdiEnums.RecordOpenModes.Write in self.open_mode_value:
                    open_simple_mode = 2
                if adi.AdiEnums.RecordOpenModes.ReadWrite in self.open_mode_value:
                    open_simple_mode = 1
                if adi.AdiEnums.RecordOpenModes.Create in self.open_mode_value and adi.AdiEnums.RecordOpenModes.NoTruncate in self.open_mode_value:
                    open_simple_mode += 0x10
                elif adi.AdiEnums.RecordOpenModes.Create in self.open_mode_value:
                    open_simple_mode += 0x20
            else:
                open_simple_mode = 0x02
                if adi.AdiEnums.RecordOpenModes.Read in self.open_mode_value:
                    open_full_mode = 0x00
                if adi.AdiEnums.RecordOpenModes.Write in self.open_mode_value:
                    open_full_mode = 0x811
                if adi.AdiEnums.RecordOpenModes.ReadWrite in self.open_mode_value:
                    open_full_mode = 1
                if adi.AdiEnums.RecordOpenModes.Create in self.open_mode_value and adi.AdiEnums.RecordOpenModes.NoTruncate in self.open_mode_value:
                    open_simple_mode += 0x10
                elif adi.AdiEnums.RecordOpenModes.Create in self.open_mode_value:
                    open_simple_mode += 0x20
            index_desc = 0
            if adi.AdiEnums.RecordOpenModes.DescriptorMode in self.open_mode_value: index_desc += (adi.AdiEnums.RecordOpenModes.DescriptorMode.value >> 13)
            if adi.AdiEnums.RecordOpenModes.DepthIndex in self.open_mode_value: index_desc += (adi.AdiEnums.RecordOpenModes.DepthIndex.value >> 3)
            if adi.AdiEnums.RecordOpenModes.TimeIndex in self.open_mode_value: index_desc += (adi.AdiEnums.RecordOpenModes.TimeIndex.value >> 3)
            
            if adi.AdiEnums.OutputFormat.BINARY_SIMPLE in self.output_format:
                bytes_data = struct.pack(f"<HH16s16s32sBB", self.fields_present, self.run_number, toUTF8Array(self.record),
                                     toUTF8Array(self.well), toUTF8Array(self.description), open_simple_mode, index_desc)
            else:
                bytes_data = struct.pack(f"<HH16s16s32sHBB", self.fields_present, self.run_number, toUTF8Array(self.record),
                                        toUTF8Array(self.well), toUTF8Array(self.description), open_full_mode, open_simple_mode, index_desc)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=self.output_format, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            if success:
                adi_dataset = adi.AdiDefinitions.AdiDataSetReader(self.client, id=response.value, well=self.well, run_number=self.run_number, record=self.record, description=self.description, open_mode_value=self.open_mode_value)
                self.client.AddOpenedDataset(adi_dataset)
                result["AdiDataSet"] = adi_dataset
            return result

    # 0x9001 - ADI_DATASET_CLOSE
    class DataSetClose(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9001

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.DataSetClose(client=client, adi_dataset=client.GetAdiDataSetReader(header.param))

        def __init__(self, client=None, adi_dataset=None):
            super().__init__(name="ADI_DATASET_CLOSE", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.is_valid = self.adi_dataset is not None

        async def GetLocalResult(self):
            success = self.adi_dataset is not None
            if success:
                # Remember that "variables" is an array of dictionaries
                # containing the keys "Variable" and "UnitOption"
                if self.client is not None:
                    self.client.CloseDataSet(self.adi_dataset.id)
                
            return { "Success": success }

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            response = adi.AdiDefinitions.AdiResponse(param=0x00 if success else 0x01)
            return response

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            if success: self.client.RemoveOpenedDataset(self.adi_dataset)
            return result

    # 0x9002 - ADI_DATASET_OPEN
    class DataSetOpen(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9002

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            record = None
            variables = []
            open_mode_value = adi.AdiEnums.RecordOpenModes(0)
            try:
                ix = 16
                open_mode, index_desc, output_format, number_variables = struct.unpack_from("<BBHI", data, ix)
                if output_format == 0x02:
                    if index_desc == 0x08 and open_mode == 0x11: open_mode_value |= adi.AdiEnums.RecordOpenModes.Write
                    else: open_mode_value |= adi.AdiEnums.RecordOpenModes.Read
                else:
                    if index_desc & 1 != 0: open_mode_value |= adi.AdiEnums.RecordOpenModes.DescriptorMode
                    if index_desc & 2 != 0: open_mode_value |= adi.AdiEnums.RecordOpenModes.DepthIndex
                    if index_desc & 4 != 0: open_mode_value |= adi.AdiEnums.RecordOpenModes.TimeIndex
                    if open_mode & 1 != 0: open_mode_value = adi.AdiEnums.RecordOpenModes.ReadWrite
                    elif open_mode & 2 != 0: open_mode_value = adi.AdiEnums.RecordOpenModes.Write
                    else: open_mode_value = adi.AdiEnums.RecordOpenModes.Read
                    if open_mode & 0x10: open_mode_value |= adi.AdiEnums.RecordOpenModes.NoTruncate | adi.AdiEnums.RecordOpenModes.Create
                    elif open_mode & 0x20: open_mode_value |= adi.AdiEnums.RecordOpenModes.Create

                if header.length != 8 + number_variables * 24 + 16: raise Exception("Invalid data")
                ix += 8
                for _ in range(number_variables):
                    size, offset, storage, unit_option, name = struct.unpack_from("<HHHH16s", data, ix)
                    name = fromArrayToUTF8(name)
                    v = adi.AdiDefinitions.AdiVariable(size=size, offset=offset, name=name, format=adi.AdiEnums.StorageType(storage), unit_type=adi.AdiDefinitions.UnitType(unit_option=adi.AdiDefinitions.UnitOption(id=unit_option)))
                    variables.append({"Variable": v, "UnitOption": v.unit_type.unit_option})
                    ix += 24
                [record] = struct.unpack_from("<16s", data, ix)
                record = fromArrayToUTF8(record)
            except Exception as ex:
                record = None
            
            return AdiCommands.DataSetOpen(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), record=record, variables=variables, open_mode_value=open_mode_value, format=adi.AdiEnums.OutputFormat.BINARY_FULL if output_format == 0x02 else adi.AdiEnums.OutputFormat.BINARY_SIMPLE)

        def __init__(self, client=None, adi_dataset=None, record=None, variables=[], open_mode_value=adi.AdiEnums.RecordOpenModes.Read, desc_mode=False, index_type=adi.AdiEnums.IndexType.Sequential, create_dataset=False, format=None):
            if format is None: format = adi.AdiEnums.OutputFormat.BINARY_FULL if open_mode_value & adi.AdiEnums.RecordOpenModes.Create == 0 else adi.AdiEnums.OutputFormat.BINARY_SIMPLE
            
            super().__init__(name="ADI_DATASET_OPEN", code=self.GetCode(), client=client, output_format=format)
            self.adi_dataset = adi_dataset
            self.record = record
            self.variables = variables
            self.open_mode_value = open_mode_value
            self.desc_mode = desc_mode
            self.index_type = index_type
            self.create_dataset = create_dataset
            self.is_valid = self.adi_dataset is not None and self.record is not None
            for v in self.variables:
                if v["Variable"] is None or v["UnitOption"] is None: self.is_valid = False
            
            # The "Create Dataset" variation was only implemented in "SIMPLE_BINARY" format
            if self.create_dataset: self.output_format = adi.AdiEnums.OutputFormat.BINARY_SIMPLE

        async def GetLocalResult(self):
            success = self.is_valid and not self.adi_dataset.is_open
            result = {}
            if success:
                await self.client_local.server.DatasetOpen(self.client, self.adi_dataset, self.variables, self.open_mode_value)
            result["Success"] = success
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            response = adi.AdiDefinitions.AdiResponse(param=0x00 if success else 0x01)
            return response

        def BuildCommandBinaryData(self):
            open_mode = 0
            if adi.AdiEnums.OutputFormat.BINARY_SIMPLE in self.output_format:
                if adi.AdiEnums.RecordOpenModes.Read in self.open_mode_value: open_mode = 0
                if adi.AdiEnums.RecordOpenModes.Write in self.open_mode_value: open_mode = 2
                if adi.AdiEnums.RecordOpenModes.ReadWrite in self.open_mode_value: open_mode = 1
                if adi.AdiEnums.RecordOpenModes.Create in self.open_mode_value and adi.AdiEnums.RecordOpenModes.NoTruncate in self.open_mode_value: open_mode += 0x10
                elif adi.AdiEnums.RecordOpenModes.Create in self.open_mode_value: open_mode += 0x20
                index_desc = 0
                if adi.AdiEnums.RecordOpenModes.DescriptorMode in self.open_mode_value: index_desc += (adi.AdiEnums.RecordOpenModes.DescriptorMode.value >> 13)
                if adi.AdiEnums.RecordOpenModes.DepthIndex in self.open_mode_value: index_desc += (adi.AdiEnums.RecordOpenModes.DepthIndex.value >> 3)
                if adi.AdiEnums.RecordOpenModes.TimeIndex in self.open_mode_value: index_desc += (adi.AdiEnums.RecordOpenModes.TimeIndex.value >> 3)

                bytes_data = struct.pack("<BBBBI", open_mode, index_desc, open_mode, index_desc, len(self.variables))
            else:
                if adi.AdiEnums.RecordOpenModes.ReadWrite in self.open_mode_value: open_mode = 0x01
                elif adi.AdiEnums.RecordOpenModes.Read in self.open_mode_value: open_mode = 0x00
                else: open_mode = 0x0811
                bytes_data = struct.pack("<HHI", open_mode, 0x02, len(self.variables))
            for variable in self.variables:
                v:adi.AdiDefinitions.AdiVariable = variable["Variable"]
                unit_option = variable["UnitOption"]
                unit_option_id = 0 if unit_option is None or unit_option.id is None else unit_option.id
                size = v.size if v.number_of_elements == 1 else v.number_of_elements
                bytes_data += struct.pack("<HHHH16s", size, v.offset, v.GetStorageType().value, unit_option_id, toUTF8Array(v.name))
            bytes_data += struct.pack("<16s", toUTF8Array(self.record))
            
            # The property "output_format" is set in the constructor, but for both cases we send BINARY_SIMPLE
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(bytes_data), format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            if success: self.adi_dataset.variables = self.variables
            return result

    # 0x9004 - ADI_DATASET_OPEN_COMPLEX
    class DataSetPrepareComplex(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9004

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            keys = None
            filter_activities_per_key = None
            variables = None
            coercion_types = None
            output_resolution = None
            iv = None
            every_data_point = False
            vars_key_indexes = []
            try:
                ix = 16
                number_keys = header.param
                [number_keys] = struct.unpack_from("<I", data, ix)
                ix += 4
                keys = []
                for i in range(number_keys):
                    # if ix + 68 > len(data): break
                    [fields_present, run_number, record, well, description] = struct.unpack_from("<HH16s16s32s", data, ix)
                    ix += 68
                    key = adi.AdiDefinitions.AdiDataSet(
                        well=None if fields_present & adi.AdiEnums.QueryFilterModes.WELL.value == 0 else fromArrayToUTF8(well),
                        run_number=None if fields_present & adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value == 0 else run_number,
                        record=None if fields_present & adi.AdiEnums.QueryFilterModes.RECORD.value == 0 else fromArrayToUTF8(record),
                        description=None if fields_present & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value == 0 else fromArrayToUTF8(description))
                    [flag_descriptor] = struct.unpack_from("<I", data, 20 + 68 * number_keys + i * 4)
                    if flag_descriptor != 0:
                        desc_record = fromArrayToUTF8(struct.unpack_from("<16s", data, 20 + 68 * number_keys + 4 * number_keys + i * 16)[0])
                        key.descriptor_record = desc_record
                    keys.append(key)
                ix += number_keys * (4 + 16)
                filter_activities_per_key = []
                for i in range(number_keys):
                    # if ix + 4 > len(data): break
                    [activity] = struct.unpack_from("<I", data, ix)
                    filter_activities_per_key.append(None if activity == 0 else activity)
                    ix += 4
                [even_intervals_flag, zero_1, output_resolution, even_intervals_iv, unit_option_iv, number_coercions] = struct.unpack_from("IId16sII", data, ix)
                ix += 40
                even_intervals_iv = fromArrayToUTF8(even_intervals_iv)
                v = adi.AdiDefinitions.AdiVariable(name=even_intervals_iv, unit_type=adi.AdiDefinitions.UnitType(unit_option=adi.AdiDefinitions.UnitOption(id=unit_option_iv)))
                iv = {"Variable": v, "UnitOption": v.unit_type.unit_option}
                if even_intervals_flag != 0x02: output_resolution = None
                every_data_point = even_intervals_flag == 0x00
                coercion_types = []
                for i in range(number_coercions):
                    [coercion_type, zero_1, coercion_param, gap_distance, zero_2, zero_3] = struct.unpack_from("<IIdddd", data, ix)
                    ix += 40
                    coercion_types.append(adi.AdiDefinitions.CoercionType(coercion_type=adi.AdiEnums.CoercionTypes(coercion_type), coercion_param=coercion_param, gap_distance=gap_distance))
                [number_unknown] = struct.unpack_from("<I", data, ix)
                ix += 4
                vars_key_indexes = []
                for i in range(number_unknown):
                    [key_index] = struct.unpack_from("<I", data, ix)
                    ix += 4
                    vars_key_indexes.append(key_index)
                ix += 8 # 2 unknown blocks
                variables = []
                [number_vars] = struct.unpack_from("<I", data, ix)
                ix += 4
                for i in range(number_vars):
                    size, offset, storage, unit_option, name = struct.unpack_from("<HHHH16s", data, ix)
                    name = fromArrayToUTF8(name)
                    ix += 24
                    v = adi.AdiDefinitions.AdiVariable(size=size, offset=offset, name=name, format=adi.AdiEnums.StorageType(storage), unit_type=adi.AdiDefinitions.UnitType(unit_option=adi.AdiDefinitions.UnitOption(id=unit_option)))
                    variables.append({"Variable": v, "UnitOption": v.unit_type.unit_option})
            except Exception as ex:
                keys = None
                variables = None

            return AdiCommands.DataSetPrepareComplex(client=client, keys=keys,
                    variables=variables, coercion_types=coercion_types, iv=iv,
                    every_data_point=every_data_point, output_resolution=output_resolution,
                    vars_key_indexes=vars_key_indexes)

        def __init__(self, client=None, keys=None, filter_activities_per_key=None, variables=None, coercion_types=None, iv=None, every_data_point=False, output_resolution=None, vars_key_indexes=None):
            super().__init__(name="ADI_DATASET_OPEN_COMPLEX", code=self.GetCode(), client=client)
            self.keys:list[adi.AdiDefinitions.AdiDataSet] = keys
            self.filter_activities_per_key:list[int] = filter_activities_per_key
            self.variables:list = variables
            self.coercion_types:list[adi.AdiDefinitions.CoercionType] = coercion_types
            self.iv:adi.AdiDefinitions.AdiVariable = iv
            self.every_data_point:bool = every_data_point
            self.output_resolution:float = output_resolution
            self.vars_key_indexes = vars_key_indexes
            self.is_valid = self.keys is not None and self.variables is not None

        async def GetLocalResult(self):
            success = await self.client_local.server.DataSetPrepareComplex(self.keys, self.filter_activities_per_key, self.variables, self.coercion_types, self.iv, self.output_resolution)
            return { "Success": success }

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            response = adi.AdiDefinitions.AdiResponse(param=0x00 if success else 0x01)
            return response

        def BuildCommandBinaryData(self):
            data = struct.pack("<I", 0 if self.keys is None else len(self.keys))
            if self.keys is not None:
                for key in self.keys:
                    fields_present = 0
                    if key.well is not None: fields_present += adi.AdiEnums.QueryFilterModes.WELL.value
                    # if key.run_number is not None and key.descriptor_record is None: fields_present += adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value
                    # if key.run_number == 0 and str(key.record).lower().startswith("desc r"): fields_present += 0
                    # elif key.run_number is not None and key.descriptor_record is None: fields_present += adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value
                    if key.run_number is not None: fields_present += adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value
                    run_number = 0 if key.run_number is None else key.run_number
                    if key.record is not None: fields_present += adi.AdiEnums.QueryFilterModes.RECORD.value
                    if key.description is not None: fields_present += adi.AdiEnums.QueryFilterModes.DESCRIPTION.value
                    data += struct.pack("<HH16s16s32s", fields_present, run_number, toUTF8Array(key.record), toUTF8Array(key.well), toUTF8Array(key.description))
                for i in range(len(self.keys)):
                    # 0x020100 and 0x100 also works, but VERY SLOW for descriptors
                    # data += struct.pack("<I", 0x100 if str(self.keys[i].run_alias).lower() == "well based" and str(self.keys[i].record).lower().startswith("desc r") else 0)
                    data += struct.pack("<I", 0x00 if self.keys[i].descriptor_record is None else 0x220100)
                for i in range(len(self.keys)):
                    # data += struct.pack("<IIII", 0x00, 0x10, 0xffffffff, 0x05)
                    # data += struct.pack("<IIII", 0x5bb69e00, 0x93e998, 0x73699058, 0x7369905f)
                    data += struct.pack("<16s", toUTF8Array(None if self.keys[i].descriptor_record is None else self.keys[i].descriptor_record))
                for i in range(len(self.keys)):
                    data += struct.pack("<I", 0 if self.filter_activities_per_key is None or len(self.filter_activities_per_key) <= i or self.filter_activities_per_key[i] is None else self.filter_activities_per_key[i])
            which_single_dataset_index = 1
            iv_unit_option_id = 0 if self.iv is None or self.iv["UnitOption"] is None else self.iv["UnitOption"].id
            iv_unit_option_id = 0 # found this field to be zero in the server response, so setting it to zero
            data += struct.pack("IId16sI", 0x00 if self.every_data_point else 0x02, which_single_dataset_index,
                0 if self.output_resolution is None else self.output_resolution,
                toUTF8Array(None if self.iv is None else self.iv["Variable"].name),
                iv_unit_option_id)
            number_coercions = 0 if self.coercion_types is None else len(self.coercion_types)
            data += struct.pack("<I", number_coercions)
            if number_coercions > 0:
                for coercion_type in self.coercion_types:
                    data += struct.pack("<IIdddd", coercion_type.coercion_type.value, 0, 0 if coercion_type.coercion_param is None else coercion_type.coercion_param, 0 if coercion_type.gap_distance is None else coercion_type.gap_distance, 0, 0)
            data += struct.pack("<I", 0 if self.vars_key_indexes is None else len(self.vars_key_indexes))
            if self.vars_key_indexes is not None:
                for i in range(len(self.vars_key_indexes)):
                    key_index = self.vars_key_indexes[i]
                    if len(self.variables) > i and self.variables[i]["Variable"].name == (None if self.iv is None else self.iv["Variable"].name):
                        key_index = 0xffffffff
                    data += struct.pack("<I", key_index)
            data += struct.pack("<I", 0)
            data += struct.pack("<I", 0)
            data += struct.pack("<I", 0 if self.variables is None else len(self.variables))
            if self.variables is not None:
                for variable in self.variables:
                    v:adi.AdiDefinitions.AdiVariable = variable["Variable"]
                    unit_option = variable["UnitOption"]
                    unit_option_id = 0 if unit_option is None or unit_option.id is None else unit_option.id
                    size = v.size if v.number_of_elements == 1 else v.number_of_elements
                    data += struct.pack("<HHHH16s", size, v.offset, v.GetStorageType().value, unit_option_id, toUTF8Array(v.name))
                    # data += struct.pack("<HHHH16s", v.size, v.offset, v.GetStorageType().value, v.unit_type.unit_option.id, toUTF8Array(v.name))
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=0 if self.keys is None else len(self.keys), format=adi.AdiEnums.OutputFormat.BINARY_FULL, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

        def TranslateResponseFromBytes(self, response):
            success = response.param != 0x01 and response.length == 4 * len(self.keys)
            # Apparently repsonse.param == 0x07 means "Dataset not Found",
            # which will create problems closing the dataset later, so we treat it as success=False
            if response.param == 0x07: success = False
            result = {"Success": success}
            if success:
                result_found = []
                # not_exists = response.param == 0x07 and response.length == 4 and struct.unpack_from("<I", response.data)[0] == 9
                for i in range(len(self.keys)): result_found.append(struct.unpack_from("<I", response.data, i * 4)[0])
                adi_dataset = adi.AdiDefinitions.AdiDataSetReaderComplex(self.client, id=response.value, keys=self.keys,
                    variables=self.variables, coercion_types=self.coercion_types, iv=self.iv, output_resolution=self.output_resolution,
                    keys_opened=result_found)
                self.client.AddOpenedDataset(adi_dataset)
                result["AdiDataSet"] = adi_dataset
            return result

    # 0x9007 - ADI_DATASET_WRITE_BAG_DATA
    class DataSetWriteBagData(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9007

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            variables = []
            values = []
            try:
                ix = 16
                _, number_variables = struct.unpack_from("<II", data, ix)
                ix += 8
                for _ in range(number_variables):
                    size, offset, storage, unit_option, name = struct.unpack_from("<HHHH16s", data, ix)
                    name = fromArrayToUTF8(name)
                    v = adi.AdiDefinitions.AdiVariable(size=size, offset=offset, name=name, format=adi.AdiEnums.StorageType(storage), unit_type=adi.AdiDefinitions.UnitType(unit_option=adi.AdiDefinitions.UnitOption(id=unit_option)))
                    variables.append({"Variable": v, "UnitOption": v.unit_type.unit_option})
                    ix += 24
                [data_length] = struct.unpack_from("<I", data, ix)
                ix += 4
                values = AdiCommands.ExtractDataFromBuffer(data, ix, data_length, ix + data_length + 4, variables, len(variables))
            except:
                variables = None
            
            return AdiCommands.DataSetWriteBagData(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), variables=variables, values=values)

        def __init__(self, client=None, adi_dataset=None, variables=[], values=[]):
            super().__init__(name="ADI_DATASET_WRITE_BAG_DATA", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.variables = variables
            self.values = values
            self.is_valid = self.adi_dataset is not None and self.variables is not None and len(variables) > 0

        async def GetLocalResult(self):
            success = await self.client_local.server.DataSetWriteBagData(self.adi_dataset, self.variables, self.values)
            return { "Success": success }

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            response = adi.AdiDefinitions.AdiResponse(param=0x00 if success else 0x01)
            return response

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack("<II", 0x00, len(self.variables))
            number_bytes_bit_test = math.ceil(float(len(self.variables)) / 8.0)
            fields_bit_test = [0] * number_bytes_bit_test
            # First we input all variables, then the size of data and the data
            vars_bytes = b''
            data_bytes = b''
            for i in range(len(self.variables)):
                v:adi.AdiDefinitions.AdiVariable = self.variables[i]["Variable"]
                value = v.GetValueBytes(self.values[i])
                unit_option:adi.AdiDefinitions.UnitOption = self.variables[i]["UnitOption"]
                unit_option_id = 0 if unit_option is None or unit_option.id is None else unit_option.id
                vars_bytes += struct.pack("<HHHH16s", v.size, v.offset, v.GetStorageType().value, unit_option_id, toUTF8Array(v.name))

                length_value = v.size if value is None else len(value)
                if value is None:
                    data_bytes += b'\0' * length_value
                else:
                    data_bytes += value
                    ix_byte_field = int(float(i) / 8.0)
                    value_byte_field = fields_bit_test[ix_byte_field]
                    value_byte_field |= 1 << (i % 8)
                    fields_bit_test[ix_byte_field] = value_byte_field
            bytes_data += vars_bytes + struct.pack("<I", len(data_bytes)) + data_bytes + struct.pack("<I", len(self.variables)) + bytes(fields_bit_test)
            
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            return result

    # 0x9008 - ADI_DATASET_READ_BAG_DATA
    class DataSetReadBagData(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9008

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            variables = []
            if header.length >= 4:
                [num_vars] = struct.unpack_from("<I", data, 16)
                if header.length == 4 + num_vars * 24:
                    ix = 20
                    for _ in range(num_vars):
                        size, offset, storage, unit_option, name = struct.unpack_from("<HHHH16s", data, ix)
                        name = fromArrayToUTF8(name)
                        v = adi.AdiDefinitions.AdiVariable(size=size, offset=offset, name=name, format=adi.AdiEnums.StorageType(storage), unit_type=adi.AdiDefinitions.UnitType(unit_option=adi.AdiDefinitions.UnitOption(id=unit_option)))
                        variables.append({"Variable": v, "UnitOption": v.unit_type.unit_option})
                        ix += 24
            return AdiCommands.DataSetReadBagData(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), variables=variables)

        def __init__(self, client=None, adi_dataset=None, variables=None):
            super().__init__(name="ADI_DATASET_READ_BAG_DATA", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.variables = variables
            self.is_valid = self.adi_dataset is not None and len(self.variables) > 0

        async def GetLocalResult(self):
            success = self.is_valid
            result = { "Success": success }
            if success:
                data = await self.client_local.server.DataSetReadBagData(self.adi_dataset, self.variables)
                if data is None: result["Success"] = False
                else: result["Data"] = data
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            response = adi.AdiDefinitions.AdiResponse(param=0x00 if result["Success"] else 0x01)
            
            if result["Success"]:
                try:
                    data = AdiCommands.BuildDataForBuffer(self.variables, result["Data"])
                    bytes_record = data["Data"] + data["Blob"]
                    bytes_data = struct.pack("<I", len(bytes_record))
                    bytes_data += bytes_record
                    bytes_data += struct.pack("<I", data["NumberValues"])
                    bytes_data += data["BitTest"]
                    response.length = len(bytes_data)
                    response.data = bytes_data
                except Exception as ex:
                    response.param = 0x01
                    
            return response

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack("<I", len(self.variables))
            for variable in self.variables:
                v = variable["Variable"]
                unit_option = variable["UnitOption"]
                unit_option_id = 0 if unit_option is None or unit_option.id is None else unit_option.id
                bytes_data += struct.pack("<HHHH16s", v.size, v.offset, v.GetStorageType().value, unit_option_id, toUTF8Array(v.name))
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(bytes_data), format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = self.adi_dataset is not None and response.param == 0x00 and response.length >= 4
            result = {"Success": success}
            if success:
                ix = 0
                [length_record] = struct.unpack_from("<I", response.data, ix)
                ix += 4
                if ix + length_record + 4 > response.length: return {"Success": False}
                [number_values] = struct.unpack_from("<I", response.data, ix + length_record)
                number_bytes_bit_test = math.ceil(number_values / 8.0)
                if ix + length_record + 4 + number_bytes_bit_test > response.length: return {"Success": False}
                ix_bit_fields_test = ix + length_record + 4
                if ix + length_record > response.length: return {"Success": False}
                data_line = AdiCommands.ExtractDataFromBuffer(response.data, ix, length_record, ix_bit_fields_test, self.adi_dataset.variables, number_values)
                result["Data"] = data_line
                
            return result

    # 0x900a - ADI_DATASET_WRITE (single)
    class DataSetWrite(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x900a

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            adi_dataset:adi.AdiDefinitions.AdiDataSetReader = client.GetAdiDataSetReader(header.param)
            write_mode = adi.AdiEnums.DataSetWriteModes(0)
            fields_to_write = []
            
            if adi_dataset is not None:
                # Structure is (one line only!):
                # aa aa aa aa bb bb bb bb   aa = mode, bb = num_bytes
                # d1 d1 d1 d1 .. ..         dx = x bytes as specified by bb
                # cc cc cc cc dd dd ..      cc = num values, dd = bit fields
                
                try:
                    ix = 16
                    write_mode_value, number_bytes = struct.unpack_from("<II", data, ix)
                    ix += 8
                    fields_to_write = AdiCommands.ExtractDataFromBuffer(data, ix, number_bytes, ix + number_bytes + 4, adi_dataset.variables, len(adi_dataset.variables))
                    
                    if write_mode_value & 0x01 != 0:
                        write_mode |= adi.AdiEnums.DataSetWriteModes.Exclusive
                    if write_mode_value & 0x02 != 0:
                        write_mode |= adi.AdiEnums.DataSetWriteModes.Insert
                    if write_mode_value & 0x03 != 0:
                        write_mode |= adi.AdiEnums.DataSetWriteModes.Update
                    if write_mode_value & 0x04 != 0:
                        write_mode |= adi.AdiEnums.DataSetWriteModes.UpdateExact
                    if write_mode_value & 0x20 != 0:
                        write_mode |= adi.AdiEnums.DataSetWriteModes.StoreData
                    if write_mode_value & 0x40 != 0:
                        write_mode |= adi.AdiEnums.DataSetWriteModes.UserUtcTime
                    if write_mode_value & 0x80 != 0:
                        write_mode |= adi.AdiEnums.DataSetWriteModes.Compressed

                except:
                    adi_dataset = None

            return AdiCommands.DataSetWrite(client=client, adi_dataset=adi_dataset, write_mode_value=write_mode, fields_to_write=fields_to_write)

        def __init__(self, client=None, adi_dataset:adi.AdiDefinitions.AdiDataSetReader=None, write_mode_value=None, fields_to_write=[]):
            super().__init__(name="ADI_DATASET_WRITE", code=self.GetCode(), client=client, response_expected=False)
            self.adi_dataset = adi_dataset
            self.write_mode_value = adi.AdiEnums.DataSetWriteModes(write_mode_value) if not type(write_mode_value).__name__ == 'DataSetWriteModes' else write_mode_value
            if write_mode_value is None: write_mode_value = adi.AdiEnums.DataSetWriteModes.Insert
            self.fields_to_write = fields_to_write
            self.is_valid = self.adi_dataset is not None and len(fields_to_write) == len(self.adi_dataset.variables)

        async def ExecuteCommand(self):
            success = self.adi_dataset is not None and self.adi_dataset.is_open and (await self.client_local.server.DatasetWrite(self.adi_dataset, self.write_mode_value, [self.fields_to_write]))
            result = {"Success": success}
            return result

        def BuildCommandBinaryData(self):
            line_data = AdiCommands.BuildDataForBuffer(self.adi_dataset.variables, self.fields_to_write)
            number_values = line_data["NumberValues"]
            total_length = len(line_data["Data"]) + len(line_data["Blob"])
            bytes_fields = line_data["Data"] + line_data["Blob"]
            bit_test_data = line_data["BitTest"]

            write_mode = 0
            if adi.AdiEnums.DataSetWriteModes.Overwrite in self.write_mode_value:
                write_mode |= 0x10
            if adi.AdiEnums.DataSetWriteModes.Exclusive in self.write_mode_value:
                write_mode |= 0x01
            if adi.AdiEnums.DataSetWriteModes.Insert in self.write_mode_value:
                write_mode |= 0x02
            if adi.AdiEnums.DataSetWriteModes.Update in self.write_mode_value:
                write_mode |= 0x03
            if adi.AdiEnums.DataSetWriteModes.UpdateExact in self.write_mode_value:
                write_mode |= 0x04
            if adi.AdiEnums.DataSetWriteModes.StoreData in self.write_mode_value:
                write_mode |= 0x20
            if adi.AdiEnums.DataSetWriteModes.UserUtcTime in self.write_mode_value:
                write_mode |= 0x40
            if adi.AdiEnums.DataSetWriteModes.Compressed in self.write_mode_value:
                write_mode |= 0x80
            if adi.AdiEnums.DataSetWriteModes.PostRealTimeData in self.write_mode_value:
                write_mode |= 0x08
            bytes_data = struct.pack("<II", write_mode, total_length)
            bytes_data += bytes_fields + struct.pack("<I", number_values) + bit_test_data
            
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            total_bytes = bytes_header + bytes_data
            return total_bytes

    # 0x900b - ADI_DATASET_READ (single)
    class DataSetRead(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x900b

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            direction = 0
            if header.length == 4: [direction] = struct.unpack_from("<I", data, 16)
            read_previous = direction == 1
            return AdiCommands.DataSetRead(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), read_previous=read_previous)

        def __init__(self, client=None, adi_dataset=None, read_previous=False):
            super().__init__(name="ADI_DATASET_READ", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.read_previous = read_previous
            self.is_valid = self.adi_dataset is not None

        async def GetLocalResult(self):
            success = self.is_valid and self.adi_dataset.is_open
            result = {"Success": success}
            if success:
                direction = -1 if self.read_previous else 1
                number_lines = 1
                data = await self.client_local.server.DatasetRead(adi_dataset=self.adi_dataset, direction=direction, number_lines=number_lines)
                if data is None: result["Success"] = False
                else: result["Data"] = data
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            data_to_return = b''
            if success:
                try:
                    number_values = 0
                    data = b''
                    for line in result["Data"]:
                        line_data = AdiCommands.BuildDataForBuffer(self.adi_dataset.variables, line)
                        
                        if number_values == 0: number_values = line_data["NumberValues"]
                        bytes_line = line_data["Data"] + line_data["Blob"]
                        length_line = len(bytes_line)
                        
                        data += struct.pack("<I", length_line) + bytes_line + struct.pack("<I", number_values) + line_data["BitTest"]
                
                    data_to_return = data
                except Exception as ex:
                    success = False
            return adi.AdiDefinitions.AdiResponse(param=0x01 if not success else 0x00 if len(result["Data"]) > 0 else 0x0b, value=0, data=data_to_return)

        def BuildCommandBinaryData(self):
            data = struct.pack("<I", 1 if self.read_previous else 0)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

        def TranslateResponseFromBytes(self, response):
            result = {}
            success = True
            if response.param == 0x0b:
                result["Data"] = []
                success = True
            else:
                success = self.adi_dataset is not None and response.param == 0x00 and response.value == 0 and response.length >= 4
                if success:
                    try:
                        result_data = []
                        number_lines = 1
                        ix = 0
                        [length_record] = struct.unpack_from("<I", response.data, ix)
                        ix += 4
                        [number_variables] = struct.unpack_from("<I", response.data, ix + length_record)
                        number_bytes_bit_test = math.ceil(number_variables / 8.0)
                        ix_bit_fields_test = ix + length_record + 4
                        for _ in range(number_lines):
                            if ix + length_record > response.length: raise Exception("Not enough bytes")
                            result_data.append(AdiCommands.ExtractDataFromBuffer(response.data, ix, length_record, ix_bit_fields_test, self.adi_dataset.variables, number_variables))
                            ix += length_record + 4 + number_bytes_bit_test
                        result["Data"] = result_data
                    except Exception as ex:
                        success = False
                
            result["Success"] = success
            return result
    
    # 0x900c - ADI_DATASET_SET_INDEX_POSITION
    class DataSetSetIndexPosition(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x900c

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            mode_seek = None
            record_number = None
            value_search = None
            if header.length == 16:
                mode_seek, record_number, value_search = struct.unpack_from("<IId", data, 16)
            return AdiCommands.DataSetSetIndexPosition(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), mode_seek=adi.AdiEnums.SeekPositionMode(mode_seek), record_number=record_number, value_search=value_search)

        def __init__(self, client=None, adi_dataset=None, mode_seek=None, record_number=None, value_search=None):
            super().__init__(name="ADI_DATASET_SET_INDEX_POSITION", code=self.GetCode(), client=client, response_expected=False)
            self.adi_dataset = adi_dataset
            self.mode_seek = mode_seek
            self.record_number = record_number
            self.value_search = value_search
            # if mode_seek != adi.AdiEnums.SeekPositionMode.RecordNumber and value_search is not None:
            #     self.record_number = int(value_search)

            if self.mode_seek == adi.AdiEnums.SeekPositionMode.Time and value_search is not None and type(value_search).__name__ == "datetime":
                value_timestamp = AdiCommands.DateToInsiteNumber(value_search)
                self.value_search = value_timestamp
                self.record_number = int(value_timestamp)
            
            self.is_valid = self.adi_dataset is not None and ( \
                (self.mode_seek == adi.AdiEnums.SeekPositionMode.Depth and value_search is not None) \
                or (self.mode_seek == adi.AdiEnums.SeekPositionMode.Time and value_search is not None) \
                or (self.mode_seek == adi.AdiEnums.SeekPositionMode.RecordNumber and record_number is not None) \
                or self.mode_seek == adi.AdiEnums.SeekPositionMode.Start or self.mode_seek == adi.AdiEnums.SeekPositionMode.End)

        async def ExecuteCommand(self):
            success = await self.client_local.server.DatasetSetIndexPosition(adi_dataset=self.adi_dataset, mode_seek=self.mode_seek, record_number=self.record_number, value_search=self.value_search)
            result = {"Success": success}
            return result

        def BuildCommandBinaryData(self):
            data = struct.pack("<IId", self.mode_seek.value, 0 if self.record_number is None else self.record_number, 0 if self.value_search is None else self.value_search)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

    # 0x900d - ADI_DATASET_DELETE_SINGLE_LINE_BY_INDEX_POSITION
    class DataSetDeleteSingleLineByIndexPosition(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x900d

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            mode_seek = None
            record_number = None
            value_search = None
            if header.length == 16:
                mode_seek, record_number, value_search = struct.unpack_from("<IId", data, 16)
            return AdiCommands.DataSetDeleteSingleLineByIndexPosition(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), mode_seek=adi.AdiEnums.SeekPositionMode(mode_seek), record_number=record_number, value_search=value_search)

        def __init__(self, client=None, adi_dataset=None, mode_seek=adi.AdiEnums.SeekPositionMode.Start, record_number=None, value_search=None):
            super().__init__(name="ADI_DATASET_DELETE_SINGLE_LINE_BY_INDEX_POSITION", code=self.GetCode(), client=client, response_expected=False)
            self.adi_dataset = adi_dataset
            self.mode_seek = mode_seek
            self.record_number = record_number
            self.value_search = value_search
            # if mode_seek != adi.AdiEnums.SeekPositionMode.RecordNumber and value_search is not None:
            #     self.record_number = int(value_search)

            if self.mode_seek == adi.AdiEnums.SeekPositionMode.Time and value_search is not None and type(value_search).__name__ == "datetime":
                value_timestamp = AdiCommands.DateToInsiteNumber(value_search)
                self.value_search = value_timestamp
                self.record_number = int(value_timestamp)
            
            self.is_valid = self.adi_dataset is not None and ( \
                (self.mode_seek == adi.AdiEnums.SeekPositionMode.Depth and value_search is not None) \
                or (self.mode_seek == adi.AdiEnums.SeekPositionMode.Time and value_search is not None) \
                or (self.mode_seek == adi.AdiEnums.SeekPositionMode.RecordNumber and record_number is not None) \
                or (self.mode_seek == adi.AdiEnums.SeekPositionMode.Start and record_number is not None) \
                or self.mode_seek == adi.AdiEnums.SeekPositionMode.End)

        async def ExecuteCommand(self):
            success = await self.client_local.server.DatasetDeleteSingleLineByIndexPosition(adi_dataset=self.adi_dataset, mode_seek=self.mode_seek, record_number=self.record_number, value_search=self.value_search)
            result = {"Success": success}
            return result

        def BuildCommandBinaryData(self):
            data = struct.pack("<IId", self.mode_seek.value, 0 if self.record_number is None else self.record_number, 0 if self.value_search is None else self.value_search)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

    # 0x9010 - ADI_DATASET_READ_MULTIPLE
    class DataSetReadMultiple(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9010

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            start_pos = None
            number_records = None
            direction = None
            if header.length == 12:
                start_pos, number_records, direction = struct.unpack_from("<III", data, 16)
            return AdiCommands.DataSetReadMultiple(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), start_pos=start_pos, number_records=number_records, direction=direction)

        def __init__(self, client=None, adi_dataset=None, start_pos:int=None, number_records:int=None, direction:int=None):
            super().__init__(name="ADI_DATASET_READ_MULTIPLE", code=self.GetCode(), client=client, response_expected=False)
            self.adi_dataset = adi_dataset
            self.start_pos = start_pos
            self.number_records = number_records
            self.direction = direction

            self.is_valid = self.adi_dataset is not None and direction in [0, 1]

        async def GetLocalResult(self):
            success = self.adi_dataset is not None and self.adi_dataset.is_open and (await self.client_local.server.DatasetSetIndexPosition(self.adi_dataset, mode_seek=adi.AdiEnums.SeekPositionMode.RecordNumber, record_number=self.start_pos))
            result = {"Success": success}
            if success:
                data = await self.client_local.server.DatasetRead(self.adi_dataset, self.direction, self.number_records)
                if data is None: result["Success"] = False
                else: result["Data"] = data
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            value_to_return = 0
            data_to_return = b''
            if success:
                try:
                    number_values = 0
                    data = b''
                    for line in result["Data"]:
                        line_data = AdiCommands.BuildDataForBuffer(self.adi_dataset.variables, line)
                        
                        if number_values == 0: number_values = line_data["NumberValues"]
                        bytes_line = line_data["Data"] + line_data["Blob"]
                        length_line = len(bytes_line)
                        
                        data += struct.pack("<I", length_line) + bytes_line + line_data["BitTest"]
                
                    value_to_return = len(result["Data"])
                    data_to_return = struct.pack("<I", number_values) + data
                except Exception as ex:
                    success = False
            return adi.AdiDefinitions.AdiResponse(param=0x01 if not success else 0x00 if value_to_return > 0 else 0x0b, value=value_to_return, data=data_to_return)

        def BuildCommandBinaryData(self):
            data = struct.pack("<III", self.start_pos, self.number_records, self.direction)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

        def TranslateResponseFromBytes(self, response):
            result = {}
            success = True
            if response.param == 0x0b:
                result["Data"] = []
                success = True
            else: success = self.adi_dataset is not None and response.param == 0x00 and response.value <= self.number_lines
            
            if success and response.param == 0x00:
                try:
                    result_data = []
                    number_lines = response.value
                    number_values = 0
                    if number_lines > 0: [number_values] = struct.unpack_from("<I", response.data)
                    number_bytes_bit_test = math.ceil(number_values / 8.0)
                    ix = 4
                    for _ in range(number_lines):
                        [length_record] = struct.unpack_from("<I", response.data, ix)
                        ix += 4
                        if ix + length_record > response.length: raise Exception("Not enough bytes")
                        result_data.append(AdiCommands.ExtractDataFromBuffer(response.data, ix, length_record, ix + length_record, self.adi_dataset.variables, number_values))
                        ix += length_record + number_bytes_bit_test
                    result["Data"] = result_data
                except Exception as ex:
                    success = False
                
            result["Success"] = success
            return result

    # 0x9011 - ADI_DATASET_UPDATE_BY_INDEX_POSITION (multiple)
    class DataSetUpdateByIndexPosition(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9011

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            adi_dataset:adi.AdiDefinitions.AdiDataSetReader = client.GetAdiDataSetReader(header.param)

            mode_update = None
            record_number = None
            lines_to_write = []
            if adi_dataset is not None and header.length >= 16:
                record_number, mode_update, number_lines, number_values = struct.unpack_from("<IIII", data, 16)
                ix = 16 + 16
                for i in range(number_lines):
                    (number_bytes,) = struct.unpack_from("<I", data, ix)
                    if header.length >= 16 + number_lines * 4 + number_bytes:
                        fields_to_write = AdiCommands.ExtractDataFromBuffer(data, 16 + 16 + number_lines * 4, number_bytes, 16 + 16 + number_lines * 4 + number_bytes, adi_dataset.variables, number_values)
                        lines_to_write.append(fields_to_write)
                    ix += number_bytes + 4
            
            return AdiCommands.DataSetUpdateByIndexPosition(client=client, adi_dataset=adi_dataset, mode_update=mode_update, record_number=record_number, fields_to_write=lines_to_write)

        def __init__(self, client=None, adi_dataset=None, mode_update=None, record_number=None, lines_to_write=[]):
            super().__init__(name="ADI_DATASET_UPDATE_BY_INDEX_POSITION", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.record_number = record_number
            self.mode_update = mode_update
            self.lines_to_write = lines_to_write
            self.is_valid = self.adi_dataset is not None and len(lines_to_write) > 0 and len(lines_to_write[0]) == len(self.adi_dataset.variables) and record_number is not None

        async def GetLocalResult(self):
            success = self.adi_dataset is not None and self.adi_dataset.is_open and (await self.client_local.server.DatasetUpdateByIndexPosition(self.adi_dataset, self.mode_update, self.record_number, self.lines_to_write))
            result = {"Success": success}
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            response = adi.AdiDefinitions.AdiResponse(param=0x00 if success else 0x01)
            return response

        def BuildCommandBinaryData(self):
            number_values_per_line = 0
            arr_lengths = [0] * len(self.lines_to_write)
            bytes_lines = b''
            bit_test_data = b''
            for i in range(len(self.lines_to_write)):
                line_data = AdiCommands.BuildDataForBuffer(self.adi_dataset.variables, self.lines_to_write[i])
                if i == 0: number_values_per_line = line_data["NumberValues"]
                arr_lengths[i] = len(line_data["Data"]) + len(line_data["Blob"])
                bytes_lines += line_data["Data"] + line_data["Blob"]
                bit_test_data += line_data["BitTest"]

            write_mode = 0
            # if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.Overwrite:
            #     write_mode |= 0x10
            # if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.Exclusive:
            #     write_mode |= 0x01
            # if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.Insert:
            #     write_mode |= 0x02
            # if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.Update:
            #     write_mode |= 0x03
            # if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.UpdateExact:
            #     write_mode |= 0x04
            # if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.StoreData:
            #     write_mode |= 0x20
            # if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.UserUtcTime:
            #     write_mode |= 0x40
            # if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.Compressed:
            #     write_mode |= 0x80
            bytes_data = struct.pack("<IIII", self.record_number, write_mode, len(self.lines_to_write), number_values_per_line)
            bytes_data += struct.pack(f"<{''.join(['I'] * len(self.lines_to_write))}", *arr_lengths)
            bytes_data += bytes_lines + bit_test_data
            
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            total_bytes = bytes_header + bytes_data
            return total_bytes

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            return result

    # 0x9012 - ADI_DATASET_DELETE_BY_INDEX_POSITION (multiple)
    class DataSetDeleteByIndexPosition(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9012

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            record_number = None
            number_records = None
            if header.length == 8:
                record_number, number_records = struct.unpack_from("<II", data, 16)
            return AdiCommands.DataSetDeleteByIndexPosition(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), record_number=record_number, number_records=number_records)

        def __init__(self, client=None, adi_dataset=None, record_number=None, number_records=None):
            super().__init__(name="ADI_DATASET_DELETE_BY_INDEX_POSITION", code=self.GetCode(), client=client, response_expected=False)
            self.adi_dataset = adi_dataset
            self.record_number = record_number
            self.number_records = number_records
            self.is_valid = self.adi_dataset is not None and record_number is not None and number_records is not None

        async def ExecuteCommand(self):
            success = await self.client_local.server.DatasetDeleteByIndexPosition(adi_dataset=self.adi_dataset, record_number=self.record_number, number_records=self.number_records)
            result = {"Success": success}
            return result

        def BuildCommandBinaryData(self):
            data = struct.pack("<II", self.record_number, self.number_records)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

    # 0x9013 - ADI_DATASET_QUERY_NUM_RECORDS
    class DataSetQueryNumberRecords(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9013

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.DataSetQueryNumberRecords(client=client, adi_dataset=client.GetAdiDataSetReader(header.param))

        def __init__(self, client=None, adi_dataset=None):
            super().__init__(name="ADI_DATASET_QUERY_NUM_RECORDS", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.is_valid = self.adi_dataset is not None

        async def GetLocalResult(self):
            success = self.adi_dataset is not None and self.adi_dataset.is_open
            result = { "Success": success }
            if success:
                number_records = await self.client_local.server.DatasetGetNumberOfRecords(self.adi_dataset)
                if number_records is None: result["Success"] = False
                else: result["NumberOfRecords"] = number_records
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            bytes_data = struct.pack("<I", result["NumberOfRecords"])
            response = adi.AdiDefinitions.AdiResponse(data=bytes_data)
            return response

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length == 4
            result = {"Success": success}
            if success: [result["NumberOfRecords"]] = struct.unpack_from("<I", response.data)
            return result

    # 0x9014 - ADI_DATASET_SET_UNKNOWN_TIME_3
    class DataSetSetSmoothUnknownTime3(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9014

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            unknown1 = None
            unknown2 = None
            value_search = None
            if header.length == 16:
                value_search, unknown1, unknown2 = struct.unpack_from("<DII", data, 16)
            return AdiCommands.DataSetSetSmoothUnknownTime3(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), value_search=value_search, unknown1=unknown1, unknown2=unknown2)

        def __init__(self, client=None, adi_dataset=None, value_search=None, unknown1=None, unknown2=None):
            super().__init__(name="ADI_DATASET_SET_UNKNOWN_TIME_3", code=self.GetCode(), client=client, response_expected=False)
            self.adi_dataset = adi_dataset
            self.value_search = value_search
            self.unknown1 = unknown1
            self.unknown2 = unknown2
            self.is_valid = self.adi_dataset is not None

        async def ExecuteCommand(self):
            success = await self.client_local.server.DatasetSetIndexPosition(adi_dataset=self.adi_dataset, mode_seek=self.mode_seek, unknown2=self.unknown2, value_search=self.value_search)
            result = {"Success": success}
            raise Exception("Not implemented!")

        def BuildCommandBinaryData(self):
            # data = struct.pack("<dII", 0 if self.value_search is None else self.value_search, 0 if self.unknown1 is None else self.unknown1, 0 if self.unknown2 is None else self.unknown2)
            data = struct.pack("<II", 0 if self.value_search is None else int(self.value_search), 0)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))#, format=adi.AdiEnums.OutputFormat.BINARY_FULL)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

    # 0x9015 - ADI_DATASET_SET_UNKNOWN
    class DataSetSetSmoothUnknown(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9015

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            unknown1 = None
            unknown2 = None
            value_search = None
            if header.length == 16:
                value_search, unknown1, unknown2 = struct.unpack_from("<DII", data, 16)
            return AdiCommands.DataSetSetSmoothUnknown(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), unknown1=unknown1, unknown2=unknown2, value_search=value_search)

        def __init__(self, client=None, adi_dataset=None, value_search=None, unknown1=None, unknown2=None):
            super().__init__(name="ADI_DATASET_SET_UNKNOWN", code=self.GetCode(), client=client, response_expected=False)
            self.adi_dataset = adi_dataset
            self.value_search = value_search
            self.unknown1 = unknown1
            self.unknown2 = unknown2
            self.is_valid = self.adi_dataset is not None

        async def ExecuteCommand(self):
            success = await self.client_local.server.DatasetSetIndexPosition(adi_dataset=self.adi_dataset, mode_seek=self.mode_seek, unknown2=self.unknown2, value_search=self.value_search)
            result = {"Success": success}
            return result

        def BuildCommandBinaryData(self):
            data = struct.pack("<dII", 0 if self.value_search is None else self.value_search, 0 if self.unknown1 is None else self.unknown1, 0 if self.unknown2 is None else self.unknown2)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

    # 0x9016 - ADI_DATASET_SET_INDEX_TYPE
    class DataSetSetIndexType(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9016

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            index_type = None
            if header.length == 4: [index_type] = struct.unpack_from("<I", data, 16)
            return AdiCommands.DataSetSetIndexType(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), index_type=adi.AdiEnums.IndexType(index_type))

        def __init__(self, client=None, adi_dataset=None, index_type=None):
            super().__init__(name="ADI_DATASET_SET_INDEX_TYPE", code=self.GetCode(), client=client, response_expected=False)
            self.adi_dataset = adi_dataset
            self.index_type = index_type
            self.is_valid = self.adi_dataset is not None and self.index_type is not None

        async def ExecuteCommand(self):
            success = self.adi_dataset is not None and self.adi_dataset.is_open
            if success:
                # Remember that "variables" is an array of dictionaries
                # containing the keys "Variable" and "UnitOption"
                self.adi_dataset.index_type = self.index_type
                self.cursor_pos = 0
                
            return { "Success": success }

        def BuildCommandBinaryData(self):
            data = struct.pack("<I", self.index_type.value)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

    # 0x901c - ADI_DATASET_LOOKUP
    class DataSetLookup(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x901c

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            variable = None
            try:
                start_pos, end_pos, direction, var_name, var_type_id, unit_option = struct.unpack_from("<III16sII", data, 16)
                name = fromArrayToUTF8(var_name)
                v = adi.AdiDefinitions.AdiVariable(name=name, format=adi.AdiEnums.StorageType(var_type_id), unit_type=adi.AdiDefinitions.UnitType(unit_option=adi.AdiDefinitions.UnitOption(id=unit_option)))
                variable = {"Variable": v, "UnitOption": v.unit_type.unit_option}
                v.size = int((len(data) - 16 - 36) / 2)
                fake_data_with_bit_checks = bytearray(data[52:])
                fake_data_with_bit_checks.append(0x03)  # Representing two existing values
                start_value = AdiCommands.ExtractDataFromBuffer(fake_data_with_bit_checks, 0, v.size, 2 * v.size, [variable], 1)[0]
                end_value = AdiCommands.ExtractDataFromBuffer(fake_data_with_bit_checks, v.size, v.size, 2 * v.size, [variable], 1)[0]
            except Exception as ex:
                variable = None
            return AdiCommands.DataSetLookup(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), start_pos=start_pos, end_pos=end_pos, direction=direction, variable=variable, start_value=start_value, end_value=end_value)

        def __init__(self, client=None, adi_dataset=None, start_pos=None, end_pos=None, direction=None, variable=None, start_value=None, end_value=None):
            super().__init__(name="ADI_DATASET_LOOKUP", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.start_pos = start_pos
            self.end_pos = end_pos
            self.direction = direction
            self.variable = variable
            self.start_value = start_value
            self.end_value = end_value
            
            self.is_valid = self.adi_dataset is not None and variable is not None and direction in [0, 1]

        async def GetLocalResult(self):
            success = self.is_valid and self.adi_dataset.is_open and self.variable is not None
            result = {"Success": success}
            if success:
                direction = adi.AdiEnums.SearchDirection.Down if self.direction == 1 else adi.AdiEnums.SearchDirection.Up
                data = await self.client_local.server.DatasetSearchValue(
                    adi_dataset=self.adi_dataset,
                    variable=self.variable,
                    search_direction=direction,
                    start_pos=self.start_pos,
                    end_pos=self.end_pos,
                    start_value=self.start_value,
                    end_value=self.end_value
                )
                if data is None: result["Success"] = False
                else:
                    result["Found"] = data != -1
                    if data != -1: result["Position"] = data
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            response = adi.AdiDefinitions.AdiResponse(param=0x01 if not result["Success"] else 0x0b if not result["Found"] else 0x00)
            if result["Success"]: response.value = result["Position"]
            return response

        def BuildCommandBinaryData(self):
            v = self.variable["Variable"]
            unit_option = self.variable["UnitOption"]
            unit_option_id = 0 if unit_option is None or unit_option.id is None else unit_option.id
            data = struct.pack("<III16sII", 0 if self.start_pos is None else self.start_pos,
                0 if self.end_pos is None else self.end_pos, self.direction,
                toUTF8Array(v.name), v.GetStorageType().value, unit_option_id)
            
            # Getting the bytes for the current data
            # [0] - Array of "values_present" for current value
            #       (if variable is array, then it will be multiple elements)
            # [1] - Content in bytes for the value
            # [2] - If this variable requires to add data to BLOB area, then
            #       blob data will be here
            try:
                tmp_v = copy.copy(v)
                tmp_v.size = max(4, tmp_v.size)
                bytes_start_value = AdiCommands.BuildBytesForVariableValue(tmp_v, self.start_value)
                bytes_end_value = AdiCommands.BuildBytesForVariableValue(tmp_v, self.end_value)
            except Exception as ex:
                raise Exception("Start or end values not in the correct format")
            
            # Adding to the bit test array if the current value is present
            data += bytes_start_value[1] + bytes_start_value[2]
            data += bytes_end_value[1] + bytes_end_value[2]
            
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

        def TranslateResponseFromBytes(self, response:adi.AdiDefinitions.AdiResponse):
            if response.param == 0x01:
                result = {"Success": False}
            elif response.param == 0x0b:
                result = {"Success": True, "Found": False}
            else:
                result = {"Success": True, "Found": True, "Position": response.value}
            return result

    # 0x901d - ADI_DATASET_READ_COMMENTS
    class DataSetReadComments(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x901d

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.DataSetReadComments(client=client, adi_dataset=client.GetAdiDataSetReader(header.param))

        def __init__(self, client=None, adi_dataset=None):
            super().__init__(name="ADI_DATASET_READ_COMMENTS", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.is_valid = self.adi_dataset is not None

        async def GetLocalResult(self):
            success = self.adi_dataset is not None
            result = { "Success": success }
            if success:
                result["Comments"] = await self.client_local.server.DatasetReadComments(self.adi_dataset)
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            bytes_data = struct.pack("<I", result["NumberOfRecords"])
            response = adi.AdiDefinitions.AdiResponse(data=bytes_data)
            return response

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.value == response.length
            result = {"Success": success}
            if success:
                [comments] = struct.unpack_from(f"<{response.length}s", response.data)
                result["Comments"] = fromArrayToUTF8(comments)
            return result
    
    # 0x901f - ADI_DATASET_APPEND_COMMENTS
    class DataSetAppendComments(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x901f

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            (comments,) = struct.unpack_from(f"<{header.length}s", data, 16)
            comments = fromArrayToUTF8(comments)
            return AdiCommands.DataSetAppendComments(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), comments=comments)

        def __init__(self, client=None, adi_dataset=None, comments=None):
            super().__init__(name="ADI_DATASET_APPEND_COMMENTS", code=self.GetCode(), client=client, response_expected=False)
            self.adi_dataset = adi_dataset
            self.comments = comments
            self.is_valid = self.adi_dataset is not None and self.comments is not None

        async def ExecuteCommand(self):
            success = self.adi_dataset is not None and self.adi_dataset.is_open and (await self.client_local.server.DatasetAppendComments(self.adi_dataset, self.comments))
            result = {"Success": success}
            return result

        def BuildCommandBinaryData(self):
            bytes_comments = toUTF8Array(self.comments)
            length = len(bytes_comments) + 1
            bytes_data = struct.pack(f"<I{length}s", length, bytes_comments)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

    # 0x9021 - ADI_DATASET_READ_NEXT (multiple)
    class DataSetReadNext(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9021

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            number_lines = None
            if header.length == 4: [number_lines] = struct.unpack_from("<I", data, 16)
            return AdiCommands.DataSetReadNext(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), number_lines=number_lines)

        def __init__(self, client=None, adi_dataset=None, number_lines=None):
            super().__init__(name="ADI_DATASET_READ_NEXT", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.number_lines = number_lines
            self.is_valid = self.adi_dataset is not None and self.number_lines is not None

        async def GetLocalResult(self):
            success = self.is_valid and self.adi_dataset.is_open
            result = {"Success": success}
            if success:
                data = await self.client_local.server.DatasetRead(adi_dataset=self.adi_dataset, direction=1, number_lines=self.number_lines)
                if data is None: result["Success"] = False
                else: result["Data"] = data
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            value_to_return = 0
            data_to_return = b''
            if success:
                try:
                    number_values = 0
                    data = b''
                    for line in result["Data"]:
                        line_data = AdiCommands.BuildDataForBuffer(self.adi_dataset.variables, line)
                        
                        if number_values == 0: number_values = line_data["NumberValues"]
                        bytes_line = line_data["Data"] + line_data["Blob"]
                        length_line = len(bytes_line)
                        
                        data += struct.pack("<I", length_line) + bytes_line + line_data["BitTest"]
                
                    value_to_return = len(result["Data"])
                    data_to_return = struct.pack("<I", number_values) + data
                except Exception as ex:
                    success = False
            return adi.AdiDefinitions.AdiResponse(param=0x01 if not success else 0x00 if value_to_return > 0 else 0x0b, value=value_to_return, data=data_to_return)

        def BuildCommandBinaryData(self):
            data = struct.pack("<I", self.number_lines)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

        def TranslateResponseFromBytes(self, response):
            result = {}
            success = True
            if response.param == 0x0b:
                result["Data"] = []
                success = True
            elif response.param == 0x14:
                result["Data"] = []
                success = True
            else: success = self.adi_dataset is not None and response.param == 0x00 and response.value <= self.number_lines
            
            if success and response.param == 0x00:
                try:
                    result_data = []
                    number_lines = response.value
                    number_values = 0
                    if number_lines > 0: [number_values] = struct.unpack_from("<I", response.data)
                    number_bytes_bit_test = math.ceil(number_values / 8.0)
                    ix = 4
                    for _ in range(number_lines):
                        [length_record] = struct.unpack_from("<I", response.data, ix)
                        ix += 4
                        if ix + length_record > response.length: raise Exception("Not enough bytes")
                        result_data.append(AdiCommands.ExtractDataFromBuffer(response.data, ix, length_record, ix + length_record, self.adi_dataset.variables, number_values))
                        ix += length_record + number_bytes_bit_test
                    result["Data"] = result_data
                except Exception as ex:
                    success = False
                
            result["Success"] = success
            return result

    # 0x9022 - ADI_DATASET_READ_WITH_LIMIT
    class DataSetReadWithLimit(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9022

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            number_lines = None
            limit_value = None
            block_read_option = None
            if header.length == 16: [number_lines, limit_value, block_read_option] = struct.unpack_from("<IdI", data, 16)
            return AdiCommands.DataSetReadWithLimit(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), number_lines=number_lines, limit_value=limit_value, block_read_option=adi.AdiEnums.BlockReadOption(block_read_option))

        def __init__(self, client=None, adi_dataset=None, number_lines=None, limit_value=None, block_read_option:adi.AdiEnums.BlockReadOption=None):
            super().__init__(name="ADI_DATASET_READ_WITH_LIMIT", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.number_lines = number_lines
            self.limit_value = limit_value
            self.block_read_option = block_read_option
            self.is_valid = self.adi_dataset is not None and self.number_lines is not None and self.limit_value is not None and self.block_read_option is not None

        async def GetLocalResult(self):
            success = self.is_valid and self.adi_dataset.is_open
            result = {"Success": success}
            if success:
                data = await self.client_local.server.DatasetReadWithLimit(adi_dataset=self.adi_dataset, number_lines=self.number_lines, start_from=self.start_from, block_read_option=self.block_read_option)
                if data is None: result["Success"] = False
                else: result["Data"] = data
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            raise Exception("Not implemented")

        def BuildCommandBinaryData(self):
            data = struct.pack("<IdI", 0 if self.number_lines is None else self.number_lines, 0 if self.limit_value is None else self.limit_value, 0 if self.block_read_option is None else self.block_read_option.value)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

        def TranslateResponseFromBytes(self, response):
            result = {}
            success = True
            if response.param == 0x0b:
                result["Data"] = []
                success = True
            elif response.param == 0x14:
                result["Data"] = []
                success = True
            else:
                print(f"p={hex(response.param)}, l={response.value}")
                success = self.adi_dataset is not None and response.param in [0x00, 0x05] and response.value <= self.number_lines
            
            if success and response.param in [0x00, 0x05]:
                try:
                    result_data = []
                    number_lines = response.value
                    number_values = 0
                    if number_lines > 0: [number_values] = struct.unpack_from("<I", response.data)
                    number_bytes_bit_test = math.ceil(number_values / 8.0)
                    ix = 4
                    for _ in range(number_lines):
                        [length_record] = struct.unpack_from("<I", response.data, ix)
                        ix += 4
                        if ix + length_record > response.length: raise Exception("Not enough bytes")
                        result_data.append(AdiCommands.ExtractDataFromBuffer(response.data, ix, length_record, ix + length_record, self.adi_dataset.variables, number_values))
                        ix += length_record + number_bytes_bit_test
                    result["Data"] = result_data
                except Exception as ex:
                    success = False
                
            result["Success"] = success
            return result

    # 0x9024 - ADI_DATASET_GET_CURRENT_POSITION
    class DataSetGetCurrentPosition(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9024

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.DataSetGetCurrentPosition(client=client, adi_dataset=client.GetAdiDataSetReader(header.param))

        def __init__(self, client=None, adi_dataset=None):
            super().__init__(name="ADI_DATASET_GET_CURRENT_POSITION", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.is_valid = self.adi_dataset is not None

        async def GetLocalResult(self):
            success = self.adi_dataset is not None and self.adi_dataset.is_open
            result = { "Success": success }
            if success:
                result["Position"] = self.adi_dataset.cursor_pos
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            response = adi.AdiDefinitions.AdiResponse(value=result["Position"])
            return response

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            if success: result["Position"] = response.value
            return result

    # 0x9026 - ADI_DATASET_WRITE_MULTIPLE
    class DataSetWriteMultiple(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9026

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            adi_dataset = client.GetAdiDataSetReader(header.param)
            write_mode_value = 0
            lines_to_write = []
            
            if adi_dataset is not None:
                # Structure is:
                # aa aa aa aa bb bb bb bb cc cc cc cc      aa = mode, bb = num_lines, cc = number_values
                # d1 d1 d1 d1 d2 d2 d2 d2 d3 d3 .. ..      dx = size of x line
                # Repeat num_lines times:
                #   AA BB CC DD .. ..                        data of every line
                #   MM NN OO PP .. ..                        extra data for PCHAR and PBYTE
                # At the end of every line, comes the bytes for the variables bit test for each line
                
                number_lines = 0
                try:
                    ix = 16
                    write_mode_value, number_lines, number_values = struct.unpack_from("<III", data, ix)
                    ix += 12
                    number_bytes_bit_test = math.ceil(float(len(number_values)) / 8.0)
                    lines_size = struct.unpack_from(f"<{''.join(['I'] * number_lines)}", ix)
                    ix_start_bit_test = ix
                    for ls in lines_size: ix_start_bit_test += ls
                    ix += number_lines * 4
                    for i in range(number_lines):
                        line_size = lines_size[i]
                        lines_to_write[i] = AdiCommands.ExtractDataFromBuffer(data, ix, line_size, ix_start_bit_test, adi_dataset.variables, number_values)
                        ix += line_size
                        ix_start_bit_test += number_bytes_bit_test
                except:
                    adi_dataset = None
            
            return AdiCommands.DataSetWriteMultiple(client=client, adi_dataset=adi_dataset, write_mode_value=write_mode_value, lines_to_write=lines_to_write)

        def __init__(self, client=None, adi_dataset=None, write_mode_value=0, lines_to_write=[]):
            super().__init__(name="ADI_DATASET_WRITE_MULTIPLE", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.write_mode_value = adi.AdiEnums.DataSetWriteModes(write_mode_value)
            self.lines_to_write = lines_to_write
            self.is_valid = self.adi_dataset is not None and len(lines_to_write) > 0

        async def GetLocalResult(self):
            success = self.adi_dataset is not None and self.adi_dataset.is_open and (await self.client_local.server.DatasetWriteMultiple(self.adi_dataset, self.write_mode_value, self.lines_to_write))
            result = {"Success": success}
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            response = adi.AdiDefinitions.AdiResponse(param=0x00 if success else 0x01)
            return response

        def BuildCommandBinaryData(self):
            number_values_per_line = 0
            arr_lengths = [0] * len(self.lines_to_write)
            bytes_lines = b''
            bit_test_data = b''
            for i in range(len(self.lines_to_write)):
                line_data = AdiCommands.BuildDataForBuffer(self.adi_dataset.variables, self.lines_to_write[i])
                if i == 0: number_values_per_line = line_data["NumberValues"]
                arr_lengths[i] = len(line_data["Data"]) + len(line_data["Blob"])
                bytes_lines += line_data["Data"] + line_data["Blob"]
                bit_test_data += line_data["BitTest"]

            write_mode = 0
            if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.Overwrite:
                write_mode |= 0x10
            if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.Exclusive:
                write_mode |= 0x01
            if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.Insert:
                write_mode |= 0x02
            if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.Update:
                write_mode |= 0x03
            if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.UpdateExact:
                write_mode |= 0x04
            if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.StoreData:
                write_mode |= 0x20
            if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.UserUtcTime:
                write_mode |= 0x40
            if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.Compressed:
                write_mode |= 0x80
            if self.write_mode_value == adi.AdiEnums.DataSetWriteModes.PostRealTimeData:
                write_mode |= 0x08
            
            bytes_data = struct.pack("<III", write_mode, len(self.lines_to_write), number_values_per_line)
            bytes_data += struct.pack(f"<{''.join(['I'] * len(self.lines_to_write))}", *arr_lengths)
            bytes_data += bytes_lines + bit_test_data
            
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            total_bytes = bytes_header + bytes_data
            return total_bytes

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            return result

    # 0x9029 - ADI_DATASET_LIST_BAG_DATA_FIELDS
    class DataSetListBagDataFields(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9029

        @staticmethod
        def CreateCommandFromBinaryData(client, header, _):
            return AdiCommands.DataSetListBagDataFields(client=client, adi_dataset=client.GetAdiDataSetReader(header.param))

        def __init__(self, client=None, adi_dataset=None):
            super().__init__(name="ADI_DATASET_LIST_BAG_DATA_FIELDS", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.is_valid = self.adi_dataset is not None

        async def GetLocalResult(self):
            success = self.is_valid
            result = { "Success": success }
            if success:
                variables = await self.client_local.server.DatasetListBagDataFields(self.adi_dataset)
                if variables is None: result["Success"] = None
                else: result["Variables"] = variables
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)

            data = b''
            variables = result["Variables"]
            for v in variables:
                data += struct.pack(f"<16s5s27sHHHHHH",
                                    toUTF8Array(v.name),
                                    toUTF8Array(v.mnemonic),
                                    toUTF8Array(v.curve_label),
                                    v.GetStorageType().value, v.size, v.unit_type_id, v.special, v.number_of_decimals, v.offset)
            response = adi.AdiDefinitions.AdiResponse(value=len(variables), data=data)
            return response

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            num_vars = response.value
            success = response.param == 0x00 and response.length == num_vars * 60
            result = {"Success": success}
            if success:
                variables_list = []
                ix = 0
                for _ in range(num_vars):
                    [name, mnemonic, curve_label, storage, size, unit_type, special, number_of_decimals, offset] = struct.unpack_from("<16s5s27sHHHHHH", response.data, ix)
                    name = fromArrayToUTF8(name)
                    mnemonic = fromArrayToUTF8(mnemonic)
                    curve_label = fromArrayToUTF8(curve_label)
                    ut = None
                    if self.client is not None and type(self.client).__name__ == 'AdiClientToRemote' and self.client.unit_types is not None and len(self.client.unit_types) > unit_type: ut = self.client.unit_types[unit_type]
                    elif self.client is not None and type(self.client).__name__ == 'AdiClient' and self.client_local.server is not None and self.client_local.server.unit_types is not None and len(self.client_local.server.unit_types) > unit_type: ut = self.client_local.server.unit_types[unit_type]
                    var = adi.AdiDefinitions.AdiVariable(name=name, mnemonic=mnemonic, curve_label=curve_label, size=size, unit_type_id=unit_type, special=special, number_of_decimals=number_of_decimals, unit_type=ut, format=adi.AdiEnums.StorageType(storage), offset=offset)
                    variables_list.append(var)
                    ix += 60
                result["Variables"] = variables_list
            return result

    # 0x902a - ADI_DATASET_READ_OVER_RANGE (single)
    class DataSetReadOverRange(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x902a

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            start_read, end_read = None, None
            if header.length == 16: [start_read, end_read] = struct.unpack_from("<dd", data, 16)
            return AdiCommands.DataSetReadOverRange(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), start_read=start_read, end_read=end_read)

        def __init__(self, client=None, adi_dataset=None, start_read:float=None, end_read:float=None):
            super().__init__(name="ADI_DATASET_READ_OVER_RANGE", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.start_read = start_read
            self.end_read = end_read
            self.is_valid = self.adi_dataset is not None and self.start_read is not None and self.end_read is not None

        async def GetLocalResult(self):
            success = self.is_valid and self.adi_dataset.is_open
            result = {"Success": success}
            if success:
                data = await self.client_local.server.DatasetReadOverRange(adi_dataset=self.adi_dataset, start_read=self.start_read, end_read=self.end_read)
                if data is None: result["Success"] = False
                else: result["Data"] = data
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            raise Exception("Not implemented")

        def BuildCommandBinaryData(self):
            data = struct.pack("<dd", 0 if self.start_read is None else self.start_read, 0 if self.end_read is None else self.end_read)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

        def TranslateResponseFromBytes(self, response):
            result = {}
            success = True
            if response.param == 0x0b:
                result["Data"] = []
                success = True
            elif response.param == 0x14:
                result["Data"] = []
                success = True
            else: success = self.adi_dataset is not None and response.param == 0x00 and response.value == 0x00
            
            if success:
                try:
                    result_data = []
                    number_lines = 1    # always single read
                    number_values = 0
                    if number_lines > 0: [number_values] = struct.unpack_from("<I", response.data)
                    number_bytes_bit_test = math.ceil(number_values / 8.0)
                    ix = 4
                    for _ in range(number_lines):
                        [length_record] = struct.unpack_from("<I", response.data, ix)
                        ix += 4
                        if ix + length_record > response.length: raise Exception("Not enough bytes")
                        result_data.append(AdiCommands.ExtractDataFromBuffer(response.data, ix, length_record, ix + length_record, self.adi_dataset.variables, number_values))
                        ix += length_record + number_bytes_bit_test
                    result["Data"] = result_data
                except Exception as ex:
                    success = False
                
            result["Success"] = success
            return result

    # 0x902e - ADI_DATASET_OPEN_RT_BROADCAST
    class DataSetOpenForRtBroadcast(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x902e

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            active_filters = None
            well = None
            run_number = None
            record = None
            description = None
            variables = []
            try:
                active_filters, run_number, record, well, description, number_variables = struct.unpack_from(
                    "<HH16s16s32sI", bytes(data[16:]))
                if active_filters & adi.AdiEnums.QueryFilterModes.WELL.value:
                    well = fromArrayToUTF8(well).strip()
                else:
                    well = None
                if active_filters & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value):
                    run_number = run_number
                else:
                    run_number = None
                if active_filters & adi.AdiEnums.QueryFilterModes.RECORD.value:
                    record = fromArrayToUTF8(record).strip()
                else:
                    record = None
                if active_filters & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value:
                    description = fromArrayToUTF8(description).strip()
                else:
                    description = None
                for i in range(number_variables):
                    offset = 16 + 2 + 2 + 16 + 16 + 32 + 4 + (i * 24)
                    size, offset, storage, unit_option, name = struct.unpack_from("<HHHH16s", data, offset)
                    name = fromArrayToUTF8(name)
                    v = adi.AdiDefinitions.AdiVariable(size=size, offset=offset, name=name, format=adi.AdiEnums.StorageType(storage), unit_type=adi.AdiDefinitions.UnitType(unit_option=adi.AdiDefinitions.UnitOption(id=unit_option)))
                    variables.append({"Variable": v, "UnitOption": v.unit_type.unit_option})
                open_mode_offset = 16 + 2 + 2 + 16 + 16 + 32 + 4 + (number_variables * 24)
                open_mode = 0 if len(data) < open_mode_offset + 2 else struct.unpack_from("<H", data, open_mode_offset)[0]
            except:
                variables = None
            return AdiCommands.DataSetOpenForRtBroadcast(client=client, active_filters=active_filters, well=well, run_number=run_number, record=record, description=description, variables=variables, open_mode_value=open_mode)

        def __init__(self, client=None, active_filters=0x00, well=None, run_number=None, record=None, description=None, variables:list[adi.AdiDefinitions.AdiVariable]=[], open_mode_value=None):
            super().__init__(name="ADI_DATASET_OPEN_RT_BROADCAST", code=self.GetCode(), client=client)
            self.active_filters = active_filters
            self.well = well
            self.run_number = run_number
            self.record = record
            self.description = description
            self.variables = variables
            self.open_mode_value = open_mode_value if open_mode_value is not None else adi.AdiEnums.RecordOpenModes.ReadWrite | adi.AdiEnums.RecordOpenModes.Create
            self.is_valid = variables is not None

        def GetDetails(self):
            details = []
            if self.well is not None and len(self.well) > 0: details.append(f"Well='{self.well}'")
            if self.run_number is not None: details.append(f"RunNumber={self.run_number}")
            if self.record is not None and len(self.record) > 0: details.append(f"Record='{self.record}'")
            if self.description is not None and len(self.description) > 0: details.append(f"Description='{self.description}'")
            details.append(f"Variables={len(self.variables)}")
            return ", ".join(details)

        async def GetLocalResult(self):
            adi_dataset:adi.AdiDefinitions.AdiDataSetReader = await self.client_local.server.DatasetPrepare(
                well=self.well,
                run_number=self.run_number,
                record=self.record,
                description=self.description,
                truncate_data=adi.AdiEnums.RecordOpenModes.NoTruncate not in self.open_mode_value,
                create_if_not_exists=adi.AdiEnums.RecordOpenModes.Create in self.open_mode_value
            )
            success = adi_dataset is not None
            if success:
                await self.client_local.server.DatasetOpen(self.client, adi_dataset, self.variables, self.open_mode_value)
                
            result = { "Success": success }

            if adi_dataset is not None:
                adi_dataset.open_mode_value = self.open_mode_value
                self.client_local.AddDataSetReader(adi_dataset)
                result["AdiDataSet"] = adi_dataset
                
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            elif not "AdiDataSet" in result: return adi.AdiDefinitions.AdiResponse(param=0x08)
            else: return adi.AdiDefinitions.AdiResponse(value=result["AdiDataSet"].id)

        def BuildCommandBinaryData(self):
            active_filters = 0
            if self.well is not None and len(self.well) > 0: active_filters |= adi.AdiEnums.QueryFilterModes.WELL.value
            if self.run_number is not None: active_filters |= adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value
            if self.record is not None and len(self.record) > 0: active_filters |= adi.AdiEnums.QueryFilterModes.RECORD.value
            if self.description is not None: active_filters |= adi.AdiEnums.QueryFilterModes.DESCRIPTION.value
            bytes_data = struct.pack("<HH16s16s32sI", active_filters, self.run_number, toUTF8Array(self.record), toUTF8Array(self.well), toUTF8Array(self.description), len(self.variables))
            for variable in self.variables:
                v:adi.AdiDefinitions.AdiVariable = variable["Variable"]
                unit_option = variable["UnitOption"]
                unit_option_id = 0 if unit_option is None or unit_option.id is None else unit_option.id
                size = v.size if v.number_of_elements == 1 else v.number_of_elements
                bytes_data += struct.pack("<HHHH16s", size, v.offset, v.GetStorageType().value, unit_option_id, toUTF8Array(v.name))
            bytes_data += struct.pack("<H", self.open_mode_value)

            # The property "output_format" is set in the constructor, but for both cases we send BINARY_SIMPLE
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data), format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            if success:
                adi_dataset = adi.AdiDefinitions.AdiDataSetReader(self.client, id=response.value, well=self.well, run_number=self.run_number, record=self.record, description=self.description, open_mode_value=self.open_mode_value)
                adi_dataset.variables = self.variables
                self.client.AddOpenedDataset(adi_dataset)
                result["AdiDataSet"] = adi_dataset
            return result

    # 0x9030 - ADI_DATASET_READ_FILE
    class DataSetReadFile(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9030

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            entry_name = None
            start_index = 0
            number_bytes = 1
            if header.length > 4:
                length_entryname = struct.unpack_from("<I", data, 16)
                if header.length >= 4 + length_entryname:
                    [entry_name] = struct.unpack_from(f"<{length_entryname}s", data, 20)
                    entry_name = fromArrayToUTF8(entry_name)
                if header.length >= 4 + length_entryname + 8:
                    [start_index, number_bytes] = struct.unpack_from(f"<II", data, 20 + length_entryname)
            return AdiCommands.DataSetReadFile(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), entry_name=entry_name, start_index=start_index, number_bytes=number_bytes)

        def __init__(self, client=None, adi_dataset=None, entry_name=None, start_index=0, number_bytes=1):
            super().__init__(name="ADI_DATASET_GET_FILE_SIZE", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.entry_name = entry_name
            self.start_index = start_index
            self.number_bytes = number_bytes
            self.is_valid = self.adi_dataset is not None and self.entry_name is not None

        async def GetLocalResult(self):
            success = self.adi_dataset is not None
            result = { "Success": success }
            if success:
                dataset_file:adi.AdiDefinitions.AdiDataSetFile = await self.client_local.server.DatasetReadFile(self.adi_dataset, entryname=self.entry_name, start_position=self.start_index, number_bytes=self.number_bytes)
                if dataset_file is None: result["Success"] = False
                else:
                    result["FileSize"] = dataset_file.file_size
                    result["Data"] = dataset_file.data
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            response = adi.AdiDefinitions.AdiResponse(param=0x00 if result["Success"] else 0x01)
            if result["Success"]:
                try:
                    file_size = 0
                    data = struct.pack(f"<IIB", 1, file_size, 0x7b)
                    response.value = 1
                    response.data = data
                except Exception as ex:
                    response.param = 0x01
            return response

        def BuildCommandBinaryData(self):
            entry_name = toUTF8Array(self.entry_name)
            length_entryname = len(entry_name) + 1
            if length_entryname < 0x80: length_entryname = 0x80
            bytes_data = struct.pack(f"<I{length_entryname}sII", length_entryname, entry_name, self.start_index, self.number_bytes)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length >= 8
            result = {}
            if success:
                try:
                    [number_bytes_returned, number_bytes_total] = struct.unpack_from("<II", response.data)
                    if response.length == number_bytes_returned + 8:
                        result["FileSize"] = number_bytes_total
                        result["Data"] = response.data[8:]
                    else: success = False
                except Exception as ex:
                    success = False
                    
            result["Success"] = success
            return result

    # 0x9032 - ADI_DATASET_GET_FILES_LIST
    class DataSetGetFilesList(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9032

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.DataSetGetFilesList(client=client, adi_dataset=client.GetAdiDataSetReader(header.param))

        def __init__(self, client=None, adi_dataset=None):
            super().__init__(name="ADI_DATASET_GET_FILES_LIST", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.is_valid = self.adi_dataset is not None

        async def GetLocalResult(self):
            success = self.adi_dataset is not None
            result = { "Success": success }
            if success:
                dataset_files:list[adi.AdiDefinitions.AdiDataSetFile] = await self.client_local.server.DataSetGetFilesList(self.adi_dataset)
                if dataset_files is None: result["Success"] = False
                else:
                    files = []
                    for dataset_file in dataset_files:
                        files.append({"EntryName": dataset_file.entry_name, "Filename": dataset_file.file_name, "FolderPath": dataset_file.folder})
                    result["Files"] = files
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            response = adi.AdiDefinitions.AdiResponse(param=0x00 if result["Success"] else 0x01)
            if result["Success"]:
                try:
                    number_files = len(result["Files"])
                    data = b''
                    bytes_filenames = b''
                    # First we have all file entry names (128 bytes each)
                    total_length_filenames = 0
                    for i in range(number_files):
                        data += struct.pack(f"<128s", toUTF8Array(result["Files"][i]["EntryName"]))
                        bytes_filename = toUTF8Array(result["Files"][i]["Filename"]) + b'\x00'
                        total_length_filenames += len(bytes_filename) + 1
                        bytes_filenames += bytes_filename
                    # Then we have a single 32-bit integer with the total length of all filenames
                    data += struct.pack("<I", total_length_filenames)
                    # Then we have all filenames
                    data += bytes_filenames
                    # Finally we have the folder path (same for all files)
                    if number_files > 0:
                        data += toUTF8Array(result["Files"][0]["FolderPath"]) + b'\x00'
                    response.value = number_files
                    response.data = data
                except Exception as ex:
                    response.param = 0x01
            return response 

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, format=0x04)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length >= 128 * response.value + 4
            result = {}
            number_files = response.value
            try:
                length_filenames = struct.unpack_from("<I", response.data, 128 * number_files)[0]
                folder_path_length = response.length - 128 * number_files - 4 - length_filenames
                folder_path = fromArrayToUTF8(struct.unpack_from(f"<{folder_path_length}s", response.data, 128 * number_files + 4 + length_filenames)[0])
                files = []
                ix_filename = number_files * 128 + 4
                for i in range(number_files):
                    entry_name = fromArrayToUTF8(struct.unpack_from(f"<128s", response.data, 128 * i)[0])
                    bytes_filename = b''
                    for ix_filename in range(ix_filename, response.length):
                        bytes_filename += bytes([response.data[ix_filename]])
                        if response.data[ix_filename] == 0: break
                    ix_filename += 1
                    files.append({
                        "EntryName": entry_name,
                        "Filename": fromArrayToUTF8(bytes_filename),
                        "FolderPath": folder_path
                    })
                result["Files"] = files
            except Exception as ex:
                success = False
                    
            result["Success"] = success
            return result

    # 0x9034 - ADI_DATASET_SET_TDA_FILTER
    class DataSetSetTDAFilter(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9034

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            activity = None
            if header.length == 4: [activity] = struct.unpack_from("<I", data, 16)
            return AdiCommands.DataSetSetTDAFilter(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), activity=activity)

        def __init__(self, client=None, adi_dataset=None, activity:int=None):
            super().__init__(name="ADI_DATASET_SET_TDA_FILTER", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.activity = activity
            self.is_valid = self.adi_dataset is not None and self.activity is not None

        async def GetLocalResult(self):
            success = True
            result = { "Success": success }
            if success:
                # Filter per activity and update records
                pass
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            response = adi.AdiDefinitions.AdiResponse(param=0x00 if success else 0x01)
            return response

        def BuildCommandBinaryData(self):
            data = struct.pack("<I", self.activity)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            return result

    # 0x9036 - ADI_DATASET_SET_UNKNOWN_TIME_4
    class DataSetSetSmoothUnknownTime4(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9036

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            unknown1 = None
            unknown2 = None
            value_search = None
            if header.length == 16:
                value_search, unknown1, unknown2 = struct.unpack_from("<DII", data, 16)
            return AdiCommands.DataSetSetSmoothUnknownTime4(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), value_search=value_search, unknown1=unknown1, unknown2=unknown2)

        def __init__(self, client=None, adi_dataset=None, value_search=None, unknown1=None, unknown2=None):
            super().__init__(name="ADI_DATASET_SET_UNKNOWN_TIME_3", code=self.GetCode(), client=client, response_expected=False)
            self.adi_dataset = adi_dataset
            self.value_search = value_search
            self.unknown1 = unknown1
            self.unknown2 = unknown2
            self.is_valid = self.adi_dataset is not None

        async def ExecuteCommand(self):
            success = await self.client_local.server.DatasetSetIndexPosition(adi_dataset=self.adi_dataset, mode_seek=self.mode_seek, unknown2=self.unknown2, value_search=self.value_search)
            result = {"Success": success}
            raise Exception("Not implemented!")

        def BuildCommandBinaryData(self):
            data = struct.pack("<dII", 0 if self.value_search is None else self.value_search, 0 if self.unknown1 is None else self.unknown1, 0 if self.unknown2 is None else self.unknown2)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

    # 0x9037 - ADI_DATASET_SEARCH_SMOOTH
    class DataSetSetSmoothUnknown2(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9037

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            unknown1 = None
            unknown2 = None
            value_search = None
            if header.length == 16:
                value_search, unknown1, unknown2 = struct.unpack_from("<DII", data, 16)
            return AdiCommands.DataSetSetSmoothUnknown2(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), unknown1=unknown1, unknown2=unknown2, value_search=value_search)

        def __init__(self, client=None, adi_dataset=None, value_search=None, unknown1=None, unknown2=None):
            super().__init__(name="ADI_DATASET_SEARCH_SMOOTH", code=self.GetCode(), client=client, response_expected=False)
            self.adi_dataset = adi_dataset
            self.value_search = value_search
            self.unknown1 = unknown1
            self.unknown2 = unknown2
            self.is_valid = self.adi_dataset is not None

        async def ExecuteCommand(self):
            success = await self.client_local.server.DatasetSetIndexPosition(adi_dataset=self.adi_dataset, mode_seek=self.mode_seek, unknown2=self.unknown2, value_search=self.value_search)
            result = {"Success": success}
            return result

        def BuildCommandBinaryData(self):
            data = struct.pack("<dII", 0 if self.value_search is None else self.value_search, 0 if self.unknown1 is None else self.unknown1, 0 if self.unknown2 is None else self.unknown2)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

    # 0x9039 - ADI_DATASET_GET_MIN_MAX_INDEX
    class DataSetGetMinMaxIndex(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x9039

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.DataSetGetMinMaxIndex(client=client, adi_dataset=client.GetAdiDataSetReader(header.param))

        def __init__(self, client=None, adi_dataset=None):
            super().__init__(name="ADI_DATASET_GET_MIN_MAX_INDEX", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.is_valid = self.adi_dataset is not None

        async def GetLocalResult(self):
            success = True
            result = { "Success": success }
            if success:
                # Filter per activity and update records
                result["MinIndex"] = 0.0
                result["MaxIndex"] = 0.0
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            response = adi.AdiDefinitions.AdiResponse(param=0x00 if success else 0x01)
            if success:
                data = struct.pack("<dd", result["MinIndex"], result["MaxIndex"])
                response.data = data
            return response

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length == 16
            result = {"Success": success}
            if success:
                result["MinIndex"], result["MaxIndex"] = struct.unpack_from("<dd", response.data)
            return result
    
    # 0x903d - ADI_DATASET_WRITE_VECTOR_ATTRIBUTES
    class DataSetWriteVectorAttributes(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x903d

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            variables = []
            ix = 16
            number_variables = struct.unpack_from("<I", data, ix)
            ix += 4
            for _ in range(len(number_variables)):
                var_name, unit_name, bin_start, bin_end, var_type_id, unused1, unused2 = struct.unpack_from("<16s16sddHIH", data, ix)
                ix += 56
                var_name = fromArrayToUTF8(var_name)
                unit_name = fromArrayToUTF8(unit_name)
                v = adi.AdiDefinitions.AdiVariable(name=var_name)
                v.vector_var_type = adi.AdiEnums.VarType(var_type_id)
                v.vector_bin_start = bin_start
                v.vector_bin_end = bin_end
                variables.append(v)
            return AdiCommands.DataSetWriteVectorAttributes(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), variables=variables)

        def __init__(self, client=None, adi_dataset=None, variables=None):
            super().__init__(name="ADI_DATASET_WRITE_VECTOR_ATTRIBUTES", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.variables = variables
            for v in self.variables:
                if v.vector_unit_type is None and v.vector_unit_type_id is not None:
                    if client and client.unit_types and len(client.unit_types) > v.vector_unit_type_id:
                        v.vector_unit_type = client.unit_types[v.vector_unit_type_id]
                    elif client and self.client_local.server and self.client_local.server.unit_types and len(self.client_local.server.unit_types) > v.vector_unit_type_id:
                        v.vector_unit_type = self.client_local.server.unit_types[v.vector_unit_type_id]
            self.is_valid = self.adi_dataset is not None and len(self.variables) > 0

        async def GetLocalResult(self):
            success = self.is_valid and (await self.client_local.server.DataSetWriteVectorAttributes(self.adi_dataset, self.variables))
            result = { "Success": success }
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            response = adi.AdiDefinitions.AdiResponse(param=0x00 if success else 0x01)
            return response

        def BuildCommandBinaryData(self):
            number_variables = len(self.variables)
            data = struct.pack("<I", number_variables)
            for v in self.variables:
                if v.vector_unit_type is None or v.vector_unit_type.name is None: raise Exception("Unit type not filled in")
                data += struct.pack("<16s16sddHIH", toUTF8Array(v.name), toUTF8Array(v.vector_unit_type.name), v.vector_bin_start, v.vector_bin_end, v.vector_var_type.value, 0, 0)
            
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.value == len(self.variables) and response.length == response.value * 56
            result = {"Success": success}
            return result
    
    # 0x903e - ADI_DATASET_READ_VECTOR_ATTRIBUTES
    class DataSetReadVectorAttributes(AdiCommand):
        @staticmethod
        def GetCode():
            return 0x903e

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            variables = []
            number_variables = 0
            if header.length >= 4: [number_variables] = struct.unpack_from("<I", data, 16)
            if header.length == 4 + number_variables * 16:
                variables = struct.unpack_from(f"<{''.join(['16s'] * number_variables)}", data, 20)
            return AdiCommands.DataSetReadVectorAttributes(client=client, adi_dataset=client.GetAdiDataSetReader(header.param), variables=variables)

        def __init__(self, client=None, adi_dataset=None, variables=None):
            super().__init__(name="ADI_DATASET_READ_VECTOR_ATTRIBUTES", code=self.GetCode(), client=client)
            self.adi_dataset = adi_dataset
            self.variables = variables
            self.is_valid = self.adi_dataset is not None and len(self.variables) > 0

        async def GetLocalResult(self):
            variables = await self.client_local.server.DataSetReadVectorAttributes(self.adi_dataset, self.variables)
            result = {"Success": variables is not None}
            if variables is not None: result["Variables"] = variables
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            response = adi.AdiDefinitions.AdiResponse(param=0x00 if success else 0x01)
            return response

        def BuildCommandBinaryData(self):
            number_variables = len(self.variables)
            data = struct.pack("<I", number_variables)
            for v in self.variables: data += struct.pack("<16s", toUTF8Array(v))
            
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.adi_dataset.id, length=len(data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.value == len(self.variables) and response.length == response.value * 56
            result = {"Success": success}

            unit_types = None
            if self.client and self.client.unit_types: unit_types = self.client.unit_types
            elif self.client and self.client_local.server and self.client_local.server.unit_types: unit_types = self.client_local.server.unit_types

            try:
                variables = []
                if success:
                    for i in range(len(self.variables)):
                        _, unit_name, bin_start, bin_end, var_type_id = struct.unpack_from("<16s16sddH", response.data, i * 56)
                        unit_name = fromArrayToUTF8(unit_name)
                        ut = None
                        if unit_types is not None:
                            for u in unit_types:
                                if u.name == unit_name:
                                    ut = u
                                    break
                        v = adi.AdiDefinitions.AdiVariable(name=self.variables[i])
                        if ut is not None:
                            v.vector_unit_type = ut
                            v.vector_unit_type_id = unit_types.index(ut)
                        v.vector_bin_start = bin_start
                        v.vector_bin_end = bin_end
                        v.vector_var_type = adi.AdiEnums.VectorVarType(var_type_id)
                        variables.append(v)
                    result["Variables"] = variables
            except: return {"Success": False}
            return result

    # 0xa003 - CMD_RT_DATASET_MONITOR
    class RT_MonitorDataset(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xa003

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            fields_present = 0
            well = None
            run_number = None
            record = None
            description = None
        
            fields_present, run_number, record, well, description, unknown1, unknown2, unknown3 = struct.unpack_from("<HH16s16s32sIII", data, 16)
            well = None if fields_present & adi.AdiEnums.QueryFilterModes.WELL.value == 0 else fromArrayToUTF8(well)
            run_number = None if fields_present & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value) == 0 else run_number
            record = None if fields_present & adi.AdiEnums.QueryFilterModes.RECORD.value == 0 else fromArrayToUTF8(record)
            description = None if fields_present & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value == 0 else fromArrayToUTF8(description)
                
            return AdiCommands.RT_MonitorDataset(client=client, fields_present=fields_present, well=well, run_number=run_number, record=record, description=description, u1=unknown1, u2=unknown2, u3=unknown3)

        def __init__(self, client=None, fields_present = 0x1d, well=None, run_number=None, record=None, description=None, u1=0, u2=0, u3=0):
            super().__init__(name="CMD_RT_DATASET_MONITOR", code=self.GetCode(), client=client, response_expected=False)
            self.fields_present = fields_present
            self.well = well
            if self.well is None and self.client is not None: self.well = self.client.well
            self.run_number = run_number
            if self.run_number is None and self.client is not None: self.run_number = self.client.run_number
            self.record = record
            self.description = description
            self.u1 = u1
            self.u2 = u2
            self.u3 = u3
            self.is_valid = self.well is not None and self.run_number is not None and self.record is not None and self.description is not None

        async def ExecuteCommand(self):
            if self.client_local.realtime_transferred:
                # Do something!
                pass

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<HH16s16s32sIII", self.fields_present, self.run_number, toUTF8Array(self.record),
                                     toUTF8Array(self.well), toUTF8Array(self.description), self.u1, self.u2, self.u3)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

    # 0xa006 - CMD_RT_STOP
    class RT_Stop(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xa006

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.RT_Stop(client=client)

        def __init__(self, client=None):
            super().__init__(name="CMD_RT_STOP", code=self.GetCode(), client=client, response_expected=False)
            self.is_valid = True

        async def ExecuteCommand(self):
            await self.client_local.server.StopAllRtMonitorFromClient(self.client)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header
        
    # 0xa007 - CMD_RT_STOP_ALL
    class RT_StopAll(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xa007

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            print(f"STOP ALL = {hex(header.param)}")
            return AdiCommands.RT_StopAll(client=client, param=header.param)

        def __init__(self, client=None, param=0x00):
            super().__init__(name="CMD_RT_STOP_ALL", code=self.GetCode(), client=client, response_expected=False)
            self.param = param
            self.is_valid = True

        async def ExecuteCommand(self):
            await self.client_local.server.StopAllRtMonitorFromClient(self.client)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

    # 0xa008 - CMD_RT_UNKNOWN_a008
    class RT_Unknown_a008(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xa008

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.RT_Unknown_a008(client=client)

        def __init__(self, client=None):
            super().__init__(name="CMD_RT_UNKNOWN_a008", code=self.GetCode(), client=client, response_expected=False)
            self.is_valid = True

        async def ExecuteCommand(self):
            pass

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

    # 0xa009 - CMD_CHECK_RT_SMT
    class CheckRealtimeSomething(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xa009

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.CheckRealtimeSomething(client=client)

        def __init__(self, client=None):
            super().__init__(name="CMD_CHECK_RT_SMT", code=self.GetCode(), client=client)
            self.is_valid = True

        async def GetLocalResult(self):
            return { "Success": True }

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            pass

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header
        
        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            return result

    # 0xa00e - CMD_RT_UNKNOWN_a00e
    class RT_Unknown_a00e(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xa00e

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.RT_Unknown_a00e(client=client)

        def __init__(self, client=None):
            super().__init__(name="CMD_RT_UNKNOWN_a00e", code=self.GetCode(), client=client, response_expected=False)
            self.is_valid = True

        async def ExecuteCommand(self):
            pass

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

    # 0xa010 - CMD_RT_CHECK_KEY
    class CheckRealtimeKey(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xa010

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            key_rt = header.param
            return AdiCommands.CheckRealtimeKey(client=client, key_rt=key_rt)

        def __init__(self, client=None, key_rt=0x00):
            super().__init__(name="CMD_RT_CHECK_KEY", code=self.GetCode(), client=client, response_expected=False)
            self.key_rt = key_rt
            # print(f"Params: key_rt={hex(self.key_rt)}")
            self.is_valid = True

        async def ExecuteCommand(self):
            if not self.client_local.realtime:
                self.client_local.realtime = self.client_local.realtime_id == self.key_rt

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.key_rt)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

    # 0xa011 - CMD_RT_DISCONNECT_KEY
    class DisconnectRtKey(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xa011

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.DisconnectRtKey(client=client, realtime_id=header.param)

        def __init__(self, client=None, realtime_id=0x00):
            super().__init__(name="CMD_RT_DISCONNECT_KEY", code=self.GetCode(), client=client)
            self.realtime_id = realtime_id
            self.is_valid = True

        async def ExecuteCommand(self):
            import random
            self.client_local.realtime_id = random.randint(0x100000, 0xff00ff00)
            self.client_local.realtime_transferred = False
            self.client_local.realtime = False

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=self.realtime_id)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

    # 0xa012 - CMD_RT_SUBSCRIBE_EVENT
    class RT_Subscribe_Events(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xa012

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            v1 = None
            v2 = None
            try:
                v1, v2 = struct.unpack_from("<II", bytes(data[16:24]))
            except:
                v1 = None
            return AdiCommands.RT_Subscribe_Events(client=client, v1=v1, v2=v2)

        def __init__(self, client=None, v1=0x00, v2=0x00, v3=0x00):
            super().__init__(name="CMD_RT_SUBSCRIBE_EVENT", code=self.GetCode(), client=client, response_expected=False)
            self.v1 = v1
            self.v2 = v2
            self.v3 = v3
            # print(f"Params: v1={self.v1}, v2={self.v2}, v3={self.v3}")

        def IsValid(self):
            return self.v1 is not None and self.v2 is not None

        async def ExecuteCommand(self):
            if self.v1 == 1 and self.v2 == 4:
                self.client_local.notify_well_change = True
            elif self.v1 == 2 and self.v2 == 3:
                self.client_local.notify_well_change = True
            elif self.v1 == 1 and self.v2 == 3:
                self.client_local.notify_run_change = True
            elif self.v1 == 4 and self.v2 == 4:
                self.client_local.notify_run_change = True
            elif self.v2 == 4:
                self.client_local.notify_well_change = False
            elif self.v2 == 3:
                self.client_local.notify_run_change = False

        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<III", self.v1, self.v2, self.v3)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

    # 0xa018 - CMD_RT_START
    class RT_Start(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xa018

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            fields_present = 0
            well = None
            run_number = None
            record = None
            description = None
            filter_activity = None
        
            try:
                ix = 16
                fields_present, run_number, record, well, description = struct.unpack_from("<HH16s16s32s", data, ix)
                ix += 68
                well = None if fields_present & adi.AdiEnums.QueryFilterModes.WELL.value == 0 else fromArrayToUTF8(well)
                run_number = None if fields_present & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value) == 0 else run_number
                record = None if fields_present & adi.AdiEnums.QueryFilterModes.RECORD.value == 0 else fromArrayToUTF8(record)
                description = None if fields_present & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value == 0 else fromArrayToUTF8(description)
                
                filter_activity, id, unknown2, unknown3, number_variables = struct.unpack_from("<IIHII", data, ix)
                ix += 18
                variables = []
                for _ in range(number_variables):
                    size, offset, storage, unit_option, name = struct.unpack_from("<HHHH16s", data, ix)
                    name = fromArrayToUTF8(name)
                    v = adi.AdiDefinitions.AdiVariable(size=size, offset=offset, name=name, format=adi.AdiEnums.StorageType(storage), unit_type=adi.AdiDefinitions.UnitType(unit_option=adi.AdiDefinitions.UnitOption(id=unit_option)))
                    variables.append({"Variable": v, "UnitOption": v.unit_type.unit_option})
                    ix += 24
            except Exception as ex:
                record = None
                
            return AdiCommands.RT_Start(client=client, id=id, fields_present=fields_present, well=well, run_number=run_number, record=record, description=description, filter_activity=filter_activity, u2=unknown2, u3=unknown3, variables=variables)

        def __init__(self, client=None, id=None, fields_present = 0x1d, well=None, run_number=None, record=None, description=None, filter_activity=None, u2=0, u3=0x10, variables=[]):
            super().__init__(name="CMD_RT_START", code=self.GetCode(), client=client, output_format=adi.AdiEnums.OutputFormat.BINARY_FULL)
            self.id = id
            self.fields_present = fields_present
            self.well = well
            if self.well is None and self.client is not None and fields_present & adi.AdiEnums.QueryFilterModes.WELL.value != 0: self.well = self.client.well
            self.run_number = run_number
            if self.run_number is None and self.client is not None and fields_present & adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value != 0: self.run_number = self.client.run_number
            self.record = record
            self.description = description
            self.filter_activity = filter_activity
            self.variables = variables
            self.is_valid = len(variables) > 0

        async def GetLocalResult(self):
            success = self.is_valid
            result = {}
            if self.is_valid:
                if self.client.realtime:
                    rt_monitor = adi.AdiDefinitions.AdiRTMonitor(self.client, id=self.id, well=self.well, run_number=self.run_number, record=self.record, description=self.description, variables_list=self.variables, filter_activity=self.filter_activity)
                    success = await self.client_local.server.AddRTMonitor(rt_monitor)
            
            result["Success"] = success
            return result

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            response = adi.AdiDefinitions.AdiResponse(param=0x00 if success else 0x01)
            return response
        
        def BuildCommandBinaryData(self):
            bytes_data = struct.pack(f"<HH16s16s32sIIHII", self.fields_present, 0 if self.run_number is None else self.run_number, toUTF8Array(self.record),
                                     toUTF8Array(self.well), toUTF8Array(self.description), 0 if self.filter_activity is None else self.filter_activity, self.id, 0x00, 0x10, len(self.variables))
            for variable in self.variables:
                v = variable["Variable"]
                bytes_data += struct.pack("<HHHH16s", v.size, v.offset, v.GetStorageType().value, variable["UnitOption"].id, toUTF8Array(v.name))
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=adi.AdiEnums.OutputFormat.BINARY_FULL, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            return result

    # 0xc022 - CMD_UNKNOWN_01
    class Unknown01(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xc022

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.Unknown01(client)

        def __init__(self, client=None):
            super().__init__(name="CMD_UNKNOWN_01", code=self.GetCode(), client=client)
            self.is_valid = True

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            return adi.AdiDefinitions.AdiResponse(param=0x01)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

    # 0xd001 - CMD_DEX_ADD
    class DEX_Add(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xd001

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            component_dex = None
            try:
                ix = 16
                # First bytes - signature 0x21FE
                signature = struct.unpack_from("<I", data, ix)[0]
                # Next 20 bytes: remote host
                component_host = struct.unpack_from("<20s", data, ix + 4)[0]
                component_host = fromArrayToUTF8(component_host)
                # Next 22 bytes: index, flags, start_time, start_depth_ft, period and end_time
                word_a, word_b, word_c, start_time, start_depth_ft, period_time, end_time = struct.unpack_from("<HHHIIII", data, ix + 24)
                start_time = None if start_time == 0 else AdiCommands.DateFromInsiteNumber(float(start_time))
                end_time = None if end_time == 0 else AdiCommands.DateFromInsiteNumber(float(end_time))

                # rt_and_stored, continuous     # 0x501 - 0101 0000 0001
                # stored_only, one_time_at_time # 0x401 - 0100 0000 0001
                # stored_only, one_time_now     # 0x301 - 0011 0000 0001
                # stored_only, periodic_at_time # 0x201 - 0010 0000 0001
                # stored_only, continuous       # 0x101 - 0001 0000 0001
                # rt_only, continuous           # 0x1   - 0000 0000 0001
                rt_stored_type = None
                if word_b & 0x500 == 0x500: rt_stored_type = adi.AdiEnums.DataTransferRtStoredType.RealtimeAndStored
                elif word_b & 0xf00 == 0: rt_stored_type = adi.AdiEnums.DataTransferRtStoredType.RealtimeOnly
                else: rt_stored_type = adi.AdiEnums.DataTransferRtStoredType.StoredOnly
                transfer_mode = None
                if word_b & 0xf00 == 0x400: transfer_mode = adi.AdiEnums.DataTransferMode.OneTimeAtTime
                elif word_b & 0xf00 == 0x300: transfer_mode = adi.AdiEnums.DataTransferMode.OneTimeNow
                elif word_b & 0xf00 == 0x200: transfer_mode = adi.AdiEnums.DataTransferMode.PeriodicAtTime
                else: transfer_mode = adi.AdiEnums.DataTransferMode.Continuous
                status_word = word_c & 0xff
                if status_word == 0x00: status_component = 'Disabled'
                elif status_word == 0x0a: status_component = 'Waiting to Resume When Connection is Made'
                elif status_word == 0x0c: status_component = 'Connecting'
                elif status_word == 0x01: status_component = 'Waiting to Send When Connection is Made and Receiver is Allowed to Receive'
                elif status_word == 0x03: status_component = 'Sending'
                elif status_word == 0x04: status_component = 'Sending'
                elif status_word == 0x07: status_component = f"Sending Complete at {end_time.strftime('%d-%m-%Y %H:%M:%S') if end_time else '-'}"
                else: status_component = f"Unknown Status {status_word}"

                # Next 128 bytes: component text
                component_text = struct.unpack_from("<128s", data, ix + 46)[0]
                component_text = fromArrayToUTF8(component_text)

                # Next 34 bytes: flags region
                dword_1_1, dword_1_2, dword_1_3, dword_1_4, dword_1_5, dword_1_6, dword_1_7, dword_1_8, word_d = struct.unpack_from("<IIIIIIIIH", data, ix + 174)
                # Values for word_d (filter modes):
                # 0000 0011 1111 = Everything in the Database
                # 0011 0011 1111 = All Data in Active Well
                # 0100 0011 1111 = All Data in Active Run
                # 0110 0011 1111 = All Data in Active Pass
                # 0010 0011 1111 = Only selected datasets, no records filter
                datasets_type = None
                if word_d & 0x300 == 0x300: datasets_type = adi.AdiEnums.DataTransferDatasetsType.ActiveWell
                elif word_d & 0x400 == 0x400: datasets_type = adi.AdiEnums.DataTransferDatasetsType.ActiveRun
                elif word_d & 0x600 == 0x600: datasets_type = adi.AdiEnums.DataTransferDatasetsType.ActivePass
                elif word_d & 0x200 == 0x200: datasets_type = adi.AdiEnums.DataTransferDatasetsType.SelectedDatasets
                else: datasets_type = adi.AdiEnums.DataTransferDatasetsType.FullDatabase
                data_transfer_enabled = (dword_1_1 & 0x01) == 0x01
                enable_config_change_notification = (dword_1_1 & 0x02) == 0x02
                enable_database_config_table_transfer = (dword_1_1 & 0x04) == 0x04
                restrict_excludes = (dword_1_1 & 0x08) == 0x08
                limit_bandwidth = (dword_1_1 & 0x10) == 0x10
                number_restricted_records = struct.unpack_from("<I", data, ix + 208)[0]
                ix += 212
                restricted_records = []
                for _ in range(number_restricted_records):
                    # Next 16 bytes: String containing record name
                    record_name = struct.unpack_from("<16s", data, ix)[0]
                    record_name = fromArrayToUTF8(record_name)
                    restricted_records.append(record_name)
                    ix += 16
                # Next 4 bytes: number of selected datasets (INT)
                number_selected_datasets = struct.unpack_from("<I", data, ix)[0]
                ix += 4
                selected_datasets:list[adi.AdiDefinitions.AdiDataSetPrimaryKey] = []
                for _ in range(number_selected_datasets):
                    fields_present, run_number, record, well, description = struct.unpack_from("<HH16s16s32s", data, ix)
                    well = None if adi.AdiEnums.QueryFilterModes.WELL not in fields_present else fromArrayToUTF8(well)
                    run_number = None if adi.AdiEnums.QueryFilterModes.RUN_NUMBER not in fields_present else run_number
                    record = None if adi.AdiEnums.QueryFilterModes.RECORD not in fields_present else fromArrayToUTF8(record)
                    description = None if adi.AdiEnums.QueryFilterModes.DESCRIPTION not in fields_present else fromArrayToUTF8(description)
                    selected_datasets.append(adi.AdiDefinitions.AdiDataSetPrimaryKey(well=well, run_number=run_number, record=record, description=description))
                    ix += 68
                # If the next 4 bytes are 0, then this is the extended version of the command, which
                # is only sent to remote clients with ID 5000973.
                # 4 bytes for the bandwidth limit and 653 bytes of unknown fields.
                zeros, limit_bandwidth_bps = struct.unpack_from("<II", data, ix)
                component_dex = adi.AdiDefinitions.AdiDataTransferComponent(
                    id=word_a,
                    remote_host=component_host, component_text=component_text, component_status=status_component,
                    rt_stored_type=rt_stored_type, transfer_mode=transfer_mode, datasets_type=datasets_type,
                    data_transfer_enabled=data_transfer_enabled,
                    enable_config_change_notification=enable_config_change_notification, enable_database_config_table_transfer=enable_database_config_table_transfer,
                    limit_bandwidth=limit_bandwidth,
                    limit_bandwidth_bps=limit_bandwidth_bps,
                    start_time=start_time, start_depth_ft=start_depth_ft, period_time=period_time, end_time=end_time,
                    restrict_excludes=restrict_excludes, restricted_records=restricted_records, datasets=selected_datasets)

            except Exception as ex:
                pass
            return AdiCommands.DEX_Add(client=client, component_dex=component_dex)

        def __init__(self, client=None, component_dex:adi.AdiDefinitions.AdiDataTransferComponent=None):
            super().__init__(name="CMD_DEX_ADD", code=self.GetCode(), client=client)
            self.is_valid = component_dex is not None
            self.component_dex = component_dex

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            return adi.AdiDefinitions.AdiResponse(param=0x00)

        def BuildCommandBinaryData(self):
            if not self.is_valid: return b""
            
            # Building in the same order that we extracted data in the method CreateCommandFromBinaryData
            bytes_data = b""
            # First bytes - signature 0x21FE
            bytes_data += struct.pack("<I", 0x21FE)
            # Next 20 bytes: remote host
            bytes_data += struct.pack("<20s", toUTF8Array(self.component_dex.remote_host))
            # Next 22 bytes: index, flags, start_time, start_depth_ft, period and end_time
            word_a = self.component_dex.id if self.component_dex.id is not None else 0xff
            word_b = 1
            if self.component_dex.rt_stored_type == adi.AdiEnums.DataTransferRtStoredType.RealtimeAndStored and \
                self.component_dex.transfer_mode == adi.AdiEnums.DataTransferMode.Continuous : word_b = 0x501
            elif self.component_dex.rt_stored_type == adi.AdiEnums.DataTransferRtStoredType.StoredOnly and \
                self.component_dex.transfer_mode == adi.AdiEnums.DataTransferMode.OneTimeAtTime : word_b = 0x401
            elif self.component_dex.rt_stored_type == adi.AdiEnums.DataTransferRtStoredType.StoredOnly and \
                self.component_dex.transfer_mode == adi.AdiEnums.DataTransferMode.OneTimeNow : word_b = 0x301
            elif self.component_dex.rt_stored_type == adi.AdiEnums.DataTransferRtStoredType.StoredOnly and \
                self.component_dex.transfer_mode == adi.AdiEnums.DataTransferMode.PeriodicAtTime : word_b = 0x201
            elif self.component_dex.rt_stored_type == adi.AdiEnums.DataTransferRtStoredType.StoredOnly and \
                self.component_dex.transfer_mode == adi.AdiEnums.DataTransferMode.Continuous : word_b = 0x101
            word_c = 0
            start_time = 0 if self.component_dex.start_time is None else int(AdiCommands.DateToInsiteNumber(self.component_dex.start_time))
            start_depth_ft = self.component_dex.start_depth_ft if self.component_dex.start_depth_ft is not None else 0
            period_time = self.component_dex.period_time if self.component_dex.period_time is not None else 0
            end_time = 0 if self.component_dex.end_time is None else int(AdiCommands.DateToInsiteNumber(self.component_dex.end_time))
            bytes_data += struct.pack("<HHHIIII", word_a, word_b, word_c, start_time, start_depth_ft, period_time, end_time)
            # Next 128 bytes: component text
            bytes_data += struct.pack("<128s", toUTF8Array(self.component_dex.component_text))
            # Next 34 bytes: flags region
            dword_1_1 = 0
            if self.component_dex.data_transfer_enabled: dword_1_1 |= 0x01
            if self.component_dex.enable_config_change_notification: dword_1_1 |= 0x02
            if self.component_dex.enable_database_config_table_transfer: dword_1_1 |= 0x04
            if self.component_dex.restrict_excludes: dword_1_1 |= 0x08
            if self.component_dex.limit_bandwidth: dword_1_1 |= 0x10
            word_d = 0
            if self.component_dex.datasets_type == adi.AdiEnums.DataTransferDatasetsType.ActiveWell: word_d |= 0x300
            elif self.component_dex.datasets_type == adi.AdiEnums.DataTransferDatasetsType.ActiveRun: word_d |= 0x400
            elif self.component_dex.datasets_type == adi.AdiEnums.DataTransferDatasetsType.ActivePass: word_d |= 0x600
            elif self.component_dex.datasets_type == adi.AdiEnums.DataTransferDatasetsType.SelectedDatasets: word_d |= 0x200
            dword_1_2 = 0
            dword_1_3 = 2959961344
            dword_1_4 = 13316
            dword_1_5 = 1140850688
            dword_1_6 = 1159741764
            dword_1_7 = 25600
            dword_1_8 = 25600
            bytes_data += struct.pack("<IIIIIIIIH", dword_1_1, dword_1_2, dword_1_3, dword_1_4, dword_1_5, dword_1_6, dword_1_7, dword_1_8, word_d)
            # Next 4 bytes: number of restricted records (INT)
            bytes_data += struct.pack("<I", len(self.component_dex.restricted_records))
            for record_name in self.component_dex.restricted_records:
                # Next 16 bytes: String containing record name
                bytes_data += struct.pack("<16s", toUTF8Array(record_name))
            # Next 4 bytes: number of selected datasets (INT)
            bytes_data += struct.pack("<I", len(self.component_dex.datasets))
            for dataset in self.component_dex.datasets:
                fields_present = 0
                if dataset.well is not None: fields_present |= adi.AdiEnums.QueryFilterModes.WELL
                if dataset.run_number is not None: fields_present |= adi.AdiEnums.QueryFilterModes.RUN_NUMBER
                if dataset.record is not None: fields_present |= adi.AdiEnums.QueryFilterModes.RECORD
                if dataset.description is not None: fields_present |= adi.AdiEnums.QueryFilterModes.DESCRIPTION
                bytes_data += struct.pack(f"<HH16s16s32s", fields_present, 0 if dataset.run_number is None else dataset.run_number, toUTF8Array(dataset.record), toUTF8Array(dataset.well), toUTF8Array(dataset.description))
            # Next 8 bytes: 0 and bandwidth limit in bps
            bytes_data += struct.pack("<II", 0, self.component_dex.limit_bandwidth_bps if self.component_dex.limit_bandwidth_bps is not None else 0)

            # Afterwards, there are 4 bytes for each selected dataset
            bytes_data += struct.pack(f"<{len(self.component_dex.datasets)}I", *[0 for _ in self.component_dex.datasets])

            # Pad the data 653 bytes of unknown fields, which are usually 0
            bytes_data += struct.pack("<653s", b"")

            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=0x01, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            return result

    # 0xd002 - CMD_DEX_REMOVE
    class DEX_Remove(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xd002

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.DEX_Remove(client)

        def __init__(self, client=None, hostname:str=None, component_id:int=None):
            super().__init__(name="CMD_DEX_REMOVE", code=self.GetCode(), client=client)
            self.is_valid = True
            self.hostname = hostname
            self.component_id = component_id

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            return adi.AdiDefinitions.AdiResponse(param=0x00)

        def BuildCommandBinaryData(self):
            hostname_bytes = toUTF8Array(self.hostname)
            hostname_length = len(hostname_bytes) + 1
            bytes_data = struct.pack(f"<H{hostname_length}sI", hostname_length, hostname_bytes, 1)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), format=adi.AdiEnums.OutputFormat.BINARY_SIMPLE, param=self.component_id, length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            return result

    # 0xd003 - CMD_DEX_LIST
    class DEX_List(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xd003

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.DEX_List(client)

        def __init__(self, client=None, full_details=False):
            super().__init__(name="CMD_DEX_LIST", code=self.GetCode(), client=client)
            self.is_valid = True
            self.full_details = full_details

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            return adi.AdiDefinitions.AdiResponse(param=0x00)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), param=0x01 if not self.full_details else 0x00)
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            result = {}
            success = True
            if response.param != 0x00:
                result["DataExchanges"] = []
                result["Success"] = False
                return result

            if self.full_details:
                # beautifyBytes(response.data)
                # pass
                # So far, the bytes below are identified:
                # 4 bytes - 34 21 00 00 - always present, unknown
                # First 4 bytes: package identifier, always 34 21 00 00
                response_identifier = struct.unpack_from("<I", response.data, 0x00)[0]
                # 4 bytes - 0x04, 0x08 ???
                # 4 bytes - 0x01 ??
                # 4 bytes - 0x02 ??
                # 20 bytes - 0x00 ???
                # 1 byte = 0x01 ??
                # 4 bytes = number of data exchanges (N)
                number_data_exchanges = struct.unpack_from("<I", response.data, 0x25)[0]
                ix = 0x29
                data_transfers:list[adi.AdiDefinitions.AdiDataTransfer] = []
                for _ in range(number_data_exchanges):
                    # First byte: 0x01 for TX and 0x00 for RX
                    direction = struct.unpack_from("<B", response.data, ix)[0]
                    # Second byte: status_code (3 = Connected, 5 = Connection Lost, attempting reconnect)
                    status_code = struct.unpack_from("<B", response.data, ix + 1)[0]
                    # Next 20 bytes: remote host
                    remote_host = struct.unpack_from("<20s", response.data, ix + 2)[0]
                    remote_host = fromArrayToUTF8(remote_host)
                    # Next 128 bytes: connection status
                    connection_status = struct.unpack_from("<128s", response.data, ix + 22)[0]
                    connection_status = fromArrayToUTF8(connection_status)
                    # Next 8 bytes: bytes transferred (double)
                    bytes_transferred = struct.unpack_from("<d", response.data, ix + 150)[0]
                    # Next 100 bytes: graphical bandwidth status (list of bytes)
                    bandwidth_status = struct.unpack_from("<100s", response.data, ix + 158)[0]
                    bandwidth_status = [b for b in bandwidth_status]
                    # Next 8 bytes: transfer rates
                    transfer_rate, avg_transfer_rate = struct.unpack_from("<ff", response.data, ix + 258)
                    # Next 4 bytes: queue_size
                    queue_size = struct.unpack_from("<I", response.data, ix + 266)[0]

                    data_transfer = adi.AdiDefinitions.AdiDataTransfer(remote_host=remote_host, direction=adi.AdiEnums.DataTransferDirection(direction))
                    data_transfer.bytes_transferred = bytes_transferred
                    data_transfer.status_code = status_code
                    data_transfer.connection_status = connection_status
                    data_transfer.str_connection_status = connection_status
                    data_transfer.bandwidth_status = bandwidth_status
                    data_transfer.average_transfer_rate = avg_transfer_rate
                    data_transfer.transfer_rate = transfer_rate
                    data_transfer.queue_size = queue_size

                    # Next 1 byte: number of components for this DEX
                    number_of_components = struct.unpack_from("<B", response.data, ix + 270)[0]
                    ix += 271
                    for _ in range(number_of_components):
                        # Next 4 bytes: component identifier, always FE 21 00 00
                        component_signature = struct.unpack_from("<I", response.data, ix)[0]
                        component_host = struct.unpack_from("<20s", response.data, ix + 4)[0]
                        component_host = fromArrayToUTF8(component_host)
                        # The below 6 bytes seems to come from the MODE on the DxGUI
                        word_a, word_b, word_c = struct.unpack_from("<HHH", response.data, ix + 24)
                        # Next 16 bytes: start time, start depth (ft), period time (s), end time
                        start_time, start_depth_ft, period_time, end_time = struct.unpack_from("<IIII", response.data, ix + 30)
                        start_time = None if start_time == 0 else AdiCommands.DateFromInsiteNumber(float(start_time))
                        end_time = None if end_time == 0 else AdiCommands.DateFromInsiteNumber(float(end_time))
                        # rt_and_stored, continuous     # 0x501 - 0101 0000 0001
                        # stored_only, one_time_at_time # 0x401 - 0100 0000 0001
                        # stored_only, one_time_now     # 0x301 - 0011 0000 0001
                        # stored_only, periodic_at_time # 0x201 - 0010 0000 0001
                        # stored_only, continuous       # 0x101 - 0001 0000 0001
                        # rt_only, continuous           # 0x1   - 0000 0000 0001
                        rt_stored_type = None
                        if word_b & 0x500 == 0x500: rt_stored_type = adi.AdiEnums.DataTransferRtStoredType.RealtimeAndStored
                        elif word_b & 0xf00 == 0: rt_stored_type = adi.AdiEnums.DataTransferRtStoredType.RealtimeOnly
                        else: rt_stored_type = adi.AdiEnums.DataTransferRtStoredType.StoredOnly
                        transfer_mode = None
                        if word_b & 0xf00 == 0x400: transfer_mode = adi.AdiEnums.DataTransferMode.OneTimeAtTime
                        elif word_b & 0xf00 == 0x300: transfer_mode = adi.AdiEnums.DataTransferMode.OneTimeNow
                        elif word_b & 0xf00 == 0x200: transfer_mode = adi.AdiEnums.DataTransferMode.PeriodicAtTime
                        else: transfer_mode = adi.AdiEnums.DataTransferMode.Continuous
                        status_word = word_c & 0xff
                        if status_word == 0x00: status_component = 'Disabled'
                        elif status_word == 0x0a: status_component = 'Waiting to Resume When Connection is Made'
                        elif status_word == 0x0c: status_component = 'Connecting'
                        elif status_word == 0x01: status_component = 'Waiting to Send When Connection is Made and Receiver is Allowed to Receive'
                        elif status_word == 0x03: status_component = 'Sending' if data_transfer.direction == adi.AdiEnums.DataTransferDirection.SendTo else 'Receiving'
                        elif status_word == 0x04: status_component = 'Sending' if data_transfer.direction == adi.AdiEnums.DataTransferDirection.SendTo else 'Receiving'
                        elif status_word == 0x07: status_component = f"Sending Complete at {end_time.strftime('%d-%m-%Y %H:%M:%S') if end_time else '-'}"
                        else: status_component = f"Unknown Status {status_word}"
                        # Next 128 bytes: text of component (type of data being transferred)
                        component_text = struct.unpack_from("<128s", response.data, ix + 46)[0]
                        component_text = fromArrayToUTF8(component_text)
                        # Next 34 bytes: unknown, being ignored for now
                        dword_1_1, dword_1_2, dword_1_3, dword_1_4, dword_1_5, dword_1_6, dword_1_7, dword_1_8, word_d = struct.unpack_from("<IIIIIIIIH", response.data, ix + 174)
                        # Values for word_d (filter modes):
                        # 0000 0011 1111 = Everything in the Database
                        # 0011 0011 1111 = All Data in Active Well
                        # 0100 0011 1111 = All Data in Active Run
                        # 0110 0011 1111 = All Data in Active Pass
                        # 0010 0011 1111 = Only selected datasets, no records filter
                        datasets_type = None
                        if word_d & 0x300 == 0x300: datasets_type = adi.AdiEnums.DataTransferDatasetsType.ActiveWell
                        elif word_d & 0x400 == 0x400: datasets_type = adi.AdiEnums.DataTransferDatasetsType.ActiveRun
                        elif word_d & 0x600 == 0x600: datasets_type = adi.AdiEnums.DataTransferDatasetsType.ActivePass
                        elif word_d & 0x200 == 0x200: datasets_type = adi.AdiEnums.DataTransferDatasetsType.SelectedDatasets
                        else: datasets_type = adi.AdiEnums.DataTransferDatasetsType.FullDatabase
                        data_transfer_enabled = (dword_1_1 & 0x01) == 0x01
                        enable_config_change_notification = (dword_1_1 & 0x02) == 0x02
                        enable_database_config_table_transfer = (dword_1_1 & 0x04) == 0x04
                        limit_bandwidth = (dword_1_1 & 0x10) == 0x10
                        # Next 4 bytes: Number of restricted records (INT)
                        number_restricted_records = struct.unpack_from("<I", response.data, ix + 208)[0]
                        ix += 212
                        restricted_records = []
                        for _ in range(number_restricted_records):
                            # Next 16 bytes: String containing record name
                            record_name = struct.unpack_from("<16s", response.data, ix)[0]
                            record_name = fromArrayToUTF8(record_name)
                            restricted_records.append(record_name)
                            ix += 16
                        # Next 4 bytes: number of selected datasets (INT)
                        number_selected_datasets = struct.unpack_from("<I", response.data, ix)[0]
                        ix += 4
                        selected_datasets:list[adi.AdiDefinitions.AdiDataSetPrimaryKey] = []
                        for _ in range(number_selected_datasets):
                            fields_present, run_number, record, well, description = struct.unpack_from("<HH16s16s32s", response.data, ix)
                            well = None if fields_present & adi.AdiEnums.QueryFilterModes.WELL.value == 0 else fromArrayToUTF8(well)
                            run_number = None if fields_present & (adi.AdiEnums.QueryFilterModes.RUN_NUMBER.value | adi.AdiEnums.QueryFilterModes.RUN_ALIAS.value) == 0 else run_number
                            record = None if fields_present & adi.AdiEnums.QueryFilterModes.RECORD.value == 0 else fromArrayToUTF8(record)
                            description = None if fields_present & adi.AdiEnums.QueryFilterModes.DESCRIPTION.value == 0 else fromArrayToUTF8(description)
                            selected_datasets.append(adi.AdiDefinitions.AdiDataSetPrimaryKey(well=well, run_number=run_number, record=record, description=description))
                            ix += 68
                        # If the next 4 bytes are 0, then this is the extended version of the command, which
                        # is only sent to remote clients with ID 5000973.
                        # 4 bytes for the bandwidth limit and 653 bytes of unknown fields.
                        zeros, limit_bandwidth_bps = struct.unpack_from("<II", response.data, ix)
                        if zeros == 0: ix += 661
                        else: limit_bandwidth_bps = None
                        while struct.unpack_from("<I", response.data, ix)[0] == 0x00: ix += 4   # This will definitely not work out! :D
                        component = adi.AdiDefinitions.AdiDataTransferComponent(
                            id=word_a,
                            remote_host=component_host, component_text=component_text, component_status=status_component,
                            rt_stored_type=rt_stored_type, transfer_mode=transfer_mode, datasets_type=datasets_type,
                            data_transfer_enabled=data_transfer_enabled,
                            enable_config_change_notification=enable_config_change_notification, enable_database_config_table_transfer=enable_database_config_table_transfer,
                            limit_bandwidth=limit_bandwidth,
                            limit_bandwidth_bps=limit_bandwidth_bps,
                            start_time=start_time, start_depth_ft=start_depth_ft, period_time=period_time, end_time=end_time,
                            restricted_records=restricted_records, datasets=selected_datasets)
                        data_transfer.components.append(component)
                    data_transfers.append(data_transfer)
                # Next 40 bytes: unknown, being ignored for now
                unknown_bytes_7 = struct.unpack_from("<40s", response.data, ix)[0]
                # Next 16 bytes: computer name
                computer_name = struct.unpack_from("<16s", response.data, ix + 40)[0]
                computer_name = fromArrayToUTF8(computer_name)
                # Next 36 bytes: unknown, being ignored for now
                unknown_bytes_8 = struct.unpack_from("<36s", response.data, ix + 56)[0]
                # Next 260 bytes: DEX files directory
                dex_directory = struct.unpack_from("<260s", response.data, ix + 92)[0]
                dex_directory = fromArrayToUTF8(dex_directory)
                # Next 8 bytes: unknown, being ignored for now
                unknown_bytes_9 = struct.unpack_from("<8s", response.data, ix + 352)[0]
                # Next 264 bytes: sound file path
                sound_file_path = struct.unpack_from("<264s", response.data, ix + 360)[0]
                sound_file_path = fromArrayToUTF8(sound_file_path)
                # Next 3 integers come as 0x0a, 0x01, 0x??, with the latter being number of hostnames
                _, _, flag_hostnames = struct.unpack_from("<III", response.data, ix + 624)
                ix += 636
                if flag_hostnames == 0x03:
                    # 2 x 20 bytes containing the hostnames
                    host_name_1 = struct.unpack_from("<20s", response.data, ix)[0]
                    host_name_1 = fromArrayToUTF8(host_name_1)
                    host_name_2 = struct.unpack_from("<20s", response.data, ix + 20)[0]
                    host_name_2 = fromArrayToUTF8(host_name_2)
                    result["HostNames"] = [host_name_1, host_name_2]
                    ix += 40
                else:
                    result["HostNames"] = []
                unknown_1, unknown_2, unknown_3 = struct.unpack_from("<III", response.data, ix)
                ix += 12
                for i in range(number_data_exchanges):
                    host_name, description_length = struct.unpack_from("<20sI", response.data, ix)
                    host_name = fromArrayToUTF8(host_name)
                    description = struct.unpack_from(f"<{description_length}s", response.data, ix + 24)[0]
                    description = fromArrayToUTF8(description)
                    data_transfers[i].description = description
                    ix += 24 + description_length
                result["DataExchanges"] = data_transfers
            else:
                # So far, the bytes below are identified:
                # 4 bytes = unknown
                # 4 bytes = unknown
                # 1 byte = 
                try:
                    result_data = []
                    number_lines = 1
                    ix = 0
                    [length_record] = struct.unpack_from("<I", response.data, ix)
                    ix += 4
                    [number_variables] = struct.unpack_from("<I", response.data, ix + length_record)
                    number_bytes_bit_test = math.ceil(number_variables / 8.0)
                    ix_bit_fields_test = ix + length_record + 4
                    for _ in range(number_lines):
                        if ix + length_record > response.length: raise Exception("Not enough bytes")
                        result_data.append(AdiCommands.ExtractDataFromBuffer(response.data, ix, length_record, ix_bit_fields_test, self.adi_dataset.variables, number_variables))
                        ix += length_record + 4 + number_bytes_bit_test
                    result["DataExchanges"] = result_data
                except Exception as ex:
                    success = False
                
            result["Success"] = success
            return result

    # 0xd00b - CMD_DEX_SET_DESCRIPTION
    class DEX_SetDescription(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xd00b

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.DEX_SetDescription(client)

        def __init__(self, client=None, hostname:str=None, description:str=None):
            super().__init__(name="CMD_DEX_SET_DESCRIPTION", code=self.GetCode(), client=client, response_expected=False)
            self.is_valid = hostname is not None and description is not None
            self.hostname = hostname
            self.description = description

        async def ExecuteCommand(self):
            # This command does not expect a response, but we can still execute some logic here if needed
            pass

        def BuildCommandBinaryData(self):
            hostname_bytes = toUTF8Array(self.hostname)
            hostname_length = len(hostname_bytes) + 1
            description_bytes = toUTF8Array(self.description)
            description_length = len(description_bytes) + 1
            bytes_data = struct.pack(f"<H{hostname_length}sH{description_length}s", hostname_length, hostname_bytes, description_length, description_bytes)
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode(), length=len(bytes_data))
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header + bytes_data

    # 0xc02d - CMD_PASSWORD_CHANGE
    class ChangeServerPassword(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xc02d

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            user = None
            old_password = None
            new_password = None
            if header.length == 32:
                user, old_password, new_password = struct.unpack_from("<32s16s16s", data, 16)
                user = fromArrayToUTF8(user)
                old_password = fromArrayToUTF8(old_password)
                new_password = fromArrayToUTF8(new_password)
                
            return AdiCommands.ChangeServerPassword(client=client, user=user, old_password=old_password, new_password=new_password)

        def __init__(self, client=None, user=None, old_password=None, new_password=None):
            super().__init__(name="CMD_PASSWORD_CHANGE", code=self.GetCode(), client=client)
            self.user = user
            self.old_password = old_password
            self.new_password = new_password

        async def GetLocalResult(self):
            raise Exception("Not implemented!")

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            success = result["Success"]
            return adi.AdiDefinitions.AdiResponse(param=0x00 if success else 0x01)

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00
            result = {"Success": success}
            return result

    # 0xe004 - CMD_QUERY_DATA_DICTIONARIES
    class QueryDataDictionaries(AdiCommand):
        @staticmethod
        def GetCode():
            return 0xe004

        @staticmethod
        def CreateCommandFromBinaryData(client, header, data):
            return AdiCommands.QueryDataDictionaries(client)

        def __init__(self, client=None):
            super().__init__(name="CMD_QUERY_DATA_DICTIONARIES", code=self.GetCode(), client=client)
            self.is_valid = True
           
        async def GetLocalResult(self):
            return {"Success": True, "DataDictionaries": ["MWD", "None", "Well Data"]}

        async def GetResponseBytes(self, result=None):
            if not self.is_valid: return adi.AdiDefinitions.AdiResponse(param=0x01)
            if result is None: result = await self.GetLocalResult()
            if not result["Success"]: return adi.AdiDefinitions.AdiResponse(param=0x01)
            
            data_dicts = result["DataDictionaries"]
            data = b''
            for dd in data_dicts:
                data += struct.pack(f"<16s", toUTF8Array(dd))
            return adi.AdiDefinitions.AdiResponse(value=len(data_dicts), data=data)

        def BuildCommandBinaryData(self):
            header = adi.AdiDefinitions.MessageHeader(command=self.GetCode())
            bytes_header = header.BuildCommandBinaryData()
            return bytes_header

        def TranslateResponseFromBytes(self, response):
            success = response.param == 0x00 and response.length == response.value * 16
            result = {"Success": success}
            if success:
                data_dictionaries = []
                for i in range(response.value):
                    [name] = struct.unpack_from(f"<16s", response.data, i * 16)
                    name = fromArrayToUTF8(name)
                    data_dictionaries.append(name)
                result["DataDictionaries"] = data_dictionaries
            return result

    # 0xa064 - CMD_RT_MESSAGE
    # 0xa066 - CMD_RT_EVENT

    # 0x900e - ADI_DATASET_WRITE_2
    # 0x901b - ADI_DATASET_CLEAR
