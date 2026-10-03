from __future__ import annotations
from collections.abc import Iterable
import datetime
import struct

import adi.AdiDefinitions
from adi.AdiEnums import *
import adi.AdiCommands
import adi.AdiEnums
from adi.EventEmitter import EventEmitter


class LogCurve:
    def __init__(self, curve_type:str=None, well=None, run_alias=None, record:str=None, description:str=None, desc_record:str=None, variable:str=None, curve_label:str=None, min_limit:float=None, max_limit:float=None, unit_option:adi.AdiDefinitions.UnitOption=None):
        self.curve_type = curve_type
        self.well = well
        self.run_alias = run_alias
        self.record = record
        self.description = description
        self.desc_record = desc_record
        self.variable = variable
        self.curve_label = curve_label
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.unit_option = unit_option

    def GetJsonObject(self):
        return {
            "CurveType": self.curve_type,
            "CurveLabel": self.curve_label,
            "MinLimit": self.min_limit,
            "MaxLimit": self.max_limit,
            "UnitOption": None if self.unit_option == None else { "ShortName": self.unit_option.short_name, "LongName": self.unit_option.long_name }
        }

    def __repr__(self):
        return f"{self.curve_label}"


class AdiDescriptorLine:
    def __init__(self, well=None, run_number=None, description=None, activity=None, record=None, start_depth=None, end_depth=None, start_time=None, end_time=None):
        self.well = well
        self.run_number = run_number
        self.description = description
        self.activity = activity
        self.record = record
        self.start_depth = start_depth
        self.end_depth = end_depth
        self.start_time = start_time
        self.end_time = end_time
    
    def __str__(self) -> str:
        s = ("" if self.well == None else self.well) + " | " + \
            ("" if self.run_alias == None else self.run_alias) + " | " + \
            ("" if self.description == None else self.description) + " | " + \
            ("" if self.start_depth == None else self.start_depth) + \
            ("" if self.start_time == None else self.start_time) + " | " + \
            ("" if self.end_depth == None else self.end_depth) + \
            ("" if self.end_time == None else self.end_time)

    def __eq__(self, value: object) -> bool:
        if value == None: return False
        if self.well != value.well: return False
        if self.run_number != value.run_number: return False
        if self.description != value.description: return False
        if self.activity != value.activity: return False
        if self.record != value.record: return False
        if self.start_depth != value.start_depth: return False
        if self.end_depth != value.end_depth: return False
        if self.start_time != value.start_time: return False
        if self.end_time != value.end_time: return False
        return True


class AdiDataSetPrimaryKey:
    def __init__(self, well=None, run=None, run_number=None, record=None, description=None, descriptor_record=None):
        self.well = well
        self.run = run
        self.run_number = run_number
        self.record = record
        self.description = description
        self.descriptor_record = descriptor_record
        
    def __repr__(self) -> str:
        return f"{self.well} | {self.run if self.run is not None else str(self.run_number)} | {self.record} | {self.description}"

    def __str__(self) -> str:
        return f"{self.well} | {self.run if self.run is not None else str(self.run_number)} | {self.record} | {self.description}"

    def GetJsonObject(self):
        return {
            "Well": self.well,
            "Run": self.run,
            "RunNumber": self.run_number,
            "Record": self.record,
            "Description": self.description
        }


class UnitOption:
    def __init__(self, id = None, short_name = None, long_name = None, psl_types = None, function_type = None, arg1 = None, arg2 = None):
        self.id = id
        self.short_name = short_name
        self.long_name = long_name
        self.psl_types = psl_types
        self.function_type = function_type  # 0=Equal Base, 1=Scale, 2=Offset, 3=Scale and Offset
        self.arg1 = arg1                    # Scale factor
        self.arg2 = arg2                    # Offset factor

    def __repr__(self) -> str:
        return f"{self.long_name} ({self.short_name})"

    def __eq__(self, value: object) -> bool:
        if value == None: return False
        return self.short_name == value.short_name and \
            self.long_name == value.long_name and \
            self.psl_types == value.psl_types


class MeasurementClass:
    def __init__(self, id:int=None, name:str=None):
        self.id = id
        self.name = name
        self.unit_options:list[UnitOption] = []
        self.unit_types:list[UnitType] = []

    def __repr__(self) -> str:
        return f"{self.name} (l={len(self.unit_options)})"


class UnitType:
    def __init__(self, id:int=None, name:str=None, unit_option:UnitOption=None, unit_options:list[UnitOption]=[], id_class:int=None, measurement_class:MeasurementClass=None):
        self.id = id
        self.name = name
        self.unit_options = unit_options
        self.unit_option = unit_option
        self.id_class = id_class
        self.measurement_class = measurement_class
    
    def __repr__(self) -> str:
        return f"n:{self.name}" + ("" if self.unit_option == None else f" | s:{self.unit_option.short_name} | l:{self.unit_option.long_name}")

    def __eq__(self, value: object) -> bool:
        if value == None: return False
        if self.unit_options != None and len(self.unit_options) != len(value.unit_options): return False
        if self.unit_option != value.unit_option: return False
        if self.id_class != value.id_class: return False
        return self.name == value.name


class OptionsList:
    def __init__(self, name=None, read_only=False, options=[]):
        self.name = name
        self.read_only = read_only
        self.options = list(options) if options is not None else []

    def __repr__(self) -> str:
        return f"{self.name} (L={len(self.options)})"

    def __eq__(self, value: object) -> bool:
        if value == None: return False
        if self.name != value.name or self.read_only != value.read_only or len(self.options) != len(value.options): return False
        for i in range(len(self.options)):
            if self.options[i] != value.options[i]: return False
        return True


class ConversionInfo:
    def __init__(self, function_type=0, arg1=0.0, arg2=0.0):
        self.function_type = function_type
        self.arg1 = arg1
        self.arg2 = arg2

    def __eq__(self, value: object) -> bool:
        if value == None: return False
        return self.function_type == value.function_type and \
            self.arg1 == value.arg1 and \
            self.arg2 == value.arg2


class AdiRecordType:
    def __init__(self, id=None, name=None, description=None):
        self.id = id
        self.name = name


class AdiRecord:
    def __init__(self, id=None, name=None, record_type_id=None, index_types=None, category=None, category_id=None, primary_keys=0, psl_types=0, attributes=0, number_variables=None):
        self.id = id
        self.name = name
        self.record_type_id = record_type_id
        self.index_types = index_types
        self.category = category
        self.category_id = category_id
        self.primary_keys = primary_keys
        self.psl_types = psl_types
        self.attributes = attributes
        self.number_variables = number_variables
        self.variables = []

    def GetIndexTypesString(self):
        str_return = "-" if self.index_types == 0 else ""
        if (self.index_types & adi.AdiEnums.IndexType.Sequential.value) != 0:
            str_return += "S"
        if (self.index_types & adi.AdiEnums.IndexType.Time.value) != 0:
            str_return += "T"
        if (self.index_types & adi.AdiEnums.IndexType.Depth.value) != 0:
            str_return += "D"
        if (self.index_types & adi.AdiEnums.IndexType.Activity.value) != 0:
            str_return += "A"
        return str_return

    def __repr__(self) -> str:
        return f"{self.name} (L={len(self.variables)})"

    def __eq__(self, value: object) -> bool:
        if value == None: return False
        return self.name == value.name and \
            self.record_type_id == value.record_type_id and \
            self.index_types == value.index_types and \
            self.category == value.category and \
            self.category_id == value.category_id and \
            self.primary_keys == value.primary_keys and \
            self.psl_types == value.psl_types and \
            self.attributes == value.attributes and \
            self.number_variables == value.number_variables and \
            len(self.variables) == len(value.variables)


class AdiRecordVariable:
    def __init__(self, variable=None, mnemonic=None, curve_label=None, mnemonic32=None, calculated=0, algorithm=None, ref_variable=None, coeff1=0.0, coeff2=0.0, coeff3=0.0):
        self.variable = variable
        self.mnemonic = mnemonic
        self.curve_label = curve_label
        self.mnemonic32 = mnemonic32
        self.calculated = calculated
        self.algorithm = algorithm
        self.ref_variable = ref_variable
        self.coeff1 = coeff1
        self.coeff2 = coeff2
        self.coeff3 = coeff3
        
    def __eq__(self, value: object) -> bool:
        if value == None: return False
        return self.mnemonic == value.mnemonic and \
            self.curve_label == value.curve_label and \
            self.mnemonic32 == value.mnemonic32 and \
            self.calculated == value.calculated and \
            self.algorithm == value.algorithm and \
            self.ref_variable == value.ref_variable and \
            self.coeff1 == value.coeff1 and \
            self.coeff2 == value.coeff2 and \
            self.coeff3 == value.coeff3


class AdiVariable:
    @staticmethod
    def GetVarTypeFormatPythonString(vt):
        if vt == VarType.ADI_VT_CHAR: return "b"
        elif vt == VarType.ADI_VT_UCHAR: return "B"
        elif vt == VarType.ADI_VT_SHORT: return "h"
        elif vt == VarType.ADI_VT_USHORT: return "H"
        elif vt == VarType.ADI_VT_INT: return "i"
        elif vt == VarType.ADI_VT_UINT: return "I"
        elif vt == VarType.ADI_VT_FLOAT: return "f"
        elif vt == VarType.ADI_VT_DOUBLE: return "d"
        else: raise Exception("Invalid variable type")

    @staticmethod
    def GetSizeByVarType(vt):
        if vt == VarType.ADI_VT_CHAR: return 1
        elif vt == VarType.ADI_VT_UCHAR: return 1
        elif vt == VarType.ADI_VT_SHORT: return 2
        elif vt == VarType.ADI_VT_USHORT: return 2
        elif vt == VarType.ADI_VT_INT: return 4
        elif vt == VarType.ADI_VT_UINT: return 4
        elif vt == VarType.ADI_VT_FLOAT: return 4
        elif vt == VarType.ADI_VT_DOUBLE: return 8
        else: raise Exception("Invalid variable type")
    
    def __init__(self, id=None, name=None, size=1, variables_types_id=0, unit_type_id=0, special=0, number_of_elements=1, number_of_decimals=0, mnemonic=None, curve_label=None, mnemonic32=None, unit_type=None, format=None, offset=0, record_variable_data=None):
        self.id = id
        self.name = name
        self.size = size
        self.var_type = variables_types_id
        self.unit_type = unit_type
        self.unit_type_id = unit_type_id
        self.special = special
        self.number_of_elements = number_of_elements
        self.number_of_decimals = number_of_decimals
        self.mnemonic = mnemonic
        self.curve_label = curve_label
        self.mnemonic32 = mnemonic32
        if format != None: self.SetStorageType(format)
        self.offset = offset
        self.record_variable_data:AdiRecordVariable = record_variable_data
        self.options_list:adi.AdiDefinitions.OptionsList = None

        self.vector_unit_type = None
        self.vector_unit_type_id = None
        self.vector_var_type = None
        self.vector_bin_start = None
        self.vector_bin_end = None

    def SetStorageType(self, storage_type):
        if isinstance(storage_type, int):
            storage_type = StorageType(storage_type)
        if storage_type == StorageType.NUMBER:
            if self.size % 8 == 0:
                self.var_type = VarType.ADI_VT_LONG
                self.number_of_elements = int(self.size / 8)
            elif self.size % 4 == 0:
                self.var_type = VarType.ADI_VT_INT
                self.number_of_elements = int(self.size / 4)
            elif self.size % 2 == 0:
                self.var_type = VarType.ADI_VT_SHORT
                self.number_of_elements = int(self.size / 2)
            else:
                self.var_type = VarType.ADI_VT_CHAR
                self.number_of_elements = self.size
        elif storage_type == StorageType.NUMBER_UNSIGNED:
            if self.size % 8 == 0:
                self.var_type = VarType.ADI_VT_ULONG
                self.number_of_elements = int(self.size / 8)
            elif self.size % 4 == 0:
                self.var_type = VarType.ADI_VT_UINT
                self.number_of_elements = int(self.size / 4)
            elif self.size % 2 == 0:
                self.var_type = VarType.ADI_VT_USHORT
                self.number_of_elements = int(self.size / 2)
            else:
                self.var_type = VarType.ADI_VT_UCHAR
                self.number_of_elements = self.size
        elif storage_type == StorageType.NUMBER_DECIMAL:
            if self.size % 8 == 0:
                self.var_type = VarType.ADI_VT_DOUBLE
                self.number_of_elements = int(self.size / 8)
            else:
                self.var_type = VarType.ADI_VT_FLOAT
                self.number_of_elements = int(self.size / 4)
        elif storage_type == StorageType.TEXT:
                self.var_type = VarType.ADI_VT_STRING
                self.number_of_elements = 1
        elif storage_type == StorageType.TEXT_LONG:
                self.var_type = VarType.ADI_VT_PCHAR
                self.number_of_elements = 1
        elif storage_type == StorageType.BINARY:
                self.var_type = VarType.ADI_VT_BINARY
                self.number_of_elements = 1
        elif storage_type == StorageType.BINARY_LONG:
                self.var_type = VarType.ADI_VT_PBYTE
                self.number_of_elements = 1
        elif storage_type == StorageType.I1_ARRAY:
            self.var_type = VarType.ADI_VT_CHAR
            self.number_of_elements = self.size
            self.size = 1
        elif storage_type == StorageType.I2_ARRAY:
            self.var_type = VarType.ADI_VT_SHORT
            self.number_of_elements = self.size
            self.size = 2
        elif storage_type == StorageType.I4_ARRAY:
            self.var_type = VarType.ADI_VT_INT
            self.number_of_elements = self.size
            self.size = 4
        elif storage_type == StorageType.U1_ARRAY:
            self.var_type = VarType.ADI_VT_UCHAR
            self.number_of_elements = self.size
            self.size = 1
        elif storage_type == StorageType.U2_ARRAY:
            self.var_type = VarType.ADI_VT_USHORT
            self.number_of_elements = self.size
            self.size = 2
        elif storage_type == StorageType.U4_ARRAY:
            self.var_type = VarType.ADI_VT_UINT
            self.number_of_elements = self.size
            self.size = 4
        elif storage_type == StorageType.F4_ARRAY:
            self.var_type = VarType.ADI_VT_FLOAT
            self.number_of_elements = self.size
            self.size = 4
        elif storage_type == StorageType.F8_ARRAY:
            self.var_type = VarType.ADI_VT_DOUBLE
            self.number_of_elements = self.size
            self.size = 8

    def GetStorageType(self) -> StorageType:
        # 1: Int
        # 2: Uns Int
        # 3: Float
        # 4: String
        # 5: PChar
        # 6: Binary
        # 7: PByte
        # 8: I1 Array
        # 9: I2 Array
        # 10: I4 Array
        # 11: U1 Array
        # 12: U2 Array
        # 13: U4 Array
        # 14: F4 Array
        # 15: F8 Array

        if self.number_of_elements > 1:
            numberOfBytes = self.size
            if self.var_type == VarType.ADI_VT_CHAR or self.var_type == VarType.ADI_VT_SHORT or self.var_type == VarType.ADI_VT_INT:
                if numberOfBytes >= 4:
                    return StorageType.I4_ARRAY   # I4
                elif numberOfBytes >= 2:
                    return StorageType.I2_ARRAY    # I2
                else:
                    return StorageType.I1_ARRAY    # I1

            if self.var_type == VarType.ADI_VT_UCHAR or self.var_type == VarType.ADI_VT_USHORT or self.var_type == VarType.ADI_VT_UINT:
                if numberOfBytes >= 4:
                    return StorageType.U4_ARRAY   # U4
                elif numberOfBytes >= 2:
                    return StorageType.U2_ARRAY   # U2
                else:
                    return StorageType.U1_ARRAY   # U1

            if self.var_type == VarType.ADI_VT_FLOAT or self.var_type == VarType.ADI_VT_DOUBLE:
                if numberOfBytes >= 8:
                    return StorageType.F8_ARRAY   # F8
                else:
                    return StorageType.F4_ARRAY   # F4

        if self.var_type == VarType.ADI_VT_CHAR: return StorageType.NUMBER
        elif self.var_type == VarType.ADI_VT_SHORT: return StorageType.NUMBER
        elif self.var_type == VarType.ADI_VT_INT: return StorageType.NUMBER
        elif self.var_type == VarType.ADI_VT_LONG: return StorageType.NUMBER
        elif self.var_type == VarType.ADI_VT_UCHAR: return StorageType.NUMBER_UNSIGNED
        elif self.var_type == VarType.ADI_VT_USHORT: return StorageType.NUMBER_UNSIGNED
        elif self.var_type == VarType.ADI_VT_UINT: return StorageType.NUMBER_UNSIGNED
        elif self.var_type == VarType.ADI_VT_ULONG: return StorageType.NUMBER_UNSIGNED
        elif self.var_type == VarType.ADI_VT_FLOAT: return StorageType.NUMBER_DECIMAL
        elif self.var_type == VarType.ADI_VT_DOUBLE: return StorageType.NUMBER_DECIMAL
        elif self.var_type == VarType.ADI_VT_STRING: return StorageType.TEXT
        elif self.var_type == VarType.ADI_VT_PCHAR: return StorageType.TEXT_LONG
        elif self.var_type == VarType.ADI_VT_BINARY: return StorageType.BINARY
        elif self.var_type == VarType.ADI_VT_PBYTE: return StorageType.BINARY_LONG

    def GetStorageTypeShort(self) -> str:
        st = self.GetStorageType()
        if st == StorageType.NUMBER:
            if self.size == 8: return "I8"
            if self.size == 4: return "I4"
            if self.size == 2: return "I2"
            return "I1"
        elif st == StorageType.NUMBER_UNSIGNED:
            if self.size == 8: return "U8"
            if self.size == 4: return "U4"
            if self.size == 2: return "U2"
            return "U1"
        elif st == StorageType.NUMBER_DECIMAL:
            if self.size == 4: return "F4"
            else: return "F8"
        elif st == StorageType.TEXT: return f"C{self.size}"
        elif st == StorageType.TEXT_LONG: return "P4"
        elif st == StorageType.BINARY: return f"B{self.size}"
        elif st == StorageType.BINARY_LONG: return "Q4"
        elif st == StorageType.I1_ARRAY: return f"I1[{self.size}]"
        elif st == StorageType.I2_ARRAY: return f"I2[{self.size}]"
        elif st == StorageType.I4_ARRAY: return f"I4[{self.size}]"
        elif st == StorageType.U1_ARRAY: return f"U1[{self.size}]"
        elif st == StorageType.U2_ARRAY: return f"U2[{self.size}]"
        elif st == StorageType.U4_ARRAY: return f"U4[{self.size}]"
        elif st == StorageType.F4_ARRAY: return f"F4[{self.size}]"
        elif st == StorageType.F8_ARRAY: return f"F8[{self.size}]"
        else: return "-"

    def RequiresBytePadding(self, number_of_bytes) -> bool:
        if self.size == number_of_bytes:
            st = self.GetStorageType()
            if st == StorageType.NUMBER: return True
            elif st == StorageType.NUMBER_UNSIGNED: return True
            elif st == StorageType.NUMBER_DECIMAL: return True
            elif st == StorageType.TEXT_LONG: return True
            elif st == StorageType.F4_ARRAY: return True
            elif st == StorageType.F8_ARRAY: return True
            elif st == StorageType.I4_ARRAY: return True
            elif st == StorageType.U4_ARRAY: return True
            elif st == StorageType.BINARY: return True
            elif st == StorageType.BINARY_LONG: return True
        return False

    def GetValueBytes(self, value):
        if value == None: return None
        
        storage_type = self.GetStorageType()
        if storage_type == StorageType.NUMBER:
            if self.size % 8 == 0:
                return struct.pack("<q", int(value))
            elif self.size % 4 == 0:
                return struct.pack("<i", int(value))
            elif self.size % 2 == 0:
                return struct.pack("<h", int(value))
            else:
                return struct.pack("<b", int(value))
        elif storage_type == StorageType.NUMBER_UNSIGNED:
            if self.size % 8 == 0:
                return struct.pack("<Q", int(value))
            elif self.size % 4 == 0:
                return struct.pack("<I", int(value))
            elif self.size % 2 == 0:
                return struct.pack("<H", int(value))
            else:
                return struct.pack("<B", int(value))
        elif storage_type == StorageType.NUMBER_DECIMAL:
            if self.size % 8 == 0:
                return struct.pack("<d", float(value))
            else:
                return struct.pack("<f", float(value))
        elif storage_type == StorageType.TEXT:
            return struct.pack(f"<{self.size}s", adi.AdiCommands.toUTF8Array(str(value)))
        elif storage_type == StorageType.TEXT_LONG:
            raise Exception("Not implemented")
        elif storage_type == StorageType.BINARY:
            return struct.pack(f"<{self.size}p", bytes(value))
        elif storage_type == StorageType.BINARY_LONG:
            raise Exception("Not implemented")
        elif storage_type == StorageType.I1_ARRAY:
            if len(value) != self.number_of_elements: raise Exception("Array length not match the expected size")
            data_bytes = b''
            for i in range(self.number_of_elements):
                data_bytes += struct.pack("<b", 0 if value[i] == None else int(value[i]))
            return data_bytes
        elif storage_type == StorageType.I2_ARRAY:
            if len(value) != self.number_of_elements: raise Exception("Array length not match the expected size")
            data_bytes = b''
            for i in range(self.number_of_elements):
                data_bytes += struct.pack("<h", 0 if value[i] == None else int(value[i]))
            return data_bytes
        elif storage_type == StorageType.I4_ARRAY:
            if len(value) != self.number_of_elements: raise Exception("Array length not match the expected size")
            data_bytes = b''
            for i in range(self.number_of_elements):
                data_bytes += struct.pack("<i", 0 if value[i] == None else int(value[i]))
            return data_bytes
        elif storage_type == StorageType.U1_ARRAY:
            if len(value) != self.number_of_elements: raise Exception("Array length not match the expected size")
            data_bytes = b''
            for i in range(self.number_of_elements):
                data_bytes += struct.pack("<B", 0 if value[i] == None else int(value[i]))
            return data_bytes
        elif storage_type == StorageType.U2_ARRAY:
            if len(value) != self.number_of_elements: raise Exception("Array length not match the expected size")
            data_bytes = b''
            for i in range(self.number_of_elements):
                data_bytes += struct.pack("<H", 0 if value[i] == None else int(value[i]))
            return data_bytes
        elif storage_type == StorageType.U4_ARRAY:
            if len(value) != self.number_of_elements: raise Exception("Array length not match the expected size")
            data_bytes = b''
            for i in range(self.number_of_elements):
                data_bytes += struct.pack("<I", 0 if value[i] == None else int(value[i]))
            return data_bytes
        elif storage_type == StorageType.F4_ARRAY:
            if len(value) != self.number_of_elements: raise Exception("Array length not match the expected size")
            data_bytes = b''
            for i in range(self.number_of_elements):
                data_bytes += struct.pack("<f", 0.0 if value[i] == None else float(value[i]))
            return data_bytes
        elif storage_type == StorageType.F8_ARRAY:
            if len(value) != self.number_of_elements: raise Exception("Array length not match the expected size")
            data_bytes = b''
            for i in range(self.number_of_elements):
                data_bytes += struct.pack("<d", 0.0 if value[i] == None else float(value[i]))
            return data_bytes

    def LoadVectorAttributes(self, v):
        self.vector_unit_type = v.vector_unit_type
        self.vector_unit_type_id = v.vector_unit_type_id
        self.vector_bin_start = v.vector_bin_start
        self.vector_bin_end = v.vector_bin_end
        self.vector_var_type = v.vector_var_type

    def GetVariableDataType(self):
        str_return = ""
        if self.var_type == VarType.ADI_VT_CHAR and self.size == 1:
            str_return = f"I1"
        elif self.var_type == VarType.ADI_VT_SHORT and self.size == 2:
            str_return = f"I2"
        elif self.var_type == VarType.ADI_VT_INT and self.size == 4:
            str_return = f"I4"
        elif self.var_type == VarType.ADI_VT_UCHAR and self.size == 1:
            str_return = f"U1"
        elif self.var_type == VarType.ADI_VT_USHORT and self.size == 2:
            str_return = f"U2"
        elif self.var_type == VarType.ADI_VT_UINT and self.size == 4:
            str_return = f"U4"
        elif self.var_type == VarType.ADI_VT_FLOAT and self.size == 4:
            str_return = f"F4"
        elif self.var_type == VarType.ADI_VT_DOUBLE and self.size == 8:
            str_return = f"F8"
        elif self.var_type == VarType.ADI_VT_PCHAR and self.size == 4:
            str_return = f"P4"
        elif self.var_type == VarType.ADI_VT_PBYTE and self.size == 4:
            str_return = f"Q4"
        elif self.var_type == VarType.ADI_VT_BINARY:
            str_return = f"B{self.size}"
        elif self.var_type == VarType.ADI_VT_CHAR:
            str_return = f"C{self.size}"
        if self.number_of_elements > 1:
            str_return += f"[{self.number_of_elements}]"
        return str_return

    def GetVariableDataTypeString(self):
        str_return = ""
        if self.var_type == VarType.ADI_VT_CHAR and self.size == 1:
            str_return = f"I1"
        elif self.var_type == VarType.ADI_VT_SHORT and self.size == 2:
            str_return = f"Short"
        elif self.var_type == VarType.ADI_VT_INT and self.size == 4:
            str_return = f"Int"
        elif self.var_type == VarType.ADI_VT_UCHAR and self.size == 1:
            str_return = f"U1"
        elif self.var_type == VarType.ADI_VT_USHORT and self.size == 2:
            str_return = f"UShort"
        elif self.var_type == VarType.ADI_VT_UINT and self.size == 4:
            str_return = f"UInt"
        elif self.var_type == VarType.ADI_VT_FLOAT and self.size == 4:
            str_return = f"Float" if self.number_of_elements == 1 else f"F4Array[{self.number_of_elements}]"
        elif self.var_type == VarType.ADI_VT_DOUBLE and self.size == 8:
            str_return = f"Double" if self.number_of_elements == 1 else f"F8Array[{self.number_of_elements}]"
        elif self.var_type == VarType.ADI_VT_PCHAR and self.size == 4:
            str_return = f"PCHAR"
        elif self.var_type == VarType.ADI_VT_PBYTE and self.size == 4:
            str_return = f"PBYTE"
        elif self.var_type == VarType.ADI_VT_BINARY:
            str_return = f"B{self.size}"
        elif self.var_type == VarType.ADI_VT_CHAR:
            str_return = f"C{self.size}"
        return str_return

    def GetSpecialsString(self):
        str_return = ""
        if (self.special & adi.AdiEnums.VariableSpecialHandlings.Calculable.value) != 0:
            str_return += "C"
        if (self.special & adi.AdiEnums.VariableSpecialHandlings.OptionList.value) != 0:
            str_return += "O"
        if (self.special & adi.AdiEnums.VariableSpecialHandlings.EnumList.value) != 0:
            str_return += "E"
        if (self.special & adi.AdiEnums.VariableSpecialHandlings.DateFormat.value) != 0:
            str_return += "T"
        if (self.special & adi.AdiEnums.VariableSpecialHandlings.DerivedDepth.value) != 0:
            str_return += "D"
        if (self.special & adi.AdiEnums.VariableSpecialHandlings.WaveForm.value) != 0:
            str_return += "W"
        if (self.special & adi.AdiEnums.VariableSpecialHandlings.VectorData.value) != 0:
            str_return += "V"
        if len(str_return) == 0:
            str_return = "-"
        return str_return

    def to_dict(self):
        return {
            "Name": self.name,
            "CurveLabel": self.curve_label if self.record_variable_data is None else self.record_variable_data.curve_label,
            "Mnemonic32": self.mnemonic32 if self.record_variable_data is None else self.record_variable_data.mnemonic32
        }

    def GetJsonObject(self):
        return {
            "Name": self.name,
            "DataType": self.GetVariableDataTypeString(),
            "Mnemonic": self.mnemonic if self.record_variable_data is None else self.record_variable_data.mnemonic,
            "CurveLabel": self.curve_label if self.record_variable_data is None else self.record_variable_data.curve_label,
            "Mnemonic32": self.mnemonic32 if self.record_variable_data is None else self.record_variable_data.mnemonic32,
            "Special": self.special,
            "NumberOfDecimals": self.number_of_decimals,
            "UnitType": None if self.unit_type == None else self.unit_type.name,
            "DefaultUnit": None if self.unit_type == None or self.unit_type.unit_option == None else { "ShortName": self.unit_type.unit_option.short_name, "LongName": self.unit_type.unit_option.long_name }
        }

    def __repr__(self) -> str:
        ut = "" if self.unit_type == None else self.unit_type.name
        return f"{self.name} (o={self.offset}, s={self.size}, {self.GetStorageTypeShort()}, {ut}, sp={self.special}, n_el={self.number_of_elements}, dec={self.number_of_decimals})"

    def __str__(self) -> str:
        ut = "" if self.unit_type == None else self.unit_type.name
        return f"{self.name} (o={self.offset}, s={self.size}, {self.GetStorageTypeShort()}, {ut}, sp={self.special}, n_el={self.number_of_elements}, dec={self.number_of_decimals})"

    def __eq__(self, value: object) -> bool:
        if value == None: return False
        if self.options_list != None:
            if len(self.options_list) != len(value.options_list): return False
            for i in range(len(self.options_list)):
                if self.options_list[i] != value.options_list[i]: return False
        return self.name == value.name and \
            self.size == value.size and \
            self.var_type == value.var_type and \
            self.unit_type == value.unit_type and \
            self.unit_type_id == value.unit_type_id and \
            self.special == value.special and \
            self.number_of_elements == value.number_of_elements and \
            self.number_of_decimals == value.number_of_decimals and \
            self.mnemonic == value.mnemonic and \
            self.curve_label == value.curve_label and \
            self.mnemonic32 == value.mnemonic32 and \
            self.offset == value.offset and \
            self.record_variable_data == value.record_variable_data


class AdiDatabaseDefinitions:
    def __init__(self, measurement_classes:Iterable[adi.AdiDefinitions.MeasurementClass], unit_types:Iterable[adi.AdiDefinitions.UnitType], variables:Iterable[adi.AdiDefinitions.AdiVariable], record_types:Iterable[adi.AdiDefinitions.AdiRecordType], records:Iterable[adi.AdiDefinitions.AdiRecord]):
        self.measurement_classes = measurement_classes
        self.unit_types = unit_types
        self.variables = variables
        self.records_types = record_types
        self.records = records


class CoercionType:
    def __init__(self, coercion_type=None, coercion_param=None, gap_distance=None):
        self.coercion_type:adi.AdiEnums.CoercionTypes = coercion_type
        self.coercion_param = coercion_param
        self.gap_distance = gap_distance

    def __repr__(self) -> str:
        return f"{self.coercion_type} (p={self.coercion_param}, d={self.gap_distance})"


class AdiVariableComplex(AdiVariable):
    def __init__(self, name=None, unit_option_short=None, coercion_type:CoercionType=None):
        self.variable = AdiVariable(name=name, unit_type=None if unit_option_short == None else UnitType(unit_option=UnitOption(short_name=unit_option_short)))
        self.coercion_type = coercion_type


class AdiDataSet:
    def __init__(self, well=None, run_number=None, run_alias=None, record=None, description=None, descriptor_record=None, variables:list=[]):
        self.well = well
        self.run_number = run_number
        self.run_alias = run_alias
        self.record = record
        self.description = description
        self.descriptor_record = descriptor_record
        self.variables = variables

    def __repr__(self):
        return f"{str(self.record)} \\ {str(self.description)} \\ {str(self.descriptor_record)}" if self.descriptor_record != None else f"{str(self.well)} \\ {str(self.run_alias)} \\ {str(self.record)} \\ {str(self.description)}"


class AdiDataSetReader:
    def __init__(self, client=None, id=None, table_number=None, well=None, run_number=None, run_alias=None, record=None, description=None, open_mode_value=None):
        from adi.AdiClientToRemote import AdiClientToRemote
        self.client:AdiClientToRemote = client
        self.id = id
        self.table_number = table_number
        self.well = well
        self.run_number = run_number
        self.run_alias = run_alias
        self.record = record
        self.description = description
        self.open_mode_value = open_mode_value
        self.variables = None
        self.is_open = False
        self.cursor_pos = None
        self.index_type = IndexType.Sequential

    async def Close(self):
        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetClose(self.client, adi_dataset=self))
        if response == None or not response["Success"]:
            raise Exception("Failed to close the dataset")
        self.is_open = False
        return True

    def IsSameDataSet(self, other:AdiDataSetReader) -> bool:
        self_run = self.run_alias if self.run_alias != None else f"{self.run_number:0>4}"
        other_run = other.run_alias if other.run_alias != None else f"{other.run_number:0>4}"
        return self.well == other.well and self_run == other_run and self.record == other.record and self.description == other.description

    async def GetNumberOfRecords(self):
        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetQueryNumberRecords(self.client, adi_dataset=self))
        if response == None or not response["Success"]: raise Exception("Failed to read number of records from dataset")
        return response["NumberOfRecords"]

    async def SetTDAFilter(self, activity: int):
        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetSetTDAFilter(self.client, adi_dataset=self, activity=activity))
        if response == None or not response["Success"]: raise Exception("Failed to set TDA filter")
        return True
    
    async def GetCurrentPosition(self) -> int:
        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetGetCurrentPosition(self.client, adi_dataset=self))
        if response == None or not response["Success"]: raise Exception("Failed to get current position of the dataset reader")
        return response["Position"]
    
    async def SetIndex(self, index_type: IndexType):
        await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetSetIndexType(self.client, adi_dataset=self, index_type=index_type))
        return True
    
    async def SetIndexPosition(self, mode_seek: SeekPositionMode, record_number=None, time_or_depth_in_ft=None):
        await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetSetIndexPosition(self.client, adi_dataset=self, mode_seek=mode_seek, record_number=record_number, value_search=time_or_depth_in_ft))
        return True
    
    async def SearchLineFromVariable(self, start_pos:int=None, end_pos:int=None, direction:adi.AdiEnums.SearchDirection=adi.AdiEnums.SearchDirection.Down, variable=None, start_value=None, end_value=None):
        var_name = variable if type(variable) == str else variable["name"]
        v = next((v for v in self.variables if v["Variable"].name == var_name), None)
        if v == None: raise Exception("Variable not existing in the DataSetReader")

        unit_option = None if type(variable) == str else variable["unit_option"]
        if unit_option == None: unit_option = v["UnitOption"]
        else:
            unit_option = next((uo for uo in v["Variable"].unit_type.unit_options if uo.short_name == unit_option or uo.long_name == unit_option))
            if unit_option != None and unit_option.id == None: unit_option.id = v["Variable"].unit_type.unit_options.index(unit_option)
        if unit_option == None: raise Exception("Unit Option for the requested variable not found")
        
        final_var = {"Variable": v["Variable"], "UnitOption": unit_option}

        result = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetLookup(self.client, adi_dataset=self, start_pos=start_pos, end_pos=end_pos, direction=direction.value, variable=final_var, start_value=start_value, end_value=end_value))
        return result
    
    async def ListBagDataFields(self):
        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetQueryNumberRecords(self.client, adi_dataset=self))
        if response == None or not response["Success"]: raise Exception("Failed to list bag data fields from the dataset")
        return response["Variables"]
    
    async def ReadBagData(self, variables_list=None):
        if len(self.variables) == 0:
            return [None] * len(variables_list)

        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetReadBagData(self.client, adi_dataset=self, variables=self.variables))
        if response == None or not response["Success"]: raise Exception("Failed to read bag data from the dataset")
        
        # Checking if client sent a list of variables. If yes, then we will
        # rebuild the answer based on those variables
        if variables_list != None:
            data_return = [None] * len(variables_list)
            for i_vl in range(len(variables_list)):
                for ix in range(len(self.variables)):
                    if variables_list[i_vl] == self.variables[ix]["Variable"].name:
                        data_return[i_vl] = response["Data"][ix]
                        break
            return data_return

        return response["Data"]
    
    async def WriteBagData(self, variables=[], values=[]):
        variables_list = await self.client.GetVariables(variables)
        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetWriteBagData(self.client, adi_dataset=self, variables=variables_list, values=values))
        if response == None or not response["Success"]: raise Exception("Failed to write bag data")
        return True
    
    async def ReadNext(self, number_lines)->list:
        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetReadNext(self.client, adi_dataset=self, number_lines=number_lines))
        if response == None or not response["Success"]: return [] # raise Exception("Failed to read lines from the dataset")
        return response["Data"]
    
    async def ReadPrevious(self):
        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetRead(self.client, adi_dataset=self, read_previous=True))
        if response == None or not response["Success"]: return [] # raise Exception("Failed to read lines from the dataset")
        return response["Data"]

    async def ReadWithLimit(self, number_lines=1, limit_value:float=None, block_read_option:adi.AdiEnums.BlockReadOption=None):
        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetReadWithLimit(self.client, adi_dataset=self, number_lines=number_lines, limit_value=limit_value, block_read_option=block_read_option))
        if response == None or not response["Success"]: return [] # raise Exception("Failed to read lines from the dataset")
        return response["Data"]

    async def WriteLines(self, write_mode_value, lines):
        if len(lines) == 1 and (write_mode_value & adi.AdiEnums.DataSetWriteModes.Insert) != 0:
            response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetWrite(self.client, write_mode_value=write_mode_value, adi_dataset=self, fields_to_write=lines[0]))
            # response will always be None for single line write
            response = {"Success": True}
        else:
            response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetWriteMultiple(self.client, write_mode_value=write_mode_value, adi_dataset=self, lines_to_write=lines))
        return response

    async def UpdateLinesByPosition(self, position, lines):
        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetUpdateByIndexPosition(self.client, adi_dataset=self, record_number=position, lines_to_write=lines))
        return response

    async def WriteVectorAttributes(self, var_name, unit_name, bin_start, bin_end, vector_type):
        variable = AdiVariable()
        variable.name = var_name
        variable.vector_unit_type = UnitType(name=unit_name)
        variable.vector_bin_start = bin_start
        variable.vector_bin_end = bin_end
        variable.vector_var_type = vector_type
        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetWriteVectorAttributes(self.client, adi_dataset=self, variables=[variable]))
        return response
    
    async def DeleteLinesByPosition(self, position, number_lines):
        await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetDeleteByIndexPosition(self.client, adi_dataset=self, record_number=position, number_records=number_lines))
        return True

    async def GetFilesList(self):
        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetGetFilesList(self.client, adi_dataset=self))
        if response == None or not response["Success"]: raise Exception("Failed to list files from the dataset")
        return response["Files"]

    async def ReadFile(self, filename)->bytes:
        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetReadFile(self.client, adi_dataset=self, entry_name=filename))
        if response == None or not response["Success"]: raise Exception("Failed to list files from the dataset")
        if response["FileSize"] == 0: return b''
        
        response = await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetReadFile(self.client, adi_dataset=self, entry_name=filename, number_bytes=response["FileSize"]))
        if response == None or not response["Success"]: raise Exception("Failed to list files from the dataset")
        
        return response["Data"]


class AdiDataSetReaderComplex(AdiDataSetReader):
    def __init__(self, client=None, id=None, keys=None, variables=None, coercion_types=None, iv=None, output_resolution=None, keys_opened:list[int]=None):
        self.client = client
        self.id = id
        self.keys:list[AdiDataSetPrimaryKey] = keys
        self.variables:list[AdiVariable] = variables
        self.coercion_types:list[CoercionType] = coercion_types
        self.iv:AdiVariable = iv
        self.output_resolution:float = output_resolution
        self.keys_opened = keys_opened

    async def SetPosition(self, position):
        await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetSetSmoothUnknown(self.client, self, position, 0, 0))

    async def SetPositionTime(self, time):
        time_search = time if type(time).__name__ != "datetime" else adi.AdiCommands.AdiCommands.DateToInsiteNumber(time) # time.timestamp() + time.utcoffset().total_seconds()
        await self.client.SendNewCommand(adi.AdiCommands.AdiCommands.DataSetSetSmoothUnknownTime3(self.client, self, time_search, 0x0a, 0))


class AdiComplexDataSet:
    def __init__(self, client=None, id=None, keys=None, variables=None, coercion_types=None, iv=None, output_resolution=None):
        self.client = client
        self.id = id
        self.keys:list[AdiDataSetPrimaryKey] = keys
        self.variables:list[AdiVariable] = variables
        self.coercion_types:list[CoercionType] = coercion_types
        self.iv:AdiVariable = iv
        self.output_resolution:float = output_resolution
        

class AdiDataSetFile:
    def __init__(self, folder:str, file_name:str, entry_name:str, file_size:int, data:bytes):
        self.folder = folder
        self.file_name = file_name
        self.entry_name = entry_name
        self.file_size = file_size
        self.data = data


class AdiDescriptorLines:
    def __init__(self, desc_lines:list[AdiDescriptorLine]=None, end_flag:bool=None, extra_bag_data:dict[str, any]=None):
        self.desc_lines = desc_lines
        self.end_flag = end_flag
        self.extra_bag_data = extra_bag_data

    def __eq__(self, value: object) -> bool:
        if value == None: return False
        if self.end_flag != value.end_flag:
            return False
        if self.desc_lines == None or value.desc_lines == None:
            if not (self.desc_lines == None and value.desc_lines == None):
                return False
        else:
            if len(self.desc_lines) != len(value.desc_lines): return False
            for i in range(len(self.desc_lines)):
                if self.desc_lines[i] != value.desc_lines[i]: return False
        if self.extra_bag_data == None or value.extra_bag_data == None:
            if not (self.extra_bag_data == None and value.extra_bag_data == None):
                return False
        else:
            if len(self.extra_bag_data) != len(value.extra_bag_data): return False
            for i in self.extra_bag_data.keys():
                if self.extra_bag_data[i] != value.extra_bag_data[i]: return False
        return True

    def GetJsonObject(self):
        json = {
            "DescriptorLines": None if self.desc_lines == None else [{"Run": x.run_number, "Description": x.description, "Activity": x.activity} for x in self.desc_lines]
        }
        return json


class AdiProcessClientIdentification():
    def __init__(self, id_client=0, exec_name=None, host_name=None, user_name=None):
        self.id_client = id_client
        self.exec_name = exec_name
        self.host_name = host_name
        self.user_name = user_name


class MessageHeader:
    def __init__(self, data=None, protocol=0x65, format=0, command=None, param=0, length=0):
        if data != None:
            self.protocol, self.format, self.command, self.param, self.length = struct.unpack_from("<hhIII", data)
        else:
            self.protocol = protocol
            self.format = format
            self.command = command
            self.param = param
            self.length = length

    def BuildCommandBinaryData(self):
        bytes_data = struct.pack("<hhIII", self.protocol, self.format, self.command, self.param, self.length)
        return bytes_data


class AdiResponse:
    @staticmethod
    def LoadFromBytes(data):
        protocol, format, param, value, length = struct.unpack("<hhIII", data[:16])
        if length == 0:
            return AdiResponse(protocol=protocol, format=format, param=param, value=value)
        else:
            return AdiResponse(protocol=protocol, format=format, param=param, value=value, length=length, data=bytes(data[16:]))
    
    def __init__(self, protocol=0x65, format=0x00, param=0x00, value=0x00, length=0x00, data=bytes()):
        self.protocol = protocol
        self.format = format
        self.param = param
        self.value = value
        self.data = data
        self.length = length
        
    def __repr__(self) -> str:
        if self.length == 0: return f"p={hex(self.param)} v={hex(self.value)}"
        else: return f"p={hex(self.param)} v={hex(self.value)} l={self.length}"

    def GetBytes(self):
        self.length = len(self.data)
        data = struct.pack("<hhIII", self.protocol, self.format, self.param, self.value, self.length)
        data += bytes(self.data)
        return data


class AdiRTMessage:
    @staticmethod
    def LoadFromResponse(resp:AdiResponse):
        if len(resp.data) >= 4:
            id = struct.unpack_from("<I", resp.data)[0]
            return AdiRTMessage(id=id, data=bytes(resp.data[4:]))
    
    def __init__(self, id=None, data=bytes()):
        self.id = id
        self.data = data
        self.length = len(data)
        
    def __repr__(self) -> str:
        if self.length == 0: return f"id={hex(self.id)}"
        else: return f"id={hex(self.id)} l={self.length}"


class AdiRTMonitor(EventEmitter):
    def __init__(self, adi_client=None, id=None, well=None, run_number=None, record=None, description=None, variables_list=[], filter_activity=None):
        super().__init__()
        self.adi_client = adi_client
        self.id = id
        self.well = well
        self.run_number = run_number
        self.record = record
        self.description = description
        self.variables_list = variables_list
        self.filter_activity = filter_activity

    async def MessageReceived(self, msg:AdiRTMessage):
        record, length = struct.unpack_from("<16sI", msg.data)
        record = adi.AdiCommands.fromArrayToUTF8(record)
        (number_values,) = struct.unpack_from("<I", msg.data, 20 + length)
        ix_bit_fields_test = 20 + length + 4
        data = adi.AdiCommands.AdiCommands.ExtractDataFromBuffer(msg.data, 20, length, ix_bit_fields_test, self.variables_list, number_values)
        await self.emit('message_received', msg, record, data)

    async def ReportRealtimeData(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, lines_to_send:list):
        # Applying filter for activity on the lines to send
        if self.filter_activity is not None and self.filter_activity != 0:
            var_td_activity = next((v for v in adi_dataset.variables if v["Variable"].name == "T/D Activity"), None)
            if var_td_activity is not None:
                index_var_td_activity = adi_dataset.variables.index(var_td_activity)
                lines_to_send = [line for line in lines_to_send if line[index_var_td_activity] == self.filter_activity]

        if len(lines_to_send) == 0:
            return

        # This will only happen when the client is AdiClientToLocal
        # Data will be sent via the writer_rt of it.
        # Preparing the bytes to send and calling the adi_client method to send the data to the local client
        data_bytes, _, bit_test_bytes = adi.AdiCommands.AdiCommands.BuildDataToSendFromLines(self.variables_list, adi_dataset.variables, lines_to_send)
        try:
            full_msg =  struct.pack("<I16sI", self.id, adi.AdiCommands.toUTF8Array(self.record), len(data_bytes)) + data_bytes
            full_msg += struct.pack("<I", len(lines_to_send[0])) # number of values for the record
            full_msg += bit_test_bytes
        except Exception as ex:
            raise Exception(f"Error building the message to send: {str(ex)}")
        await self.adi_client.SendRealtimeData(self, full_msg)

    async def Stop(self):
        await self.adi_client.StopRtMonitor(self)


class AdiDataTransferComponent:
    def __init__(self, id=None, remote_host:str=None, component_text:str=None, component_status:str=None, rt_stored_type:int=None, transfer_mode:int=None, datasets_type:int=None,
            data_transfer_enabled:bool=False, enable_config_change_notification:bool=False, enable_database_config_table_transfer:bool=False, limit_bandwidth:bool=False,
            limit_bandwidth_bps:int=32000, start_time:datetime.datetime=None, start_depth_ft:float=None, period_time:int=86400, end_time:datetime.datetime=None,
            restrict_excludes:bool=True, restricted_records:list[str]=[], datasets:list[AdiDataSetPrimaryKey]=[]):
        self.id = id
        self.remote_host = remote_host
        self.component_text = component_text
        self.component_status = component_status
        self.rt_stored_type = None if rt_stored_type is None else adi.AdiEnums.DataTransferRtStoredType(rt_stored_type)
        self.transfer_mode = None if transfer_mode is None else adi.AdiEnums.DataTransferMode(transfer_mode)
        self.datasets_type = None if datasets_type is None else adi.AdiEnums.DataTransferDatasetsType(datasets_type)
        self.data_transfer_enabled = data_transfer_enabled
        self.enable_config_change_notification = enable_config_change_notification
        self.enable_database_config_table_transfer = enable_database_config_table_transfer
        self.limit_bandwidth = limit_bandwidth
        self.limit_bandwidth_bps = limit_bandwidth_bps
        self.start_time = start_time
        self.start_depth_ft = start_depth_ft
        self.period_time = period_time
        self.end_time = end_time
        self.restrict_excludes = restrict_excludes
        self.restricted_records = restricted_records
        self.datasets = datasets

    def __str__(self) -> str:
        if self.datasets_type == adi.AdiEnums.DataTransferDatasetsType.ActiveWell: return "All Data in Active Well"
        if self.datasets_type == adi.AdiEnums.DataTransferDatasetsType.ActiveRun: return "All Data in Active Run"
        if self.datasets_type == adi.AdiEnums.DataTransferDatasetsType.FullDatabase: return "All Data in the Database"
        if self.datasets_type == adi.AdiEnums.DataTransferDatasetsType.SelectedDatasets:
            datasets = ['"{}"'.format(d) for d in self.datasets]
            return f"(Id={self.id}) Datasets: {datasets}"

    def __eq__(self, value):
        if value is None or not isinstance(value, AdiDataTransferComponent):
            return False
        return self.remote_host == value.remote_host and self.component_text == value.component_text and self.component_status == value.component_status and self.rt_stored_type == value.rt_stored_type and \
            self.transfer_mode == value.transfer_mode and self.datasets_type == value.datasets_type and self.data_transfer_enabled == value.data_transfer_enabled and self.enable_config_change_notification == value.enable_config_change_notification and \
            self.enable_database_config_table_transfer == value.enable_database_config_table_transfer and self.limit_bandwidth == value.limit_bandwidth and self.limit_bandwidth_bps == value.limit_bandwidth_bps and self.start_time == value.start_time and self.start_depth_ft == value.start_depth_ft and \
            self.period_time == value.period_time and self.end_time == value.end_time and self.restrict_excludes == value.restrict_excludes

    def GetJsonObject(self):
        return {
            "Id": self.id,
            "RemoteHost": self.remote_host,
            "ComponentText": self.component_text,
            "ComponentStatus": self.component_status,
            "StartTime": self.start_time.isoformat() if self.start_time != None else None,
            "StartDepthFt": self.start_depth_ft,
            "PeriodTime": self.period_time,
            "EndTime": self.end_time.isoformat() if self.end_time != None else None,
            "RestrictedRecords": self.restricted_records,
            "Datasets": [d.GetJsonObject() for d in self.datasets]
        }


class AdiDataTransfer(EventEmitter):
    def __init__(self, remote_host:str=None, description:str=None, adi_type:int=None, direction:int=None):
        super().__init__()
        self.remote_host = remote_host
        self.description = description
        self.adi_type = None if adi_type is None else adi.AdiEnums.DataTransferAdiType(adi_type)
        self.direction = None if direction is None else adi.AdiEnums.DataTransferDirection(direction)
        self.status_code = None
        self.connection_status = None # adi.AdiEnums.DataTransferConnectionStatus.Disabled
        self.transfer_status = adi.AdiEnums.DataTransferStatus.Stopped
        self.queue_size = 0
        self.bytes_transferred = 0
        self.transfer_rate = 0.0
        self.average_transfer_rate = 0.0
        self.last_error = None

        self.str_connection_status = ""
        self.bandwidth_status:list[int] = []
        self.components:list[AdiDataTransferComponent] = []

    def __str__(self) -> str:
        return "RemoteHost: " + self.remote_host + "\r\n" + \
            "Description: " + self.description + "\r\n" + \
            "Components: " + "\r\n".join([f"    {str(c)}" for c in self.components])

    def __eq__(self, value):
        if value is None or not isinstance(value, AdiDataTransfer):
            return False
        return self.remote_host == value.remote_host and self.description == value.description and \
            self.adi_type == value.adi_type and self.direction == value.direction and \
            self.connection_status == value.connection_status and self.transfer_status == value.transfer_status and \
            self.queue_size == value.queue_size and self.bytes_transferred == value.bytes_transferred and \
            self.transfer_rate == value.transfer_rate and self.average_transfer_rate == value.average_transfer_rate and \
            self.last_error == value.last_error and self.bandwidth_status == value.bandwidth_status and \
            len(self.components) == len(value.components) and all([self.components[i] == value.components[i] for i in range(len(self.components))])

    def GetJsonObject(self):
        return {
            "RemoteHost": self.remote_host,
            "Description": self.description,
            # "AdiType": self.adi_type.name,
            "Direction": self.direction.name,
            # "RtStoredType": self.rt_stored_type.name,
            # "DatasetsType": self.datasets_type.name,
            # "Enabled": self.enabled,
            "ConnectionStatus": self.str_connection_status,
            "ConnectionStatusCode": self.connection_status,
            # "TransferStatus": self.transfer_status.name,
            "QueueSize": self.queue_size,
            "BytesTransferred": self.bytes_transferred,
            "AverageTransferRate": self.average_transfer_rate,
            "TransferRate": self.transfer_rate,
            # "LastError": str(self.last_error),
            "BandwidthStatus": self.bandwidth_status,
            "Components": [c.GetJsonObject() for c in self.components]
        }    
