from __future__ import annotations
from asyncio import Server, StreamReader, StreamWriter, AbstractEventLoop
import asyncio
from collections.abc import Iterable
import csv
import enum
from itertools import islice
import json
import math
import os
import re
import struct
import sys
import mysql.connector.aio
import mysql.connector.abstracts
from typing import TYPE_CHECKING

from adi import AdiServerIris
from adi.EventEmitter import EventEmitter
import adi.AdiDefinitions
import adi.AdiEnums
import rigs_control.rigs

if TYPE_CHECKING:
    import adi.AdiCommands

DB_USER = "thales"
DB_PASS = "thaleS01"
DB_HOST = "localhost"   # Use None for unix socket connection
DB_SOCKET = "/var/run/mysqld/mysqld.sock"  # Used if DB_HOST is None

class AdiServerEventType(enum.Enum):
    WELL_CHANGED = 1
    RUN_CHANGED = 2
    UNITSET_CHANGED = 3

class CurrentData:
    def __init__(self, well=None, run=None, activity=None, bit_depth=None, hole_depth=None, drill_model_desc=None, lithology_desc=None, survey_desc=None, unitset=None):
        self.well = well
        self.run = run
        self.activity = activity
        self.bit_depth = bit_depth
        self.hole_depth = hole_depth
        self.drill_model_desc = drill_model_desc
        self.lithology_desc = lithology_desc
        self.survey_desc = survey_desc
        self.unitset = unitset

    def __str__(self):
        return f"Well: {self.well}\nRun: {self.run}\nActivity: {self.activity}\nBit Depth: {self.bit_depth}\nHole Depth: {self.hole_depth}\nUnitset: {self.unitset}"

class AdiOpenDataSet:
    def __init__(self, identified_client:adi.AdiDefinitions.AdiProcessClientIdentification, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, mode:adi.AdiEnums.RecordOpenModes):
        self.identified_client = identified_client
        self.adi_dataset = adi_dataset
        self.mode = mode

class AdiServerEvent:
    def __init__(self, event_type:AdiServerEventType, adi_server:AdiServer):
        self.event_type = event_type
        self.adi_server = adi_server

class AdiServer(EventEmitter):
    @staticmethod
    async def __GetOneTimeDatabaseConnection(db_name:str)->mysql.connector.abstracts.MySQLConnectionAbstract:
        ### Only used for direct connections which does not go through pool
        try:
            if DB_HOST == None:
                conn = await mysql.connector.aio.connect(user=DB_USER, unix_socket=DB_SOCKET, database=db_name)
            else:
                conn = await mysql.connector.aio.connect(user=DB_USER, password=DB_PASS, host=DB_HOST, database=db_name)
            return conn
        except mysql.connector.aio.Error as e:
            print(f"Error connecting to database: {e}")
            return None

    @staticmethod
    def __GetDefaultRecordType()->Iterable[adi.AdiDefinitions.AdiRecordType]:
        record_types:dict[int, adi.AdiDefinitions.AdiRecordType] = {}
        record_types[0] = adi.AdiDefinitions.AdiRecordType(id=0, name="ADI_REC_UNKNOWN")
        record_types[1] = adi.AdiDefinitions.AdiRecordType(id=1, name="ADI_REC_NONE")
        record_types[2] = adi.AdiDefinitions.AdiRecordType(id=2, name="ADI_REC_TIME")
        record_types[3] = adi.AdiDefinitions.AdiRecordType(id=3, name="ADI_REC_DEPTH")
        record_types[4] = adi.AdiDefinitions.AdiRecordType(id=4, name="ADI_REC_TDA")
        record_types[5] = adi.AdiDefinitions.AdiRecordType(id=5, name="ADI_REC_LITH")
        record_types[6] = adi.AdiDefinitions.AdiRecordType(id=6, name="ADI_REC_TD")
        record_types[7] = adi.AdiDefinitions.AdiRecordType(id=7, name="ADI_REC_BHA_COMPONENT")
        record_types[8] = adi.AdiDefinitions.AdiRecordType(id=8, name="ADI_REC_BHA_COMPOSITE")
        record_types[9] = adi.AdiDefinitions.AdiRecordType(id=9, name="ADI_REC_DESCRIPTOR")
        record_types[10] = adi.AdiDefinitions.AdiRecordType(id=10, name="ADI_REC_PUMP")
        record_types[11] = adi.AdiDefinitions.AdiRecordType(id=11, name="ADI_REC_TIME_DEPTH")
        record_types[12] = adi.AdiDefinitions.AdiRecordType(id=12, name="ADI_REC_NO_INDEX")
        record_types[13] = adi.AdiDefinitions.AdiRecordType(id=13, name="ADI_REC_REMARKS")
        record_types[14] = adi.AdiDefinitions.AdiRecordType(id=14, name="ADI_REC_REALTIME")
        record_types[15] = adi.AdiDefinitions.AdiRecordType(id=15, name="ADI_REC_GEOMETRY")
        record_types[16] = adi.AdiDefinitions.AdiRecordType(id=16, name="ADI_REC_SURVEY")
        record_types[17] = adi.AdiDefinitions.AdiRecordType(id=17, name="ADI_REC_BAG")
        record_types[18] = adi.AdiDefinitions.AdiRecordType(id=18, name="ADI_REC_FAILURE")
        record_types[20] = adi.AdiDefinitions.AdiRecordType(id=20, name="ADI_REC_TOOL_PARAMS")
        record_types[21] = adi.AdiDefinitions.AdiRecordType(id=21, name="ADI_REC_ENVIRONMENTAL")
        record_types[22] = adi.AdiDefinitions.AdiRecordType(id=22, name="ADI_REC_WELL_RUN_INFO")
        record_types[23] = adi.AdiDefinitions.AdiRecordType(id=23, name="ADI_REC_LITH_PALETTE")
        record_types[24] = adi.AdiDefinitions.AdiRecordType(id=24, name="ADI_REC_DX_FILE")
        record_types[25] = adi.AdiDefinitions.AdiRecordType(id=25, name="ADI_REC_REPORT_EDITOR")
        record_types[26] = adi.AdiDefinitions.AdiRecordType(id=26, name="ADI_REC_AWC_EVENT_LOG")
        record_types[27] = adi.AdiDefinitions.AdiRecordType(id=27, name="ADI_REC_ATTACHMENT_MAN")
        record_types[28] = adi.AdiDefinitions.AdiRecordType(id=28, name="ADI_REC_WL_PARAMETER_EDITOR")
        record_types[30] = adi.AdiDefinitions.AdiRecordType(id=30, name="ADI_REC_MUD_EDITOR")
        record_types[31] = adi.AdiDefinitions.AdiRecordType(id=31, name="ADI_REC_RLE_COMPRESSION")
        record_types[32] = adi.AdiDefinitions.AdiRecordType(id=32, name="ADI_REC_BHA_ANALYSIS")
        record_types[33] = adi.AdiDefinitions.AdiRecordType(id=33, name="ADI_REC_SPERRY_IMAGE")
        record_types[34] = adi.AdiDefinitions.AdiRecordType(id=34, name="ADI_REC_TORQUE_DRAG")
        record_types[35] = adi.AdiDefinitions.AdiRecordType(id=35, name="ADI_REC_XMLREPORTVIEWER")
        record_types[36] = adi.AdiDefinitions.AdiRecordType(id=36, name="ADI_REC_PDT")
        record_types[37] = adi.AdiDefinitions.AdiRecordType(id=37, name="ADI_REC_IREMARKS")
        record_types[38] = adi.AdiDefinitions.AdiRecordType(id=38, name="ADI_REC_EVENT_LOG")
        record_types[39] = adi.AdiDefinitions.AdiRecordType(id=39, name="ADI_REC_VIBRATION_ANALYSIS")
        record_types[40] = adi.AdiDefinitions.AdiRecordType(id=40, name="ADI_REC_DXSERVERINFOVIEWER")
        record_types[41] = adi.AdiDefinitions.AdiRecordType(id=41, name="ADI_REC_GAS_SUMMARY")
        record_types[42] = adi.AdiDefinitions.AdiRecordType(id=42, name="ADI_REC_TRIP_SHEET")
        return record_types

    @staticmethod
    async def __ReplaceDatabaseTableDefinitions(my_cursor:mysql.connector.abstracts.MySQLCursorAbstract, db_name:str, database_definitions:adi.AdiDefinitions.AdiDatabaseDefinitions):
        # Zero-copy iterables (no sort)
        measurement_classes = database_definitions.measurement_classes.values() if database_definitions.measurement_classes else ()
        unit_types          = database_definitions.unit_types.values()          if database_definitions.unit_types          else ()
        variables_iter      = database_definitions.variables.values()           if database_definitions.variables           else ()
        records_types       = database_definitions.records_types.values()       if database_definitions.records_types       else ()
        records             = database_definitions.records.values()             if database_definitions.records             else ()

        if not records_types:
            records_types = AdiServer.__GetDefaultRecordType()  # make sure this returns an Iterable
            # Checking if any record_id from the listing is not in the default set.
            # If so, we need to add it to the DB too as "Custom" name.
            custom_records = {rec.record_type_id for rec in (records or ()) if rec.record_type_id not in records_types}
            for cr in custom_records:
                records_types[cr] = adi.AdiDefinitions.AdiRecordType(id=cr, name=f"Custom_{cr}")
            records_types = records_types.values()  # re-assign to the values view

        async def execmany_chunked(cursor, sql, rows_iter, chunk=5000):
            it = iter(rows_iter)
            while True:
                batch = list(islice(it, chunk))
                if not batch:
                    break
                await cursor.executemany(sql, batch)

        sql_mc  = f"INSERT INTO `{db_name}`.`measurement_classes` (id, name) VALUES (%s, %s)"
        sql_mcu = f"""INSERT INTO `{db_name}`.`mc_units`
        (id, measurement_classes_id, name_long, name_short, function_type, arg1, arg2, psl_types)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""
        sql_upd = f"UPDATE `{db_name}`.`measurement_classes` SET mc_default_id=%s WHERE id=%s"

        # Build rows without mutating your domain objects (optional, cleaner)
        mc_rows   = []
        mcu_rows  = []
        upd_rows  = []

        mc_id  = 1
        mcu_id = 1

        for mc in (measurement_classes or ()):
            mc_rows.append((mc_id, mc.name))

            default_mcu_id = None
            if mc.unit_options:
                # assume "first option in this class" is the default
                default_mcu_id = mcu_id

                for uo in mc.unit_options:
                    mcu_rows.append((
                        mcu_id,
                        mc_id,
                        uo.long_name,
                        uo.short_name,
                        0 if uo.function_type is None else uo.function_type,
                        0.0 if uo.arg1 is None else uo.arg1,
                        0.0 if uo.arg2 is None else uo.arg2,
                        0 if uo.psl_types is None else uo.psl_types,
                    ))
                    mcu_id += 1

            if default_mcu_id is not None:
                upd_rows.append((default_mcu_id, mc_id))

            mc_id += 1

        # insert in chunks (works for sync or async drivers)
        await execmany_chunked(my_cursor, sql_mc,  mc_rows,  1000)
        await execmany_chunked(my_cursor, sql_mcu, mcu_rows, 5000)
        if upd_rows:
            await execmany_chunked(my_cursor, sql_upd, upd_rows, 1000)

        # ---- Unit Types ----
        sql_ut = f"INSERT INTO `{db_name}`.`unit_types` (id, measurement_classes_id, name) VALUES (%s, %s, %s)"
        ut_rows = []
        ut_id = 1
        mc_name_to_id = dict((name, mc_id) for mc_id, name in mc_rows)  # id,name from mc_rows
        for ut in (unit_types or ()):
            ut_rows.append((ut_id, mc_name_to_id[ut.measurement_class.name], ut.name))
            ut.id = ut_id  # assign the ID back to the domain object for later FK use
            ut_id += 1

        await execmany_chunked(my_cursor, sql_ut, ut_rows, 5000)

        sql_vars = f"""INSERT INTO `{db_name}`.`variables`
            (id, name, mnemonic, curve_label, unit_types_id, variables_types_id, special, options_lists_id,
            size, number_of_elements, number_of_decimals, mnemonic32)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""

        sql_optlist = f"""INSERT INTO `{db_name}`.`options_lists`
            (id, name, read_only) VALUES (%s,%s,%s)"""

        sql_opt = f"""INSERT INTO `{db_name}`.`options_lists_options`
            (options_lists_id, name) VALUES (%s,%s)"""

        # Build rows without reassigning variable IDs
        opt_id_auto = 1
        var_id_auto = 1
        optlists_rows = []
        optitems_rows = []
        vars_rows = []

        for v in variables_iter:
            v.id = var_id_auto
            var_id_auto += 1
            # FK to options list (one per variable if present)
            opt_fk = None
            if v.options_list is not None:
                opt_fk = opt_id_auto
                optlists_rows.append((opt_fk, v.options_list.name, 1 if getattr(v.options_list, "read_only", False) else 0))
                # options text rows
                optitems_rows.extend((opt_fk, s) for s in v.options_list.options)
                opt_id_auto += 1

            # normalize nullable fields
            mnemonic32 = v.mnemonic32 or ""
            num_elems  = v.number_of_elements if v.number_of_elements is not None else 0
            special    = v.special if v.special is not None else 0

            # IMPORTANT: keep `v.id` as parsed; do not overwrite
            # Ensure unit_type.id and var_type are integers (FKs)
            vars_rows.append((
                v.id,
                v.name,
                v.mnemonic,
                v.curve_label,
                v.unit_type.id,   # make sure unit types were inserted first and have ids
                v.var_type,       # ensure this is the integer FK your schema expects
                special,
                opt_fk,
                v.size,
                num_elems,
                v.number_of_decimals,
                mnemonic32
            ))

        await execmany_chunked(my_cursor, sql_optlist,  optlists_rows, 5000)
        await execmany_chunked(my_cursor, sql_opt,      optitems_rows, 10000)
        await execmany_chunked(my_cursor, sql_vars,     vars_rows, 5000)

        # records_types
        sql_rt = f"INSERT INTO `{db_name}`.`records_types` (id, name) VALUES (%s, %s)"
        rt_rows = ((rt.id, rt.name) for rt in (records_types or ()))
        await execmany_chunked(my_cursor, sql_rt, rt_rows, chunk=1000)

        # records
        sql_rec = f"""INSERT INTO `{db_name}`.`records`
        (id, name, records_types_id, index_types, records_categories_id, primary_keys, psl_types, attributes)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""

        # records_variables
        sql_rv = f"""INSERT INTO `{db_name}`.`records_variables`
        (records_id, variables_id, calculated, mnemonic, curve_label, mnemonic32,
        algorithms_calculation_id, reference_variable_id, coeff1, coeff2, coeff3)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""

        rec_rows_batch = []
        rv_rows_batch  = []
        rec_id = 1

        for rec in (records or ()):
            # build record row
            rec_rows_batch.append((
                rec_id,
                rec.name,
                rec.record_type_id,
                rec.index_types,
                rec.category_id,
                rec.primary_keys,
                rec.psl_types,
                rec.attributes,
            ))
            # flush records in chunks
            if len(rec_rows_batch) >= 2000:
                await execmany_chunked(my_cursor, sql_rec, rec_rows_batch, chunk=2000)
                rec_rows_batch.clear()

            # build record_variables rows (chunked too)
            for rv in rec.variables:
                rv_rows_batch.append((
                    rec_id,
                    rv.variable.id,
                    1 if rv.calculated else 0,
                    rv.mnemonic or "",
                    rv.curve_label or "",
                    rv.mnemonic32 or "",
                    rv.algorithm or 0,
                    (rv.ref_variable.id if rv.ref_variable else None),
                    rv.coeff1 or 0.0,
                    rv.coeff2 or 0.0,
                    rv.coeff3 or 0.0,
                ))
                if len(rv_rows_batch) >= 10000 and len(rec_rows_batch) == 0:
                    await execmany_chunked(my_cursor, sql_rv, rv_rows_batch, chunk=10000)
                    rv_rows_batch.clear()

            rec_id += 1

        # flush leftovers
        if rec_rows_batch:
            await execmany_chunked(my_cursor, sql_rec, rec_rows_batch, chunk=2000)
        if rv_rows_batch:
            await execmany_chunked(my_cursor, sql_rv, rv_rows_batch, chunk=10000)

    @staticmethod
    async def __LoadDatabaseTableDefinitionsFromFiles(files_for_database_config:list[str]) -> adi.AdiDefinitions.AdiDatabaseDefinitions:
        try:
            all_measurement_classes: dict[str, adi.AdiDefinitions.MeasurementClass] = {}
            all_unit_types: dict[str, adi.AdiDefinitions.UnitType] = {}
            all_variables: dict[str, adi.AdiDefinitions.AdiVariable] = {}
            all_records_types: dict[int, adi.AdiDefinitions.AdiRecordType] = {}
            all_options_lists: dict[str, list[str]] = {}
            all_records: dict[str, adi.AdiDefinitions.AdiRecord] = {}

            _ws_collapse = re.compile(r'\s+').sub
            def canon_key(s:str) -> str:
                # trim → collapse internal whitespace → casefold
                return sys.intern(_ws_collapse(' ', s.strip()).casefold())
                # return ' '.join(s.strip().split()).casefold()

            def iter_clean_lines(s:str):
                buf = []
                for raw in s.split('\n'):
                    t = raw.strip()
                    if not t or t.startswith('#'):
                        continue
                    if t.endswith('\\'):
                        buf.append(t[:-1])
                        continue
                    if buf:
                        t = ''.join(buf) + t
                        buf.clear()
                    yield t
            
            def csv_rows_from_text(s:str):
                rdr = csv.reader(iter_clean_lines(s), delimiter=';', skipinitialspace=True)
                for row in rdr:
                    yield [cell.strip() for cell in row if cell is not None]

            def parse_measurement_classes(rows_iter):
                """
                rows_iter: iterator of List[str] from csv_rows_from_text(slice_text)
                """
                last_obj = None
                for data in rows_iter:
                    if not data:
                        last_obj = None
                        continue
                    if len(data) < 5:
                        last_obj = adi.AdiDefinitions.MeasurementClass(name=data[0].strip())
                        key_name = canon_key(last_obj.name)
                        all_measurement_classes[key_name] = last_obj

                        mc_unit = adi.AdiDefinitions.UnitOption(long_name=data[1].strip(), short_name=data[2].strip())
                        last_obj.unit_options.append(mc_unit)
                    elif last_obj != None and len(data) >= 5:  # and line.startswith(" ")
                        mc_unit = adi.AdiDefinitions.UnitOption(long_name=data[0].strip(), short_name=data[1].strip(),
                                                    function_type=int(data[2].strip()), arg1=float(data[3].strip()),
                                                    arg2=float(data[4].strip()), psl_types=int(data[5].strip()))
                        last_obj.unit_options.append(mc_unit)

            def parse_unit_types(rows_iter):
                for data in rows_iter:
                    if len(data) >= 2:
                        mc_key_name = canon_key(data[0])
                        for i in range(1, len(data)):
                            name = data[i].strip()
                            unit_type = adi.AdiDefinitions.UnitType(name=name, measurement_class=adi.AdiDefinitions.MeasurementClass(name=mc_key_name))

                            key_name = canon_key(unit_type.name)
                            all_unit_types[key_name] = unit_type

            def parse_variables(rows_iter):
                def IdentifyVarType(var_type_str:str) -> list[int]:
                    if var_type_str == None or len(var_type_str) == 0:
                        raise Exception("Variable type not specified")
                    size = 0
                    var_type = 0
                    number_of_elements = 1
                    upper = var_type_str.upper()

                    if upper == "I1":
                        size = 1
                        var_type = adi.AdiEnums.VarType.ADI_VT_CHAR.value
                    elif upper == "I2":
                        size = 2
                        var_type = adi.AdiEnums.VarType.ADI_VT_SHORT.value
                    elif upper == "I4":
                        size = 4
                        var_type = adi.AdiEnums.VarType.ADI_VT_INT.value
                    elif upper == "U1":
                        size = 1
                        var_type = adi.AdiEnums.VarType.ADI_VT_UCHAR.value
                    elif upper == "U2":
                        size = 2
                        var_type = adi.AdiEnums.VarType.ADI_VT_USHORT.value
                    elif upper == "U4":
                        size = 4
                        var_type = adi.AdiEnums.VarType.ADI_VT_UINT.value
                    elif upper == "F4":
                        size = 4
                        var_type = adi.AdiEnums.VarType.ADI_VT_FLOAT.value
                    elif upper == "F8":
                        size = 8
                        var_type = adi.AdiEnums.VarType.ADI_VT_DOUBLE.value
                    elif var_type_str.startswith("C"):
                        size = int(var_type_str[1:])
                        var_type = adi.AdiEnums.VarType.ADI_VT_STRING.value
                    elif upper == "P4":
                        size = 4
                        var_type = adi.AdiEnums.VarType.ADI_VT_PCHAR.value
                    elif upper == "Q4":
                        size = 4
                        var_type = adi.AdiEnums.VarType.ADI_VT_PBYTE.value
                    else:
                        pattern = re.compile(
                            "([A-z0-9]+)[\\[\\(]([0-9]+)[\\]\\)]", re.IGNORECASE)
                        result = pattern.search(var_type_str)
                        if result != None:
                            IdentifyVarType(result.group(1))
                            number_of_elements = int(result.group(2))
                        else:
                            raise Exception(f"Invalid variable type \"{var_type_str}\"")
                    return [var_type, size, number_of_elements]

                def IdentifySpecial(special_str:str):
                    if special_str == None or len(special_str) == 0:
                        return 0
                    special_str = special_str.lower()
                    special = 0
                    if "c" in special_str: special += 1
                    if "o" in special_str: special += 2
                    if "e" in special_str: special += 32
                    if "t" in special_str: special += 8
                    if "d" in special_str: special += 4
                    if "w" in special_str: special += 16
                    if "l" in special_str: special += 64
                    if "v" in special_str: special += 256
                    return special

                for data in rows_iter:
                    if len(data) >= 8:
                        name = data[0].strip()
                        mnemonic = data[1].strip()
                        curve_label = data[2].strip()
                        unit_type_name = canon_key(data[3])
                        var_type_str = data[4].strip()
                        special_str = data[5].strip()
                        number_of_decimals = int(data[6].strip())
                        mnemonic32 = data[7].strip()

                        special = IdentifySpecial(special_str)
                        [var_type, size, number_of_elements] = IdentifyVarType(var_type_str)

                        variable = adi.AdiDefinitions.AdiVariable(name=name, mnemonic=mnemonic, curve_label=curve_label,
                                                                unit_type=adi.AdiDefinitions.UnitType(name=unit_type_name),
                                                                variables_types_id=var_type, special=special, size=size,
                                                                number_of_elements=number_of_elements,
                                                                number_of_decimals=number_of_decimals,
                                                                mnemonic32=mnemonic32)
                        key_name = canon_key(name)
                        all_variables[key_name] = variable

            def parse_option_lists(rows_iter):
                for data in rows_iter:
                    if len(data) >= 3:
                        list_name = data[0].strip()
                        key_name = canon_key(list_name)
                        ro = int(data[1].strip()) != 0
                        options = []
                        for i in range(2, len(data)):
                            name = data[i].strip()
                            options.append(name)

                        all_options_lists[key_name] = adi.AdiDefinitions.OptionsList(name=list_name, read_only=ro, options=options)

            def parse_record_types(rows_iter):
                for data in rows_iter:
                    if len(data) >= 2:
                        name = data[0].strip()
                        id = int(data[1].strip())
                        record_type = adi.AdiDefinitions.AdiRecordType(id=id, name=name)
                        all_records_types[id] = record_type

            def parse_records(rows_iter):
                
                def _parse_index_types(text:str) -> int:
                    text = (text or '').upper()
                    mask = 0
                    if 'S' in text: mask |= adi.AdiEnums.IndexType.Sequential.value
                    if 'T' in text: mask |= adi.AdiEnums.IndexType.Time.value
                    if 'D' in text: mask |= adi.AdiEnums.IndexType.Depth.value
                    if 'A' in text: mask |= adi.AdiEnums.IndexType.Activity.value
                    return mask

                def _parse_primary_keys(w_text:str, b_text:str, d_text:str) -> int:
                    mask = 0
                    if '2' in w_text: mask |= adi.AdiEnums.RecordPrimaryKeys.Well.value
                    if '2' in b_text: mask |= adi.AdiEnums.RecordPrimaryKeys.BitRun.value
                    if '2' in d_text: mask |= adi.AdiEnums.RecordPrimaryKeys.Description.value
                    return mask

                def _parse_attributes(h_text:str, r_text:str, l_text:str) -> int:
                    mask = 0
                    if '1' in h_text: mask |= adi.AdiEnums.RecordAttributes.Hidden.value
                    if '1' in r_text: mask |= adi.AdiEnums.RecordAttributes.ReadOnly.value
                    if '1' in l_text: mask |= adi.AdiEnums.RecordAttributes.Locked.value
                    return mask

                # tiny helpers
                def f0(x): 
                    # very common zeros: avoid float() when possible
                    return 0.0 if (x == '' or x == '0' or x == '0.0') else float(x)

                record_type_id_by_name = {rt.name.lower(): rt.id for rt in all_records_types.values()}
                algorithms = ["none", "bit test", "reciprocal", "vector access", "mod", "digit", "linear equation"]
                algorithms = {name: idx for idx, name in enumerate(algorithms)}
                categories = ["none", "surface logging", "mwd"]
                categories = {cat: idx for idx, cat in enumerate(categories)}

                last_obj = None
                for data in rows_iter:
                    if not data:
                        last_obj = None
                        continue
                    if (data[0] or '').lower().startswith('recdef'):
                        name = data[1].strip()
                        record_type_id = record_type_id_by_name.get(data[2].strip(), 0)
                        idx_mask = _parse_index_types(data[3] if len(data) > 3 else '')
                        category = categories.get(data[4].lower() if len(data) > 4 else '', 0)
                        pks_mask = _parse_primary_keys(data[5].strip(), data[6].strip(), data[7].strip())
                        psl = int(data[8] or 0)
                        attributes = _parse_attributes(data[9].strip(), data[10].strip(), data[11].strip())
                        last_obj = adi.AdiDefinitions.AdiRecord(
                            id=None, name=name,
                            record_type_id=record_type_id,
                            index_types=idx_mask,
                            category_id=category, primary_keys=pks_mask,
                            psl_types=psl, attributes=attributes
                        )
                        key_name = canon_key(name)
                        all_records[key_name] = last_obj
                        continue

                    # Variable row in record
                    if last_obj is None: continue

                    vname       = canon_key(data[0])             # Variable Name
                    stored_flag = int(data[1] or 0)              # 0=stored, 1=calculated
                    mnemonic    = data[2]
                    label       = data[3]
                    big_mn      = data[4]
                    algorithm   = algorithms.get(data[5].lower(), 0)
                    ref_name    = canon_key(data[6])
                    c1 = f0(data[7])
                    c2 = f0(data[8])
                    c3 = f0(data[9])
                    last_obj.variables.append(
                        adi.AdiDefinitions.AdiRecordVariable(
                            variable=adi.AdiDefinitions.AdiVariable(name=vname),
                            mnemonic=mnemonic,
                            curve_label=label,
                            mnemonic32=big_mn,
                            calculated=1 if stored_flag == 1 else 0,
                            algorithm=algorithm,
                            ref_variable=adi.AdiDefinitions.AdiVariable(name=ref_name) if len(ref_name) > 0 else None,
                            coeff1=c1, coeff2=c2, coeff3=c3
                        )
                    )

            dispatch = {
                'measurement classes': parse_measurement_classes,
                'unit types':          parse_unit_types,
                'variables':           parse_variables,
                'option lists':        parse_option_lists,
                'record types':        parse_record_types,
                'records':             parse_records,
            }

            if len(files_for_database_config) == 0:
                raise Exception("No files specified for database configuration")
            
            import time
            start_time = time.time()
            for file_path in files_for_database_config:
                if not os.path.isfile(file_path):
                    raise Exception(f"The specified file '{file_path}' does not exist.")    

                start_time_file = time.time()

                with open(file_path, 'rb') as f:        # binary is fastest
                    raw = f.read()                      # 40 MB -> fine in RAM
                text = raw.decode('utf-8', 'replace')   # one decode pass

                sec_re = re.compile(r'(?m)^:([^\n]+)')
                sections = []
                for m in sec_re.finditer(text):
                    name = m.group(1).strip()
                    before = m.start()
                    start = m.end()        # char offset right before the header line
                    sections.append([name, before, start, None])
                for i in range(len(sections) - 1):
                    sections[i][3] = sections[i+1][1]     # end char = next start
                sections[-1][3] = len(text)                # last section to EOF

                for name, _, a, b in sections:
                    name = name.strip().lower()
                    if name not in dispatch:
                        continue
                    slice_text = text[a:b]
                    csv_rows = csv_rows_from_text(slice_text)
                    dispatch[name](csv_rows)

                print(f"Parsed '{file_path}' in {time.time() - start_time_file:.2f} seconds")

            # ===================
            # Cross references (fast)
            # ===================

            # 1) Unit Types ↔ Measurement Classes
            mc_get = all_measurement_classes.get
            for ut in all_unit_types.values():
                mc = mc_get(ut.measurement_class.name)  # already canonical
                if mc is None:
                    raise Exception(f"Unit Type '{ut.name}' references unknown Measurement Class '{ut.measurement_class.name}'")
                ut.measurement_class = mc

            # 2) Variables ↔ Unit Types + Option Lists
            ut_get = all_unit_types.get
            ol_get = all_options_lists.get
            OPT_FLAG = adi.AdiEnums.VariableSpecialHandlings.OptionList.value

            # iterate items to reuse the canonical key you stored in the dict
            for v_key, var in all_variables.items():
                # Unit Type
                ut = ut_get(var.unit_type.name)  # was set to canonical name during parsing
                if ut is None:
                    raise Exception(f"Variable '{var.name}' references unknown Unit Type '{var.unit_type.name}'")
                var.unit_type = ut

                # Option List (key is the variable's canonical name; reuse v_key)
                if var.special & OPT_FLAG:
                    ol = ol_get(v_key)
                    if ol is None:
                        # decide: either ignore silently or raise/log once after collecting
                        # raise Exception(f"Options List for Variable '{var.name}' not found")
                        pass
                    else:
                        var.options_list = ol

            # 3) Records ↔ Variables + Ref Variables
            v_get = all_variables.get
            for rec in all_records.values():
                for rv in rec.variables:
                    v = v_get(rv.variable.name)  # rv.variable.name was set to canonical during parsing
                    if v is None:
                        raise Exception(f"Record '{rec.name}' references unknown Variable '{rv.variable.name}'")
                    rv.variable = v

                    if rv.ref_variable:
                        ref = v_get(rv.ref_variable.name)
                        if ref is not None:
                            rv.ref_variable = ref
                        # else keep None or collect for a single aggregated error/report

            print(f"Parsing completed in {time.time() - start_time:.2f} seconds")

        except Exception as e:
            print(f"It was not possible to read the specified file: {repr(e)}")
        
        return adi.AdiDefinitions.AdiDatabaseDefinitions(all_measurement_classes, all_unit_types, all_variables, all_records_types, all_records)

    @staticmethod
    def IsWellNameValid(well_name:str) -> bool:
        if well_name == None or len(well_name) < 3:
            return False
        pattern = re.compile("^[A-Za-z0-9_\\-]+$")
        result = pattern.search(well_name)
        return result != None

    @staticmethod
    async def CreateNewAdiServer(name:str, db_name:str, well:str, run:str, database_definitions:adi.AdiDefinitions.AdiDatabaseDefinitions=None, files_for_database_config:list[str]=None, listen_to_tcp:bool=True, control:rigs_control.rigs.RigsControl=None)->AdiServer:
        if db_name == None or len(db_name) == 0:
            raise Exception("Database name not specified")
        if well == None or len(well) == 0:
            raise Exception("Well name not specified")
        if run == None or len(run) == 0:
            raise Exception("Run name not specified")
        if not run.isnumeric() or int(run) < 1:
            raise Exception("Invalid run number")
        if not AdiServer.IsWellNameValid(well):
            raise Exception("Well name is invalid")

        async def CreateTables(mycursor: mysql.connector.abstracts.MySQLCursorAbstract, db_name: str):
            sql = """
                SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
            """
            await mycursor.execute(sql)

            sql = """
                SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
            """
            await mycursor.execute(sql)

            sql = """
                SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
            """
            await mycursor.execute(sql)

            # Table Wells
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`wells`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`wells` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `name` VARCHAR(45) NOT NULL,
                PRIMARY KEY (`id`))
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Runs
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`runs`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`runs` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `wells_id` INT NOT NULL,
                `run_alias` VARCHAR(45) NOT NULL,
                `run_number` INT NOT NULL,
                PRIMARY KEY (`id`),
                INDEX `fk_runs_wells_idx` (`wells_id` ASC) VISIBLE,
                CONSTRAINT `fk_runs_wells`
                    FOREIGN KEY (`wells_id`)
                    REFERENCES `{db_name}`.`wells` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION)
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Records Types
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`records_types`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`records_types` (
                `id` INT NOT NULL,
                `name` VARCHAR(45) NOT NULL,
                PRIMARY KEY (`id`))
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Records Categories
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`records_categories`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`records_categories` (
                `id` INT NOT NULL,
                `name` VARCHAR(45) NOT NULL,
                PRIMARY KEY (`id`))
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Records
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`records`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`records` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `name` VARCHAR(45) NOT NULL,
                `records_types_id` INT NOT NULL,
                `index_types` INT NOT NULL COMMENT 'RECORD_PK_WELL = 1;\nRECORD_PK_BITRUN = 2;\nRECORD_PK_DESCRIPTION = 4;',
                `records_categories_id` INT NULL,
                `primary_keys` TINYINT NOT NULL,
                `psl_types` INT NOT NULL,
                `attributes` INT NOT NULL,
                PRIMARY KEY (`id`),
                INDEX `fk_records_records_types1_idx` (`records_types_id` ASC) VISIBLE,
                INDEX `fk_records_records_categories1_idx` (`records_categories_id` ASC) VISIBLE,
                CONSTRAINT `fk_records_records_types1`
                    FOREIGN KEY (`records_types_id`)
                    REFERENCES `{db_name}`.`records_types` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION,
                CONSTRAINT `fk_records_records_categories1`
                    FOREIGN KEY (`records_categories_id`)
                    REFERENCES `{db_name}`.`records_categories` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION)
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table MC Units
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`mc_units`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`mc_units` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `measurement_classes_id` INT NOT NULL,
                `name_long` VARCHAR(45) NOT NULL,
                `name_short` VARCHAR(45) NOT NULL,
                `function_type` TINYINT NOT NULL,
                `arg1` DOUBLE NOT NULL,
                `arg2` DOUBLE NOT NULL,
                `psl_types` INT NOT NULL,
                PRIMARY KEY (`id`),
                INDEX `fk_mc_units_measurement_classes1_idx` (`measurement_classes_id` ASC) VISIBLE,
                CONSTRAINT `fk_mc_units_measurement_classes1`
                    FOREIGN KEY (`measurement_classes_id`)
                    REFERENCES `{db_name}`.`measurement_classes` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION)
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Measurement Classes
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`measurement_classes`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`measurement_classes` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `name` VARCHAR(45) NOT NULL,
                `mc_default_id` INT NULL,
                PRIMARY KEY (`id`),
                INDEX `fk_measurement_classes_measurement_classes_units1_idx` (`mc_default_id` ASC) VISIBLE,
                CONSTRAINT `fk_measurement_classes_measurement_classes_units1`
                    FOREIGN KEY (`mc_default_id`)
                    REFERENCES `{db_name}`.`mc_units` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION)
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Unit Types
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`unit_types`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`unit_types` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `measurement_classes_id` INT NOT NULL,
                `name` VARCHAR(45) NOT NULL,
                PRIMARY KEY (`id`),
                INDEX `fk_unit_types_measurement_classes1_idx` (`measurement_classes_id` ASC) VISIBLE,
                CONSTRAINT `fk_unit_types_measurement_classes1`
                    FOREIGN KEY (`measurement_classes_id`)
                    REFERENCES `{db_name}`.`measurement_classes` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION)
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Unit Sets
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`unitsets`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`unitsets` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `name` VARCHAR(45) NOT NULL,
                PRIMARY KEY (`id`))
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Unit Sets Options
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`unitsets_options`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`unitsets_options` (
                `unitsets_id` INT NOT NULL AUTO_INCREMENT,
                `unit_types_id` INT NOT NULL,
                `mc_units_id` INT NOT NULL,
                PRIMARY KEY (`unitsets_id`, `unit_types_id`),
                INDEX `fk_unitsets_options_unit_types1_idx` (`unit_types_id` ASC) VISIBLE,
                INDEX `fk_unitsets_options_mc_units1_idx` (`mc_units_id` ASC) VISIBLE,
                CONSTRAINT `fk_unitsets_options_unit_types1`
                    FOREIGN KEY (`unit_types_id`)
                    REFERENCES `{db_name}`.`unit_types` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION,
                CONSTRAINT `fk_unitsets_options_mc_units1`
                    FOREIGN KEY (`mc_units_id`)
                    REFERENCES `{db_name}`.`mc_units` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION)
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Variables Types
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`variables_types`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`variables_types` (
                `id` INT NOT NULL,
                `name` VARCHAR(45) NOT NULL,
                PRIMARY KEY (`id`))
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Options Lists
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`options_lists`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`options_lists` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `name` VARCHAR(45) NOT NULL,
                `read_only` TINYINT NOT NULL,
                PRIMARY KEY (`id`))
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Options Lists Options
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`options_lists_options`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`options_lists_options` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `options_lists_id` INT NOT NULL,
                `name` VARCHAR(100) NOT NULL,
                PRIMARY KEY (`id`),
                INDEX `fk_option_lists_options_options_lists1_idx` (`options_lists_id` ASC) VISIBLE,
                CONSTRAINT `fk_option_lists_options_options_lists1`
                    FOREIGN KEY (`options_lists_id`)
                    REFERENCES `{db_name}`.`options_lists` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION)
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Variables
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`variables`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`variables` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `name` VARCHAR(45) NOT NULL,
                `mnemonic` VARCHAR(4) NULL,
                `curve_label` VARCHAR(45) NULL,
                `unit_types_id` INT NOT NULL,
                `variables_types_id` INT NOT NULL COMMENT 'ADI_VT_ARRAY = __MIN_INT,\nADI_VT_NONE = 0,\nADI_VT_CHAR = 1,\nADI_VT_UCHAR = 2,\nADI_VT_SHORT = 3,\nADI_VT_USHORT = 4,\nADI_VT_INT = 5,\nADI_VT_LONG = 5,\nADI_VT_UINT = 6,\nADI_VT_ULONG = 6,\nADI_VT_FLOAT = 7,\nADI_VT_DOUBLE = 8,\nADI_VT_STRING = 9,\nADI_VT_PCHAR = 10,\nADI_VT_BINARY = 11,\nADI_VT_PBYTE = 12,\nADI_VT_ENUM = 13',
                `special` INT NOT NULL COMMENT 'Nothing = 0,\nCalculated = 1,\nOptionList = 2,\nDerivedDepth = 4,\nDateFormat = 8,\nWaveForm = 16,\nEnumList = 32,\nBoundArray = 64,\nVectorData = 256',
                `options_lists_id` INT NULL,
                `size` INT NOT NULL,
                `number_of_elements` INT NOT NULL,
                `number_of_decimals` INT NOT NULL,
                `mnemonic32` VARCHAR(45) NULL,
                PRIMARY KEY (`id`),
                INDEX `fk_variables_unit_types1_idx` (`unit_types_id` ASC) VISIBLE,
                INDEX `fk_variables_variables_types1_idx` (`variables_types_id` ASC) VISIBLE,
                INDEX `fk_variables_options_lists1_idx` (`options_lists_id` ASC) VISIBLE,
                CONSTRAINT `fk_variables_unit_types1`
                    FOREIGN KEY (`unit_types_id`)
                    REFERENCES `{db_name}`.`unit_types` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION,
                CONSTRAINT `fk_variables_variables_types1`
                    FOREIGN KEY (`variables_types_id`)
                    REFERENCES `{db_name}`.`variables_types` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION,
                CONSTRAINT `fk_variables_options_lists1`
                    FOREIGN KEY (`options_lists_id`)
                    REFERENCES `{db_name}`.`options_lists` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION)
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Algorithms Calculation
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`algorithms_calculation`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`algorithms_calculation` (
                `id` INT NOT NULL,
                `name` VARCHAR(45) NOT NULL,
                PRIMARY KEY (`id`))
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Records Variables
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`records_variables`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`records_variables` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `records_id` INT NOT NULL,
                `variables_id` INT NOT NULL,
                `calculated` TINYINT NOT NULL COMMENT '0=variable stored in record, 1=calculated',
                `mnemonic` VARCHAR(4) NULL,
                `curve_label` VARCHAR(45) NULL,
                `mnemonic32` VARCHAR(45) NULL,
                `algorithms_calculation_id` INT NULL,
                `reference_variable_id` INT NULL,
                `coeff1` DOUBLE NOT NULL,
                `coeff2` DOUBLE NOT NULL,
                `coeff3` DOUBLE NOT NULL,
                PRIMARY KEY (`id`),
                INDEX `fk_records_variables_records1_idx` (`records_id` ASC) VISIBLE,
                INDEX `fk_records_variables_variables1_idx` (`variables_id` ASC) VISIBLE,
                INDEX `fk_records_variables_algorithms_calculation1_idx` (`algorithms_calculation_id` ASC) VISIBLE,
                INDEX `fk_records_variables_variables2_idx` (`reference_variable_id` ASC) VISIBLE,
                CONSTRAINT `fk_records_variables_records1`
                    FOREIGN KEY (`records_id`)
                    REFERENCES `{db_name}`.`records` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION,
                CONSTRAINT `fk_records_variables_variables1`
                    FOREIGN KEY (`variables_id`)
                    REFERENCES `{db_name}`.`variables` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION,
                CONSTRAINT `fk_records_variables_algorithms_calculation1`
                    FOREIGN KEY (`algorithms_calculation_id`)
                    REFERENCES `{db_name}`.`algorithms_calculation` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION,
                CONSTRAINT `fk_records_variables_variables2`
                    FOREIGN KEY (`reference_variable_id`)
                    REFERENCES `{db_name}`.`variables` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION)
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Data Tables
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`data_tables`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`data_tables` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `wells_id` INT NOT NULL,
                `runs_id` INT NOT NULL,
                `records_id` INT NOT NULL,
                `description` VARCHAR(45) NOT NULL,
                PRIMARY KEY (`id`),
                INDEX `fk_data_wells1_idx` (`wells_id` ASC) VISIBLE,
                INDEX `fk_data_runs1_idx` (`runs_id` ASC) VISIBLE,
                INDEX `fk_data_records1_idx` (`records_id` ASC) VISIBLE,
                CONSTRAINT `fk_data_wells1`
                    FOREIGN KEY (`wells_id`)
                    REFERENCES `{db_name}`.`wells` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION,
                CONSTRAINT `fk_data_runs1`
                    FOREIGN KEY (`runs_id`)
                    REFERENCES `{db_name}`.`runs` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION,
                CONSTRAINT `fk_data_records1`
                    FOREIGN KEY (`records_id`)
                    REFERENCES `{db_name}`.`records` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION)
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Data Tables Variables
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`data_tables_variables`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`data_tables_variables` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `data_tables_id` INT NOT NULL,
                `variables_id` INT NOT NULL,
                `calculated` TINYINT NOT NULL,
                `mnemonic` VARCHAR(4) NULL,
                `curve_label` VARCHAR(45) NULL,
                `mnemonic32` VARCHAR(45) NULL,
                `algorithms_calculation_id` INT NULL,
                `reference_variable_id` INT NULL,
                `coeff1` DOUBLE NOT NULL,
                `coeff2` DOUBLE NOT NULL,
                `coeff3` DOUBLE NOT NULL,
                PRIMARY KEY (`id`),
                INDEX `fk_data_tables_variables_data_tables1_idx` (`data_tables_id` ASC) VISIBLE,
                INDEX `fk_data_tables_variables_variables1_idx` (`variables_id` ASC) VISIBLE,
                CONSTRAINT `fk_data_tables_variables_data_tables1`
                    FOREIGN KEY (`data_tables_id`)
                    REFERENCES `{db_name}`.`data_tables` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION,
                CONSTRAINT `fk_data_tables_variables_variables1`
                    FOREIGN KEY (`variables_id`)
                    REFERENCES `{db_name}`.`variables` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION)
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Variables Vector Types
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`variables_vector_types`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`variables_vector_types` (
                `id` INT NOT NULL,
                `name` VARCHAR(45) NOT NULL,
                PRIMARY KEY (`id`))
                ENGINE = InnoDB
                COMMENT = 'Unknown = 0\nUnsignedByteId = 1\nUnsignedShortId = 2\nUnsignedIntId = 3\nByteId = 4\nShortId = 5\nIntId = 6\nFloatId = 7\nDoubleId = 8';
            """
            await mycursor.execute(sql)

            # Table Variables Vector Attributes
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`variables_vector_attributes`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`variables_vector_attributes` (
                `data_tables_id` INT NOT NULL,
                `variables_id` INT NOT NULL,
                `variables_vector_types_id` INT NOT NULL,
                `unit_types_id` INT NOT NULL,
                `bin_start` DOUBLE NOT NULL,
                `bin_end` DOUBLE NOT NULL,
                PRIMARY KEY (`data_tables_id`, `variables_id`),
                INDEX `fk_variables_vector_attributes_unit_types1_idx` (`unit_types_id` ASC) VISIBLE,
                INDEX `fk_variables_vector_attributes_variables_vector_types1_idx` (`variables_vector_types_id` ASC) VISIBLE,
                INDEX `fk_variables_vector_attributes_data_tables1_idx` (`data_tables_id` ASC) VISIBLE,
                CONSTRAINT `fk_variables_vector_attributes_variables1`
                    FOREIGN KEY (`variables_id`)
                    REFERENCES `{db_name}`.`variables` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION,
                CONSTRAINT `fk_variables_vector_attributes_unit_types1`
                    FOREIGN KEY (`unit_types_id`)
                    REFERENCES `{db_name}`.`unit_types` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION,
                CONSTRAINT `fk_variables_vector_attributes_variables_vector_types1`
                    FOREIGN KEY (`variables_vector_types_id`)
                    REFERENCES `{db_name}`.`variables_vector_types` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION,
                CONSTRAINT `fk_variables_vector_attributes_data_tables1`
                    FOREIGN KEY (`data_tables_id`)
                    REFERENCES `{db_name}`.`data_tables` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION)
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            # Table Current Job
            sql = f"""
                -- -----------------------------------------------------
                -- Table `{db_name}`.`current_job`
                -- -----------------------------------------------------
                CREATE TABLE IF NOT EXISTS `{db_name}`.`current_job` (
                `id` INT NOT NULL DEFAULT 1,
                `runs_id` INT NOT NULL,
                `unitsets_id` INT NOT NULL,
                `activity` INT NOT NULL DEFAULT 0,
                `bit_depth` DOUBLE NOT NULL,
                `hole_depth` DOUBLE NOT NULL,
                `drill_model_desc` VARCHAR(45) NULL,
                `lithology_desc` VARCHAR(45) NULL,
                `survey_desc` VARCHAR(45) NULL,
                PRIMARY KEY (`id`),
                INDEX `fk_current_job_runs1_idx` (`runs_id` ASC) VISIBLE,
                INDEX `fk_current_job_unitsets1_idx` (`unitsets_id` ASC) VISIBLE,
                CONSTRAINT `fk_current_job_runs1`
                    FOREIGN KEY (`runs_id`)
                    REFERENCES `{db_name}`.`runs` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION,
                CONSTRAINT `fk_current_job_unitsets1`
                    FOREIGN KEY (`unitsets_id`)
                    REFERENCES `{db_name}`.`unitsets` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION)
                ENGINE = InnoDB;
            """
            await mycursor.execute(sql)

            sql = """
                SET SQL_MODE=@OLD_SQL_MODE;
            """
            await mycursor.execute(sql)

            sql = """
                SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
            """
            await mycursor.execute(sql)

            sql = """
                SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
            """
            await mycursor.execute(sql)

        async def PopulateFirstTables(mycursor: mysql.connector.abstracts.MySQLCursorAbstract, db_name: str):
            sql = f"""INSERT INTO `{db_name}`.`variables_types` (name, id) VALUES
                ('ADI_VT_NONE', 0), ('ADI_VT_CHAR', 1), ('ADI_VT_UCHAR', 2), ('ADI_VT_SHORT', 3),
                ('ADI_VT_USHORT', 4), ('ADI_VT_INT', 5), ('ADI_VT_UINT', 6),
                ('ADI_VT_FLOAT', 7), ('ADI_VT_DOUBLE', 8), ('ADI_VT_STRING', 9),
                ('ADI_VT_PCHAR', 10), ('ADI_VT_BINARY', 11), ('ADI_VT_PBYTE', 12), ('ADI_VT_ENUM', 13)"""
            await mycursor.execute(sql)

            sql = f"""INSERT INTO `{db_name}`.`variables_vector_types` (name, id) VALUES
                ('Unknown', 0), ('UnsignedByteId', 1), ('UnsignedShortId', 2), ('UnsignedIntId', 3),
                ('ByteId', 4), ('ShortId', 5), ('IntId', 6),
                ('FloatId', 7), ('DoubleId', 8)"""
            await mycursor.execute(sql)

            sql = f"""INSERT INTO `{db_name}`.`records_categories` (name, id) VALUES
                ('None', 0), ('Surface Logging', 1), ('MWD', 2)"""
            await mycursor.execute(sql)

            sql = f"""INSERT INTO `{db_name}`.`algorithms_calculation` (id, name) values (0, 'None'), (1, 'Bit Test'), (2, 'Reciprocal'), (3, 'Vector Access'), (4, 'Mod'), (5, 'Digit'), (6, 'Linear Equation')"""
            await mycursor.execute(sql)
            
            sql = f"""INSERT INTO `{db_name}`.`wells` (name) VALUES (%s)"""
            await mycursor.execute(sql, (well,))
            well_id = mycursor.lastrowid
            
            run_alias = run.zfill(4)
            sql = f"""INSERT INTO `{db_name}`.`runs` (wells_id, run_alias, run_number) VALUES (%s, %s, %s)"""
            await mycursor.execute(sql, (well_id, run_alias, int(run)))
            run_id = mycursor.lastrowid
            
            sql = f"""INSERT INTO `{db_name}`.`unitsets` (name) VALUES ('Default')"""
            await mycursor.execute(sql)
            unitset_id = mycursor.lastrowid

            sql = f"""INSERT INTO `{db_name}`.`current_job` (id, runs_id, unitsets_id, activity, bit_depth, hole_depth, survey_desc) VALUES (1, %s, %s, 0, 0, 0, 'Survey')"""
            await mycursor.execute(sql, (run_id, unitset_id))

        if database_definitions == None:
            if files_for_database_config == None or len(files_for_database_config) == 0:
                raise Exception("Standard definitions file path not specified")
            if any([f == None or len(f) == 0 or not os.path.isfile(f) for f in files_for_database_config]):
                raise Exception("One or more standard definitions file paths are invalid")

            import time
            start_time = time.time()
            database_definitions = await AdiServer.__LoadDatabaseTableDefinitionsFromFiles(files_for_database_config)
            print(f"Standard definitions loaded in {time.time() - start_time:.2f} seconds")

        # Ensuring database_definitions.variables.get('t/d activity').options_list.options exists and has "OffBottom Drilling" and "Wipe"
        if not hasattr(database_definitions, 'variables') or database_definitions.variables is None or not hasattr(database_definitions.variables, 'get') or database_definitions.variables.get('t/d activity') is None:
            raise Exception("The standard definitions must include the variable 't/d activity' with an options list")
        activities = database_definitions.variables.get('t/d activity').options_list.options
        if not 'OffBottom Drilling' in activities: activities.append('OffBottom Drilling')
        if not 'Wipe' in activities: activities.append('Wipe')

        conn: mysql.connector.abstracts.MySQLConnectionAbstract = None
        mycursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            # Getting a connection to MySQL server and checking if the database exists
            conn = await AdiServer.__GetOneTimeDatabaseConnection(None)
            mycursor = await conn.cursor()

            # Check if the database exists
            await mycursor.execute(f"SHOW DATABASES LIKE '{db_name}';")
            result = await mycursor.fetchone()
            if result: raise Exception(f"Database '{db_name}' already exists.")

            # If the database does not exist, create it
            await mycursor.execute(f"CREATE DATABASE `{db_name}`;")
            await mycursor.execute(f"USE `{db_name}`;")
            await CreateTables(mycursor, db_name)
            await conn.start_transaction()
            await PopulateFirstTables(mycursor, db_name)
            await AdiServer.__ReplaceDatabaseTableDefinitions(mycursor, db_name, database_definitions)
            
            await conn.commit()

            return AdiServer(name, db_name, listen_to_tcp, control)
        except Exception as ex:
            await conn.rollback()
            raise ex
        finally:
            if mycursor != None:
                await mycursor.close()
            if conn is not None:
                await conn.close()

    def __init__(self, id:int, name:str, db_name:str, listen_to_tcp:bool=True, control:rigs_control.rigs.RigsControl=None):
        EventEmitter.__init__(self)
    
        self.id = id
        self.name = name
        self.db_name = db_name
        self.NextRunNumber = 11123

        self.enabled:bool = False
        self.listen_to_tcp:bool = listen_to_tcp

        self.server_iris:AdiServerIris.AdiServerIris = AdiServerIris.AdiServerIris(self)
        self.data_transfers:list[adi.AdiDefinitions.AdiDataTransfer] = []

        self._setup_volatiles(control)

    def _setup_volatiles(self, control:rigs_control.rigs.RigsControl):
        self._v_control = control

        # Volatile variables which will not be persisted
        # into the ZODB database.
        self._v_server:Server = None
        self._v_server_rt:Server = None
        self._v_loop:AbstractEventLoop = None

        if not hasattr(self, 'server_iris') or self.server_iris is None: self.server_iris = AdiServerIris.AdiServerIris(self)
        self.server_iris._setup_volatiles(self)

        self._v_running:bool = False

        from adi.AdiClientToLocal import AdiClientToLocal
        self._v_clients:list[AdiClientToLocal] = []
        self._v_clients_rt:list = []
        self._v_open_datasets:list[AdiOpenDataSet] = []
        self._v_rt_monitors:list[adi.AdiDefinitions.AdiRTMonitor] = []

        self._v_mydb_lock:asyncio.Lock = asyncio.Lock()
        self._v_mydb:mysql.connector.abstracts.MySQLConnectionAbstract = None

        self._v_activities = []
        self._v_unit_types = []
        self._v_records:dict[str, adi.AdiDefinitions.AdiRecord] = {}
        self._v_current:CurrentData = None

        self._v_callers_for_connection:dict[str, int] = {}

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._setup_volatiles(None)

    async def GenerateEvent(self, event_type:AdiServerEventType):
        self._v_loop.create_task(self.emit(event_type.name, AdiServerEvent(event_type, self)))

    async def __GetDatabaseConnection(self) -> mysql.connector.abstracts.MySQLConnectionAbstract:
        conn:mysql.connector.abstracts.MySQLConnectionAbstract = None
        if DB_HOST == None:
            conn = await mysql.connector.aio.connect(
                pool_name=f"local_pool_{self.db_name}",
                pool_size=6,
                autocommit=True,
                pool_reset_session=True,
                user=DB_USER,
                unix_socket=DB_SOCKET,
                database=self.db_name
            )
        else:
            conn = await mysql.connector.aio.connect(
                pool_name=f"local_pool_{self.db_name}",
                pool_size=6,
                autocommit=True,
                pool_reset_session=True,
                user=DB_USER,
                password=DB_PASS,
                host=DB_HOST,
                database=self.db_name
            )
        return conn

    async def Start(self, loop:AbstractEventLoop):
        if hasattr(self, '_v_running') and self._v_running: raise Exception("RigsStats is already running!")
        EventEmitter.__init__(self)

        self._v_server:Server = None
        self._v_server_rt:Server = None
        self._v_loop:AbstractEventLoop = loop

        from adi.AdiClientToLocal import AdiClientToLocal
        self._v_clients:list[AdiClientToLocal] = []
        self._v_clients_rt:list = []
        self._v_open_datasets:list[AdiOpenDataSet] = []

        self._v_mydb_lock:asyncio.Lock = asyncio.Lock()
        self._v_mydb:mysql.connector.abstracts.MySQLConnectionAbstract = None
        
        self._v_activities = []
        self._v_unit_types = []
        self._v_current:CurrentData = None

        try:
            await self.__LoadInitialDataFromDB()
        except Exception as ex:
            print(f"Error during initialization of ADI Server '{self.name}': {repr(ex)}")

        if self.server_iris.enabled:
            self.server_iris.Start(self._v_loop)

        self._v_running = True
        if self.enabled and self.listen_to_tcp:
            await self.__StartTcpServerProcess()

    async def Stop(self):
        if not self._v_running:
            raise Exception("ADI Server is not running.")

        if self.server_iris.enabled:
            await self.server_iris.Stop()

        self._v_running = False

        await self.__DisconnectTcp()


        if self._v_mydb != None:
            if await self._v_mydb.is_connected():
                await self._v_mydb.close()
            self._v_mydb = None

        self._v_activities = []
        self._v_unit_types = []
        self._v_current:CurrentData = None
        self._v_open_datasets = []

    async def SetEnabled(self, enabled):
        self.enabled = enabled

        if self._v_running and self.enabled and self.listen_to_tcp:
            await self.__StartTcpServerProcess()
        elif not self.enabled and self.listen_to_tcp:
            await self.__DisconnectTcp()

    async def StartAdiServer(self):
        if self.listen_to_tcp:
            raise Exception("ADI Server is already configured to listen to ADI connections.")
        if self._v_running:
            self.listen_to_tcp = True
            if self.enabled:
                await self.__StartTcpServerProcess()

    async def StopAdiServer(self):
        if not self.listen_to_tcp:
            raise Exception("ADI Server is already configured to not listen to ADI connections.")
        if self._v_running:
            self.listen_to_tcp = False
            await self.__DisconnectTcp()

    async def UpdateServerData(self, name:str, well:str, run:str, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None):
        owns_conn = conn is None
        if name == None or len(name) == 0:
            raise Exception("Server name cannot be empty.")
        if well == None or len(well) == 0:
            raise Exception("Well name cannot be empty.")
        if run == None or len(run) == 0:
            raise Exception("Run name cannot be empty.")
        if not run.isnumeric() or int(run) < 1:
            raise Exception("Invalid run number")
        if not AdiServer.IsWellNameValid(well):
            raise Exception("Well name is invalid")

        old_well = self._v_current.well
        old_run = self._v_current.run

        owns_conn = False
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()

            await cursor.execute(f"SELECT id FROM wells WHERE name=%s", (well,))
            result = await cursor.fetchone()
            if result == None:
                await cursor.execute(f"INSERT INTO wells (name) VALUES (%s)", (well,))
                well_id = cursor.lastrowid
            else:
                (well_id,) = result

            run_alias = run.zfill(4)
            await cursor.execute(f"SELECT id FROM runs WHERE wells_id=%s AND run_alias=%s", (well_id, run_alias))
            result = await cursor.fetchone()
            if result == None:
                await cursor.execute(f"INSERT INTO runs (wells_id, run_alias, run_number) VALUES (%s, %s, %s)", (well_id, run_alias, int(run)))
                run_id = cursor.lastrowid
            else:
                (run_id,) = result

            await cursor.execute(f"UPDATE current_job SET runs_id=%s, activity=%s WHERE id=1", (run_id, 0))

            if old_well != well:
                await self.GenerateEvent(AdiServerEventType.WELL_CHANGED)
                await self.GenerateEvent(AdiServerEventType.RUN_CHANGED)
            elif old_run != run:
                await self.GenerateEvent(AdiServerEventType.RUN_CHANGED)
        except Exception as ex:
            raise ex
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

        self.name = name
        self._v_current.well = well
        self._v_current.run = run
        self._v_current.activity = 0
        return True

    async def RemoveFullDatabase(self, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None):
        owns_conn = conn is None
        if self.enabled:
            raise Exception("Cannot remove the database while the ADI Server is running. Please stop it first.")

        await self.Stop()
        
        try:
            if conn is None: conn = await AdiServer.__GetOneTimeDatabaseConnection(None)
            mycursor: mysql.connector.abstracts.MySQLCursorAbstract = await conn.cursor()
            await mycursor.execute(f"DROP DATABASE IF EXISTS `{self.db_name}`;")
            await mycursor.close()
        except Exception as ex:
            raise ex
        finally:
            if owns_conn and conn is not None:
                await conn.close()

    async def StartIrisServer(self):
        if self.server_iris.enabled:
            raise Exception("Iris Server is already running.")
        self.db.set_adi_server_iris_enabled(self, True)
        self.server_iris.Start(self._v_loop)
        return True

    async def StopIrisServer(self):
        if not self.server_iris.enabled:
            raise Exception("Iris Server is not running.")
        self.db.set_adi_server_iris_enabled(self, False)
        await self.server_iris.Stop()
        return True

    async def __DisconnectTcp(self):
        # disconnecting all clients
        for c in self._v_clients:
            await c.Disconnect()

        if self._v_server != None:
            self._v_server.close()
        if self._v_server_rt != None:
            self._v_server_rt.close()

        # closing all RT sockets without clients associated
        socket_writer_rt:asyncio.StreamWriter
        for [_, socket_writer_rt] in self._v_clients_rt:
            if socket_writer_rt.is_closing(): continue
            socket_writer_rt.close()
            await socket_writer_rt.wait_closed()
        self._v_clients_rt.clear()

        self._v_clients = []
        self._v_clients_rt = []

        if self._v_server != None:
            await self._v_server.wait_closed()
            self._v_server = None
        if self._v_server_rt != None:
            await self._v_server_rt.wait_closed()
            self._v_server_rt = None

    async def __StartTcpServerProcess(self):
        try:
            self._v_server = await asyncio.start_server(self.__AcceptClient, "0.0.0.0", 23052)
            self._v_server_rt = await asyncio.start_server(self.__AcceptClientRT, "0.0.0.0", 23053)
        except Exception as ex:
            await self.Stop()
            raise ex

    async def __AcceptClient(self, reader:StreamReader, writer:StreamWriter):
        from adi.AdiClientToLocal import AdiClientToLocal
        client = AdiClientToLocal(self, self._v_loop, reader, writer)
        self._v_clients.append(client)

    async def __AcceptClientRT(self, reader:StreamReader, writer:StreamWriter):
        self._v_clients_rt.append([reader, writer])
        for c in self._v_clients:
            if c.writer == None: continue
            [c_ip, c_port] = c.writer.get_extra_info('peername')
            [s_ip, s_port] = writer.get_extra_info('peername')
            if not c.realtime_transferred and c_ip == s_ip:
                c.realtime_transferred = True
                c.reader_rt, c.writer_rt = reader, writer
                writer.write(struct.pack(f"<I", c.realtime_id))
                await writer.drain()

    async def __LoadInitialDataFromDB(self, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None):
        owns_conn = conn is None
        self._v_activities = []
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            import time
            start_time = time.time()

            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            query = "SELECT name FROM options_lists_options WHERE options_lists_id=(SELECT id FROM options_lists WHERE name='T/D Activity') ORDER BY id"
            await cursor.execute(query)
            results = await cursor.fetchall()
            for (name,) in results:
                self._v_activities.append(name)

            query = "SELECT wells.name AS well, runs.run_alias AS run, activity, bit_depth, hole_depth, drill_model_desc, lithology_desc, survey_desc, us.name unitset FROM current_job AS c LEFT JOIN runs ON c.runs_id = runs.id LEFT JOIN wells ON wells.id = runs.wells_id LEFT JOIN unitsets AS us ON c.unitsets_id = us.id WHERE c.id=1"
            await cursor.execute(query)
            results = await cursor.fetchall()
            for (well, run, activity, bit_depth, hole_depth, drill_model_desc, lithology_desc, survey_desc, unitset) in results:
                self._v_current = CurrentData(well=well, run=run, activity=activity, bit_depth=bit_depth, hole_depth=hole_depth,
                                            drill_model_desc=drill_model_desc, lithology_desc=lithology_desc, survey_desc=survey_desc, unitset=unitset)

            self._v_unit_types = []
            query = "SELECT name FROM unit_types ORDER BY id"
            await cursor.execute(query)
            results = await cursor.fetchall()
            for (name,) in results: self._v_unit_types.append(adi.AdiDefinitions.UnitType(id=len(self._v_unit_types), name=name))

            await self.__LoadUnitOptionsFromUnitset(conn)

            sql = "SELECT name FROM options_lists_options WHERE options_lists_id=(SELECT id FROM options_lists WHERE name='Data Group') ORDER BY id"
            await cursor.execute(sql)
            results = await cursor.fetchall()
            data_groups = []
            for [group_name] in results: data_groups.append(group_name)

            records = dict[str, adi.AdiDefinitions.AdiRecord]()
            sql = """
                SELECT
                    records.id, records.name, records_types_id, index_types,
                    cat.name AS category, primary_keys, psl_types, attributes,
                    (SELECT COUNT(1) FROM records_variables WHERE records_id=records.id) AS number_variables
                FROM records
                    LEFT JOIN records_categories AS cat ON records.records_categories_id=cat.id"""
            await cursor.execute(sql)
            results = await cursor.fetchall()
            for [id, name, record_type_id, index_types, category, primary_keys, psl_types, attributes, number_variables] in results:
                category_id = 0 if category == None else data_groups.index(category)
                if category_id < 0: category_id = 0
                records[name] = adi.AdiDefinitions.AdiRecord(id=id, name=name, record_type_id=record_type_id, index_types=index_types, category_id=category_id,
                        category=category, primary_keys=primary_keys, psl_types=psl_types,
                        attributes=attributes, number_variables=number_variables)
            self._v_records = records
            print(f"ADI Server '{self.name}' initialized in {time.time() - start_time:.2f} seconds")
        except Exception as e:
            print(f"Cannot load data from the database: {repr(e)}")
            raise
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def __LoadUnitOptionsFromUnitset(self, conn: mysql.connector.abstracts.MySQLConnectionAbstract):
        owns_conn = conn is None
        try:
            unit_type_options = await self.GetUnitsetOptions(self._v_current.unitset, conn)
            for u in unit_type_options:
                ut:adi.AdiDefinitions.UnitType = next((x for x in self._v_unit_types if x.name == u.name), None)
                if ut is None: continue
                ut_index = self._v_unit_types.index(ut)
                ut.unit_options = await self.GetUnitOptionsByUnitType(ut_index, conn)
                if ut.unit_options is None: continue
                ut.unit_option = next((x for x in ut.unit_options if x.long_name == u.unit_option.long_name), None)
                if ut.unit_option is not None:
                    ut.unit_option.id = ut.unit_options.index(ut.unit_option)
                    ut.unit_option.function_type = u.unit_option.function_type
                    ut.unit_option.arg1 = u.unit_option.arg1
                    ut.unit_option.arg2 = u.unit_option.arg2
            await self.GenerateEvent(AdiServerEventType.UNITSET_CHANGED)
        finally:
            if owns_conn and conn is not None:
                await conn.close()

    def RemoveClient(self, client):
        self._v_clients = list(filter(lambda x: x != client, self._v_clients))
        
        if client.writer_rt != None:
            self._v_clients_rt = list(filter(lambda x: x[1] != client.writer_rt, self._v_clients_rt))
            self._v_rt_monitors = list(filter(lambda x: x.adi_client != client, self._v_rt_monitors))
            client.writer_rt.close()

        self.CloseDataSetsFromClient(client)
        
        print(f"\033[1;34;40mEvt\033[0m Users list updated: \033[1;31;40mdisconnected\033[0m")

    async def ChangeWellRun(self, well:str, run_number:int, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None):
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            # If the well exists on the table "well", then get its ID. Otherwise, insert it and get the new ID.
            # if the run exists on the table "runs" belonging to that "wells_id", then get its ID. Otherwise, insert it and get the new ID.
            await cursor.execute("SELECT id FROM wells WHERE name=%s", [well])
            result = await cursor.fetchone()
            if result == None:
                await cursor.execute("INSERT INTO wells (name) VALUES (%s)", [well])
                await conn.commit()
                wells_id = cursor.lastrowid
            else: wells_id = result[0]

            await cursor.execute("SELECT id FROM runs WHERE wells_id=%s AND run_number=%s", [wells_id, run_number])
            result = await cursor.fetchone()
            if result == None:
                await cursor.execute("INSERT INTO runs (wells_id, run_number) VALUES (%s, %s)", [wells_id, run_number])
                runs_id = cursor.lastrowid
            else: runs_id = result[0]

            await cursor.execute("UPDATE current_job SET runs_id=%s WHERE id=1", [runs_id])
        except:
            pass
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetWellsList(self, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list[str]:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            wells = []
            sql = "SELECT name FROM wells ORDER BY name"
            await cursor.execute(sql)
            results = await cursor.fetchall()
            for [name] in results:
                wells.append(name)
            return wells
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetRunsList(self, well:str=None, run_alias:str=None, run_number:int=None, record:str=None, description:str=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list[int]:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            sql = """
                SELECT
                    runs.run_number,
                    runs.run_alias
                FROM
                    data_tables AS dt
                    LEFT JOIN wells ON wells.id = dt.wells_id
                    LEFT JOIN runs ON runs.id = dt.runs_id
                    LEFT JOIN records ON records.id = dt.records_id
                WHERE 1=1"""

            params = []
            if well != None:
                sql += " AND wells.name = %s"
                params.append(well)
            if run_number != None:
                sql += " AND runs.run_number = %s"
                params.append(run_number)
            if run_alias != None:
                sql += " AND runs.run_alias = %s"
                params.append(run_alias)
            if record != None:
                sql += " AND records.name = %s"
                params.append(record)
            if description != None:
                sql += " AND dt.description = %s"
                params.append(description)
            sql += """
                GROUP BY runs.run_number, runs.run_alias
                ORDER BY runs.run_number"""
            cursor = await conn.cursor()
            await cursor.execute(sql + " LIMIT 1", params)
            results = await cursor.fetchall()
            runs = []
            for [_, run_number] in results:
                runs.append(run_number)
            return runs
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetUnitTypes(self, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list[adi.AdiDefinitions.UnitType]:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            unit_types = []
            query = "SELECT name FROM unit_types ORDER BY id"
            await cursor.execute(query)
            results = await cursor.fetchall()
            for [name] in results: unit_types.append(adi.AdiDefinitions.UnitType(name=name))
            return unit_types
        except Exception as ex:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetUnitTypeName(self, unit_type_index:int, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->str:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()

            sql = """SELECT name FROM (
                SELECT (ROW_NUMBER() OVER(ORDER BY id)) - 1 AS unit_type, name
                FROM unit_types) AS ut
            WHERE ut.unit_type=%s"""

            await cursor.execute(sql, [unit_type_index])
            results = await cursor.fetchall()
            return None if len(results) != 1 else results[0][0]
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetUnitTypeById(self, unit_type_index:int, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->adi.AdiDefinitions.UnitType:
        if unit_type_index < 0 or unit_type_index >= len(self._v_unit_types): return None
        return self._v_unit_types[unit_type_index]

    async def GetUnitTypeByName(self, unit_type_name:str, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->int:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()

            sql = """SELECT unit_type FROM (
                    SELECT (ROW_NUMBER() OVER(ORDER BY id)) - 1 AS unit_type, name
                    FROM unit_types) AS ut
                    WHERE ut.name=%s"""

            await cursor.execute(sql, [unit_type_name])
            results = await cursor.fetchall()
            return None if len(results) != 1 else results[0][0]
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetUnitOptionsByUnitType(self, unit_type_index:int, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list[adi.AdiDefinitions.UnitOption]:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            unit_options = []

            sql = f"""
                    SELECT name_long, name_short FROM mc_units WHERE measurement_classes_id=
                    (
                        SELECT measurement_classes_id FROM (
                            SELECT
                                (ROW_NUMBER() OVER(ORDER BY id)) - 1 AS unit_type,
                                measurement_classes_id
                            FROM unit_types) AS ut
                        WHERE ut.unit_type=%s
                    )
                    ORDER BY id"""

            await cursor.execute(sql, [unit_type_index])
            results = await cursor.fetchall()
            for [name_long, name_short] in results: unit_options.append(adi.AdiDefinitions.UnitOption(short_name=name_short, long_name=name_long))
            return unit_options
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetUnitOptionByUnitTypeName(self, unit_type_name:str, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->adi.AdiDefinitions.UnitOption:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            # If the current unitset has an option for this unit type, return it. Otherwise,
            # the first option of that unit type from the database.
            # If the unit type does not exist, return None.
            ut:adi.AdiDefinitions.UnitType = next((ut for ut in self._v_unit_types if ut.name.lower() == unit_type_name.lower()), None)
            if ut is None: return None

            if ut.unit_option is not None: return ut.unit_option

            # No unit option selected for this unit type. Getting the first one from the database.
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            sql = f"""
                SELECT uo_id, name_long, name_short, function_type, arg1, arg2
                FROM
                (
                    SELECT
                        (ROW_NUMBER() OVER(ORDER BY id)) - 1 AS uo_id,
                        name_long, name_short, function_type, arg1, arg2
                    FROM
                        mc_units
                        LEFT JOIN measurement_classes ON measurement_classes.id = mc_units.measurement_classes_id
                        LEFT JOIN unit_types AS ut ON ut.measurement_classes_id = measurement_classes.id
                    WHERE ut.name = %s
                ) AS subquery
            """

            await cursor.execute(sql, [unit_type_name])
            results = await cursor.fetchall()
            if len(results) == 0: return None

            uo = adi.AdiDefinitions.UnitOption(id=results[0][0], short_name=results[0][2], long_name=results[0][1], function_type=results[0][3], arg1=results[0][4], arg2=results[0][5])
            return uo
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetUnitsets(self, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list[str]:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            unitsets = []

            sql = "SELECT name FROM unitsets ORDER BY name"

            await cursor.execute(sql)
            results = await cursor.fetchall()
            for [name] in results:
                unitsets.append(name)
            return unitsets
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetUnitsetOptions(self, unitset:str, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list[adi.AdiDefinitions.UnitType]:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            unit_types = []

            sql = """SELECT
                    ut.id,
                    ut.name,
                    uo.name_long,
                    uo.name_short,
                    uo.function_type,
                    uo.arg1,
                    uo.arg2
                FROM
                    unitsets_options uso
                    LEFT JOIN (
                        SELECT
                            (ROW_NUMBER() OVER(ORDER BY id)) - 1 AS unit_type,
                            id,
                            name,
                            measurement_classes_id
                        FROM
                            unit_types
                    ) ut ON ut.id=uso.unit_types_id
                    LEFT JOIN mc_units AS uo ON uo.id=uso.mc_units_id
                WHERE uso.unitsets_id=
                (SELECT id FROM unitsets WHERE name=%s)"""

            await cursor.execute(sql, [unitset])
            results = await cursor.fetchall()
            for [id, name, name_long, name_short, function_type, arg1, arg2] in results:
                ut = adi.AdiDefinitions.UnitType(id=id, name=name, unit_option=adi.AdiDefinitions.UnitOption(short_name=name_short, long_name=name_long, function_type=function_type, arg1=arg1, arg2=arg2))
                unit_types.append(ut)
            return unit_types
        except Exception as ex:
            raise ex
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetUnitConversionInfo(self, unit_type_index, unit_option_number, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->adi.AdiDefinitions.ConversionInfo:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            sql = """SELECT mc.function_type, mc.arg1, mc.arg2
                    FROM
                    (
                    SELECT
                        (ROW_NUMBER() OVER(ORDER BY mc_units.id)) - 1 AS num_option,
                        mc_units.function_type,
                        mc_units.arg1,
                        mc_units.arg2
                    FROM
                    (
                        SELECT
                            (ROW_NUMBER() OVER(ORDER BY id)) - 1 AS unit_type,
                            id,
                            measurement_classes_id
                        FROM
                            unit_types
                    ) ut
                        LEFT JOIN mc_units ON mc_units.measurement_classes_id = ut.measurement_classes_id
                    WHERE
                        ut.unit_type = %s
                    ) AS mc WHERE mc.num_option = %s"""

            await cursor.execute(sql, [unit_type_index, unit_option_number])
            results = await cursor.fetchall()
            if len(results) == 1:
                (fn_type, arg1, arg2) = results[0]
                conversion_info = adi.AdiDefinitions.ConversionInfo(fn_type, arg1, arg2)
                return conversion_info
        except Exception as ex:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetOptionsListByName(self, list_name:str, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->adi.AdiDefinitions.OptionsList:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            options_list = adi.AdiDefinitions.OptionsList(list_name)

            sql = "SELECT name FROM options_lists_options WHERE options_lists_id=(SELECT id FROM options_lists WHERE name=%s) ORDER BY id"

            await cursor.execute(sql, [list_name])
            results = await cursor.fetchall()
            for [name] in results:
                options_list.options.append(name)
            return options_list
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetVariable(self, var_name, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->adi.AdiDefinitions.AdiVariable:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            is_expanded_array = '[' in var_name
            final_var_name = var_name if not is_expanded_array else str(var_name)[0:var_name.index("[")]

            await cursor.execute("SELECT id, name, mnemonic, curve_label, mnemonic32, size, variables_types_id, unit_types_id, special, number_of_elements, number_of_decimals FROM variables WHERE name=%s", [final_var_name])
            [id, name, mnemonic, curve_label, mnemonic32, size, variables_types_id, unit_type_id, special, number_of_elements, number_of_decimals] = await cursor.fetchone()
            rv = adi.AdiDefinitions.AdiRecordVariable(
                mnemonic=mnemonic,
                curve_label=curve_label,
                mnemonic32=mnemonic32)
            v = adi.AdiDefinitions.AdiVariable(
                id=id,
                name=name,
                mnemonic=mnemonic,
                curve_label=curve_label,
                mnemonic32=mnemonic32,
                variables_types_id=adi.AdiEnums.VarType(variables_types_id),
                size=size,
                unit_type=adi.AdiDefinitions.UnitType(id=unit_type_id - 1),
                unit_type_id=unit_type_id - 1,
                special=special,
                number_of_elements=1 if is_expanded_array else number_of_elements,
                number_of_decimals=number_of_decimals,
                record_variable_data=rv)

            return v
        except Exception as ex:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetVariableDecimalsByUnitOption(self, var_name, unit_option_number, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->int:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            sql = """
                SELECT
                    v.number_of_decimals,
                    COALESCE(x.function_type, 0) function_type,
                    COALESCE(x.arg1, 0) arg1,
                    COALESCE(x.arg2, 0) arg2
                FROM
                    variables v
                    LEFT JOIN
                    (SELECT
                        (ROW_NUMBER() OVER(ORDER BY units.id)) - 1 id,
                        units.function_type,
                        units.arg1,
                        units.arg2,
                        v.id variables_id
                    FROM
                        variables v
                        LEFT JOIN unit_types ut ON v.unit_types_id=ut.id
                        LEFT JOIN measurement_classes mc ON ut.measurement_classes_id=mc.id
                        LEFT JOIN mc_units units ON units.measurement_classes_id=mc.id
                    WHERE v.name=%s) x ON v.id=x.variables_id AND x.id=%s
                WHERE v.name=%s
            """

            await cursor.execute(sql, [var_name, unit_option_number, var_name])
            results = await cursor.fetchall()
            if len(results) == 0: return 0
            else:
                [number_decimals_default, fn_type, arg1, arg2] = results[0]
                ci = adi.AdiDefinitions.ConversionInfo(fn_type, arg1, arg2)
                conversion_of_1 = adi.AdiCommands.AdiCommands.ApplyConversionInfoToValue(ci, 1)
                math_op = round(math.log10(conversion_of_1) * -1)
                final_precision = 0 if number_decimals_default + math_op < 0 else number_decimals_default + math_op
                return final_precision
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetRecordVariablesFromTable(self, well:str=None, run_number:int=None, record:str=None, description:str=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list[adi.AdiDefinitions.AdiVariable]:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            sql = """
                    SELECT dt.id
                    FROM
                        data_tables dt
                    WHERE
                        1=1"""
            params = []
            if well != None:
                sql += " AND dt.wells_id=(SELECT id FROM wells WHERE name=%s)"
                params.append(well)
            if run_number != None:
                sql += " AND dt.runs_id=(SELECT id FROM runs WHERE wells_id=dt.wells_id AND run_number=%s)"
                params.append(run_number)
            if record != None:
                sql += " AND dt.records_id=(SELECT id FROM records WHERE name=%s)"
                params.append(record)
            if description != None:
                sql += " AND dt.description=%s"
                params.append(description)

            table_number = None
            await cursor.execute(sql + " LIMIT 1", params)
            results = await cursor.fetchall()
            if len(results) == 1: table_number = results[0][0]
            if table_number == None: return None

            sql = """
                    SELECT
                        v.name, v.size, v.variables_types_id, v.unit_types_id - 1, v.special, v.number_of_elements, v.number_of_decimals, dtv.calculated, dtv.mnemonic, dtv.curve_label, dtv.mnemonic32, alg.name algorithm, ref_var.name ref_var, dtv.coeff1, dtv.coeff2, dtv.coeff3
                    FROM
                        data_tables_variables AS dtv
                        LEFT JOIN variables AS v ON dtv.variables_id = v.id
                        LEFT JOIN algorithms_calculation AS alg ON alg.id = dtv.algorithms_calculation_id
                        LEFT JOIN variables AS ref_var ON dtv.reference_variable_id = ref_var.id
                    WHERE dtv.data_tables_id = %s
                    ORDER BY dtv.id
                """
            variables = []
            await cursor.execute(sql, [table_number])
            results = await cursor.fetchall()
            offset = 0
            for (name, size, variables_types_id, unit_type_id, special, number_of_elements, number_of_decimals, calculated, mnemonic, curve_label, mnemonic32, algorithm, ref_var, coeff1, coeff2, coeff3) in results:
                rv = adi.AdiDefinitions.AdiRecordVariable(mnemonic=mnemonic, curve_label=curve_label, mnemonic32=mnemonic32, calculated=calculated,
                                algorithm=algorithm, ref_variable=ref_var, coeff1=coeff1, coeff2=coeff2, coeff3=coeff3)
                v = adi.AdiDefinitions.AdiVariable(name=name, size=size, variables_types_id=adi.AdiEnums.VarType(variables_types_id),
                                unit_type_id=unit_type_id, special=special, number_of_elements=number_of_elements,
                                number_of_decimals=number_of_decimals, record_variable_data=rv)
                if v.RequiresBytePadding(4) and offset % 4 != 0: offset += 4 - (offset % 4)
                elif v.RequiresBytePadding(8) and offset % 8 != 0: offset += 8 - (offset % 8)
                v.offset = offset
                offset += size * number_of_elements
                variables.append(v)
            return variables
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetRecordVariables(self, record_name:str=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list[adi.AdiDefinitions.AdiVariable]:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            sql = """
                SELECT v.name, v.size, v.variables_types_id, v.unit_types_id - 1, v.special, v.number_of_elements, v.number_of_decimals, rv.calculated, rv.mnemonic, rv.curve_label, rv.mnemonic32, alg.name algorithm, ref_var.name ref_var, rv.coeff1, rv.coeff2, rv.coeff3
                FROM
                    records_variables AS rv
                    LEFT JOIN variables AS v ON rv.variables_id = v.id
                    LEFT JOIN algorithms_calculation AS alg ON alg.id = rv.algorithms_calculation_id
                    LEFT JOIN variables AS ref_var ON rv.reference_variable_id = ref_var.id
                WHERE rv.records_id=(SELECT id FROM records WHERE name=%s)
                ORDER BY rv.id
            """

            variables = []
            await cursor.execute(sql, [record_name])
            results = await cursor.fetchall()
            offset = 0
            for (name, size, variables_types_id, unit_type_id, special, number_of_elements, number_of_decimals, calculated, mnemonic, curve_label, mnemonic32, algorithm, ref_var, coeff1, coeff2, coeff3) in results:
                rv = adi.AdiDefinitions.AdiRecordVariable(mnemonic=mnemonic, curve_label=curve_label, mnemonic32=mnemonic32, calculated=calculated,
                                algorithm=algorithm, ref_variable=ref_var, coeff1=coeff1, coeff2=coeff2, coeff3=coeff3)
                v = adi.AdiDefinitions.AdiVariable(name=name, size=size, variables_types_id=adi.AdiEnums.VarType(variables_types_id),
                                unit_type_id=unit_type_id, special=special, number_of_elements=number_of_elements,
                                number_of_decimals=number_of_decimals, record_variable_data=rv)
                if v.RequiresBytePadding(4) and offset % 4 != 0: offset += 4 - (offset % 4)
                elif v.RequiresBytePadding(8) and offset % 8 != 0: offset += 8 - (offset % 8)
                v.offset = offset
                offset += size * number_of_elements
                variables.append(v)
            return variables
        except Exception as ex:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetRecordAttributes(self, record_name:str=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->adi.AdiDefinitions.AdiRecord:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            record = self._v_records.get(record_name, None)
            if record != None: return record

            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            sql = "SELECT name FROM options_lists_options WHERE options_lists_id=(SELECT id FROM options_lists WHERE name='Data Group') ORDER BY id"
            await cursor.execute(sql)
            results = await cursor.fetchall()
            data_groups = []
            for [group_name] in results: data_groups.append(group_name)

            sql = """
                SELECT
                    records.id, records.name, records_types_id, index_types,
                    cat.name AS category, primary_keys, psl_types, attributes,
                    (SELECT COUNT(1) FROM records_variables WHERE records_id=records.id) AS number_variables
                FROM records
                    LEFT JOIN records_categories AS cat ON records.records_categories_id=cat.id
                WHERE records.name=%s"""
            await cursor.execute(sql, [record_name])
            results = await cursor.fetchall()
            if len(results) == 0: return None
            [id, name, record_type_id, index_types, category, primary_keys, psl_types, attributes, number_variables] = results[0]
            category_id = 0 if category == None else data_groups.index(category)
            if category_id < 0: category_id = 0
            return adi.AdiDefinitions.AdiRecord(id=id, name=name, record_type_id=record_type_id, index_types=index_types, category_id=category_id,
                    category=category, primary_keys=primary_keys, psl_types=psl_types,
                    attributes=attributes, number_variables=number_variables)
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetRunNumberByAlias(self, run_alias:str, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->int:
        owns_conn = conn is None
        run_number = None
        if str(run_alias).lower() == "well based":
            run_number = 0
        elif str(run_alias).isnumeric():
            run_number = int(run_alias)
        else:
            cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
            try:
                if conn is None: conn = await self.__GetDatabaseConnection()
                cursor = await conn.cursor()
                sql = "SELECT run_number FROM runs WHERE wells_id=(SELECT id FROM wells WHERE name=%s) AND run_alias=%s"

                await cursor.execute(sql)
                results = await cursor.fetchall()
                if len(results) == 1: run_number = results[0][0]
                if run_number == None:
                    await cursor.execute("SELECT COALESCE(MAX(run_number), %s - 1) + 1 FROM runs WHERE run_number > %s", (self.NextRunNumber, self.NextRunNumber))
                    result = await cursor.fetchone()[0]
                    self.NextRunNumber = result + 1
                    run_number = result
            except:
                pass
            finally:
                if cursor is not None:
                    await cursor.close()
                if owns_conn and conn is not None:
                    await conn.close()
        return run_number

    async def GetDataCenterInfo(self, well=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->any:
        owns_conn = conn is None
        variables = ["Customer Name", "Well Name", "Rig Name", "Field Name", "Country Name", "State Name", "County Name", "Platform", "Well Type",
            "Job Number", "Start Time", "End Time", "Spud Date", "Start Depth", "End Depth", "North Reference", "Grid Correction",
            "Magnetic Decl", "Magnetic Dip", "Magnetic Field", "Vert Sec Direct", "Latitude", "Longitude",
            "UTM X", "UTM Y", "Well Head N/S", "Well Head E/W", "Permanent Datum", "Elevation",
            "Log Meas From", "Drill Meas From", "Depth above PD", "KB Elev", "DF Elev", "GL Elev", "WD Elev",
            "DDCoordinator1", "MWDCoordinator1", "SDLADTCoor1", "SDLADTCoor2", "Time Zone", "TimeZone Label"]

        try:
            if conn is None: conn = await self.__GetDatabaseConnection()

            variables_list = []
            for var_name in variables:
                v = await self.GetVariable(var_name, conn=conn)
                if v == None: raise Exception(f"Variable '{var_name}' not found on database")
                ut = self._v_unit_types[v.unit_type_id] if len(self._v_unit_types) > v.unit_type_id and v.unit_type_id is not None else None
                uo = ut.unit_option if ut is not None and ut.unit_option is not None and ut.unit_option.id is not None else adi.AdiDefinitions.UnitOption(id=0)
                variables_list.append({"Variable": v, "UnitOption": uo })

            ds = await self.DatasetPrepare(well=well, run_number=0, record="Well Info", description="", conn=conn)
            if ds is None: return dict(zip(variables, [None] * len(variables)))

            data = await self.DataSetReadBagData(ds, variables_list, conn=conn)

            return dict(zip(variables, data))
        except Exception as ex:
            raise ex
        finally:
            if owns_conn and conn is not None:
                await conn.close()

    async def GetSperryServersStatus(self):
        return { "Iris": self.server_iris.enabled }

    async def UpdateDataCenterInfo(self, well=None, data:dict={}, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->bool:
        owns_conn = conn is None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            ds = await self.DatasetPrepare(well=well, run_number=0, record="Well Info", description="", create_if_not_exists=True, conn=conn)
            if ds == None: return False

            variables = ["Customer Name", "Well Name", "Rig Name", "Field Name", "Country Name", "State Name", "County Name", "Platform", "Well Type",
                "Job Number", "Start Time", "End Time", "Spud Date", "Start Depth", "End Depth", "North Reference", "Grid Correction",
                "Magnetic Decl", "Magnetic Dip", "Magnetic Field", "Vert Sec Direct", "Latitude", "Longitude",
                "UTM X", "UTM Y", "Well Head N/S", "Well Head E/W", "Permanent Datum", "Elevation",
                "Log Meas From", "Drill Meas From", "Depth above PD", "KB Elev", "DF Elev", "GL Elev", "WD Elev",
                "DDCoordinator1", "MWDCoordinator1", "SDLADTCoor1", "SDLADTCoor2", "Time Zone", "TimeZone Label"]
            update_variables = []
            update_values = []
            for var_name in variables:
                v = await self.GetVariable(var_name, conn=conn)
                if v == None: raise Exception(f"Variable '{var_name}' not found on database")
                ut = self._v_unit_types[v.unit_type_id] if len(self._v_unit_types) > v.unit_type_id and v.unit_type_id is not None else None
                uo = ut.unit_option if ut is not None and ut.unit_option is not None and ut.unit_option.id is not None else adi.AdiDefinitions.UnitOption(id=0)
                update_variables.append({"Variable": v, "UnitOption": uo })
                update_values.append(None if var_name not in data else data[var_name])

            await self.DataSetWriteBagData(ds, update_variables, update_values, conn=conn)
            return True
        except Exception as ex:
            raise ex
        finally:
            if owns_conn and conn is not None:
                await conn.close()

    async def QueryNumberDatasets(self, well:str=None, run_alias:str=None, run_number:int=None, record:str=None, description:str=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->bool:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            datasets = []

            sql = """
                SELECT
                    COUNT(1)
                FROM
                    data_tables AS dt
                    LEFT JOIN wells ON wells.id = dt.wells_id
                    LEFT JOIN runs ON runs.id = dt.runs_id
                    LEFT JOIN records ON records.id = dt.records_id
                WHERE 1=1"""
            params = []
            if well != None:
                sql += " AND wells.name = %s"
                params.append(well)
            if run_number != None:
                sql += " AND runs.run_number = %s"
                params.append(run_number)
            if run_alias != None:
                sql += " AND runs.run_alias = %s"
                params.append(run_alias)
            if record != None:
                sql += " AND records.name = %s"
                params.append(record)
            if description != None:
                sql += " AND dt.description = %s"
                params.append(description)

            await cursor.execute(sql, params)
            result = await cursor.fetchone()
            return result[0] > 0 if result is not None else False
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetDatasets(self, well:str=None, run_alias:str=None, run_number:int=None, record:str=None, description:str=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list[adi.AdiDefinitions.AdiDataSet]:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            datasets = []

            sql = """
                SELECT
                    wells.name AS well, runs.run_number, runs.run_alias, records.name AS record, dt.description
                FROM
                    data_tables AS dt
                    LEFT JOIN wells ON wells.id = dt.wells_id
                    LEFT JOIN runs ON runs.id = dt.runs_id
                    LEFT JOIN records ON records.id = dt.records_id
                WHERE 1=1"""
            params = []
            if well != None:
                sql += " AND wells.name = %s"
                params.append(well)
            if run_number != None:
                sql += " AND runs.run_number = %s"
                params.append(run_number)
            if run_alias != None:
                sql += " AND runs.run_alias = %s"
                params.append(run_alias)
            if record != None:
                sql += " AND records.name = %s"
                params.append(record)
            if description != None:
                sql += " AND dt.description = %s"
                params.append(description)

            await cursor.execute(sql, params)
            results = await cursor.fetchall()
            for (well, run_number, run_alias, record, description) in results:
                datasets.append(adi.AdiDefinitions.AdiDataSet(well=well, run_number=run_number, run_alias=run_alias, record=record, description=description))
            return datasets
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetRecordsListByPslTypes(self, psl_types:int, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list[str]:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            records = []

            sql = """
                    SELECT
                        name
                    FROM records
                    WHERE %s=0 OR (psl_types & %s <> 0)"""

            await cursor.execute(sql, [psl_types, psl_types])
            results = await cursor.fetchall()
            for [name] in results: records.append(name)
            return records
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def GetAllRecordsList(self)->list[adi.AdiDefinitions.AdiRecord]:
        return self._v_records

    async def GetRecordsList(self, well:str=None, run_number:int=None, record:str=None, description:str=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list[str]:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            records = []

            sql = """
                SELECT
                    DISTINCT records.name AS record
                FROM
                    data_tables AS dt
                    LEFT JOIN wells ON wells.id = dt.wells_id
                    LEFT JOIN runs ON runs.id = dt.runs_id
                    LEFT JOIN records ON records.id = dt.records_id
                WHERE 1=1"""
            params = []
            if well != None:
                sql += " AND wells.name = %s"
                params.append(well)
            if run_number != None:
                sql += " AND runs.run_number = %s"
                params.append(run_number)
            if record != None:
                sql += " AND records.name = %s"
                params.append(record)
            if description != None:
                sql += " AND dt.description = %s"
                params.append(description)

            await cursor.execute(sql, params)
            results = await cursor.fetchall()
            for [name] in results: records.append(name)
            return records
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def DatasetDelete(self, well:str=None, run_number:int=None, record:str=None, description:str=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->bool:
        owns_conn = conn is None
        if well == None or run_number == None or record == None or description == None: return False
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            sql = """SELECT dt.id
                    FROM
                        data_tables dt
                    WHERE
                        dt.wells_id=(SELECT id FROM wells WHERE name=%s)
                        AND dt.runs_id=(SELECT id FROM runs WHERE wells_id=dt.wells_id AND run_number=%s)
                        AND dt.records_id=(SELECT id FROM records WHERE name=%s)
                        AND dt.description=%s"""
            await cursor.execute(sql, [well, run_number, record, description])
            result = await cursor.fetchall()
            if len(result) == 0: return False
            else:
                table_number = result[0][0]
                await cursor.execute(f"DROP TABLE `data_{table_number}`")
                await cursor.execute(f"DROP TABLE `bag_{table_number}`")
                await cursor.execute(sql.replace("SELECT dt.id", "DELETE"), [well, run_number, record, description])
        except:
            return False
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def DatasetRename(self, well:str=None, run_number:int=None, record:str=None, description:str=None, new_well:str=None, new_run_number:int=None, new_record:str=None, new_description:str=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->bool:
        owns_conn = conn is None
        if well == None or run_number == None or record == None or description == None: return False
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            sql = """SELECT dt.id
                    FROM
                        data_tables dt
                    WHERE
                        dt.wells_id=(SELECT id FROM wells WHERE name=%s)
                        AND dt.runs_id=(SELECT id FROM runs WHERE wells_id=dt.wells_id AND run_number=%s)
                        AND dt.records_id=(SELECT id FROM records WHERE name=%s)
                        AND dt.description=%s"""
            await cursor.execute(sql, [well, run_number, record, description])
            result = await cursor.fetchall()
            if len(result) == 0: return False
            else:
                table_number = result[0][0]
                update_sql = sql.replace("SELECT dt.id", "UPDATE data_tables SET")
                update_sql += ", wells_id=(SELECT id FROM wells WHERE name=%s)" if new_well != None else ""
                update_sql += ", runs_id=(SELECT id FROM runs WHERE wells_id=dt.wells_id AND run_number=%s)" if new_run_number != None else ""
                update_sql += ", records_id=(SELECT id FROM records WHERE name=%s)" if new_record != None else ""
                update_sql += ", description=%s" if new_description != None else ""
                update_sql += " WHERE dt.id=%s"
                params = []
                if new_well != None: params.append(new_well)
                if new_run_number != None: params.append(new_run_number)
                if new_record != None: params.append(new_record)
                if new_description != None: params.append(new_description)
                params.append(table_number)
                await cursor.execute(update_sql, params)
        except:
            return False
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()
        return True

    async def DatasetCopy(self, well:str=None, run_number:int=None, record:str=None, description:str=None, new_well:str=None, new_run_number:int=None, new_record:str=None, new_description:str=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->bool:
        owns_conn = conn is None
        if well == None or run_number == None or record == None or description == None: return False
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            sql = """SELECT dt.id
                    FROM
                        data_tables dt
                    WHERE
                        dt.wells_id=(SELECT id FROM wells WHERE name=%s)
                        AND dt.runs_id=(SELECT id FROM runs WHERE wells_id=dt.wells_id AND run_number=%s)
                        AND dt.records_id=(SELECT id FROM records WHERE name=%s)
                        AND dt.description=%s"""
            await cursor.execute(sql, [well, run_number, record, description])
            result = await cursor.fetchall()
            if len(result) == 0: return False
            else:
                table_number = result[0][0]
                new_table_number = await self.__CreateDataSetTables(well=new_well, run_number=new_run_number, record=new_record, description=new_description, conn=conn)
                if new_table_number == None: return False
                await cursor.execute(f"INSERT INTO `data_{new_table_number}` SELECT * FROM `data_{table_number}`")
                await cursor.execute(f"INSERT INTO `bag_{new_table_number}` SELECT * FROM `bag_{table_number}`")
        except:
            return False
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()
        return True

    async def DatasetExists(self, well:str, run_number:int, record:str, description:str, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->bool:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            sql = """SELECT COUNT(1) AS cnt
                    FROM
                        data_tables dt
                    WHERE 1=1"""
            if well != None:
                sql += """ AND dt.wells_id=(SELECT id FROM wells WHERE name=%s)"""
            if run_number != None:
                sql += """ AND dt.runs_id=(SELECT id FROM runs WHERE wells_id=dt.wells_id AND run_number=%s)"""
            if record != None:
                sql += """ AND dt.records_id=(SELECT id FROM records WHERE name=%s)"""
            if description != None:
                sql += """ AND dt.description=%s"""
            await cursor.execute(sql, [well, run_number, record, description])
            results = await cursor.fetchone()
            return results[0] > 0
        except Exception as ex:
            raise ex
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def DatasetPrepare(self, well:str, run_number:int, record:str, description:str, truncate_data:bool=False, create_if_not_exists:bool=False, record_variables_on_create:list[adi.AdiDefinitions.AdiVariable]=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->adi.AdiDefinitions.AdiDataSetReader:
        if any(v is None for v in [well, run_number, record, description]): return None

        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            table_number = None
            sql = f"""SELECT dt.id
                    FROM
                        runs
                        LEFT JOIN data_tables dt ON dt.wells_id=runs.wells_id AND dt.runs_id=runs.id
                    WHERE
                        runs.wells_id=(SELECT id FROM wells WHERE name=%s)
                        AND runs.run_number=%s
                        AND dt.records_id=(SELECT id FROM records WHERE name=%s)
                        AND dt.description=%s"""
            await cursor.execute(sql, [well, run_number, record, description])
            results = await cursor.fetchall()
            # Doesn't exist and it was not requested to create:
            if len(results) == 0 and not create_if_not_exists:
                pass
            # Doesn't exist and it was requested to create:
            elif len(results) == 0 and create_if_not_exists:
                table_number = await self.__CreateDataSetTables(well, run_number, record, description, record_variables_on_create=record_variables_on_create, conn=conn)
                if table_number == None: return None
            # Exists and it was requested to create and WIPE
            elif len(results) == 1 and create_if_not_exists and truncate_data:
                await cursor.execute(f"TRUNCATE TABLE `z_data_{results[0][0]}`")
                await cursor.execute(f"TRUNCATE TABLE `z_bag_{results[0][0]}`")
                table_number = results[0][0]
            else: table_number = results[0][0]

            if table_number is None: return None

            adi_dataset = adi.AdiDefinitions.AdiDataSetReader(id=0, table_number=table_number, well=well, run_number=run_number, record=record, description=description)
            return adi_dataset
        except Exception as ex:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def __CreateDataSetTables(self, well=None, run_number=None, record=None, description=None, record_variables_on_create:list[adi.AdiDefinitions.AdiVariable]=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->int:
        owns_conn = conn is None
        if well == None and run_number == None and record == None and description == None:
            return None
        
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()

            # If record name does not exist, we cannot proceed
            sql = """SELECT id FROM records WHERE name=%s"""
            await cursor.execute(sql, [record])
            results = await cursor.fetchall()
            if len(results) == 0: return None
            record_id = results[0][0]

            # Checking if well and run exists. If not, create
            sql = """SELECT id FROM wells WHERE name=%s"""
            await cursor.execute(sql, [well])
            results = await cursor.fetchall()
            if len(results) == 0:
                await cursor.execute("INSERT INTO wells (name) VALUES (%s)", [well])
                well_id = cursor.lastrowid
            else: well_id = results[0][0]

            sql = """SELECT id FROM runs WHERE wells_id=%s AND run_number=%s"""
            await cursor.execute(sql, [well_id, run_number])
            results = await cursor.fetchall()
            if len(results) == 0:
                await cursor.execute("INSERT INTO runs (wells_id, run_number, run_alias) VALUES (%s, %s, %s)", [well_id, run_number, str(run_number)])
                run_id = cursor.lastrowid
            else: run_id = results[0][0]

            # First inserting the record on data_tables, to have a "table_number"
            sql = """
                INSERT INTO `data_tables` (wells_id, runs_id, records_id, description)
                VALUES (%s, %s, %s, %s);
                """
            
            table_number = None
            await cursor.execute(sql, [well_id, run_id, record_id, description])
            table_number = cursor.lastrowid
        
            # If the user informed the variables, we create a new record structure
            # If not, we copy from the default record definition
            if record_variables_on_create == None:
                sql = """
                    INSERT INTO `data_tables_variables` (data_tables_id, variables_id, calculated, mnemonic, curve_label, mnemonic32, algorithms_calculation_id, reference_variable_id, coeff1, coeff2, coeff3)
                    SELECT %s, variables_id, calculated, mnemonic, curve_label, mnemonic32, algorithms_calculation_id, reference_variable_id, coeff1, coeff2, coeff3
                    FROM records_variables
                    WHERE records_id=(SELECT id FROM records WHERE name=%s)
                """
                await cursor.execute(sql, [table_number, record])
            else:
                # Making sure all variables exist. If not, we'll create them
                # the result of the block below will be "v.id" filled in
                sql = """SELECT id FROM variables WHERE name=%s"""
                for v in record_variables_on_create:
                    await cursor.execute(sql, [v.name])
                    var_id = await cursor.fetchone()
                    if var_id == None:
                        # Creating variable...
                        sub_sql = """
                            INSERT INTO variables (name, unit_types_id, variables_types_id, special, size, number_of_elements, number_of_decimals)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """
                        await cursor.execute(sub_sql, [v.name, v.unit_type_id, v.var_type.value, v.special, v.size, v.number_of_elements, v.number_of_decimals])
                        v.id = cursor.lastrowid
                        if v.special & adi.AdiEnums.VariableSpecialHandlings.OptionList.value != 0:
                            # Looking for an Options List with same name
                            await cursor.execute("SELECT id FROM options_lists WHERE name=%s", [v.name])
                            options_list_id = await cursor.fetchone()
                            if options_list_id != None: options_list_id = options_list_id[0]
                            else:
                                await cursor.execute("INSERT INTO options_lists (name, read_only) VALUES (%s, 0)", [v.name])
                                options_list_id = cursor.lastrowid
                                for option in v.options_list.options:
                                    await cursor.execute("INSERT INTO options_lists_options (options_lists_id, name) VALUES (%s, %s)", [options_list_id, option])
                            await cursor.execute("UPDATE variables SET options_lists_id=%s WHERE id=%s", [options_list_id, v.id])
                    else: v.id = var_id[0]
                
                sql = """
                    INSERT INTO `data_tables_variables`
                        (data_tables_id, variables_id, calculated, mnemonic, curve_label, mnemonic32, algorithms_calculation_id, reference_variable_id, coeff1, coeff2, coeff3)
                    VALUES (
                        %s,
                        %s,
                        %s, %s, %s, %s,
                        (SELECT id FROM algorithms_calculation WHERE name=%s),
                        CASE WHEN %s IS NULL THEN NULL ELSE (SELECT id FROM variables WHERE name=%s) END,
                        %s, %s, %s)
                """
                for v in record_variables_on_create:
                    var_ref = None if v.record_variable_data.ref_variable == None else v.record_variable_data.ref_variable
                    val = [table_number, v.id, v.record_variable_data.calculated, v.record_variable_data.mnemonic, v.record_variable_data.curve_label, v.record_variable_data.mnemonic32,
                            v.record_variable_data.algorithm, var_ref, var_ref,
                            0 if v.record_variable_data.coeff1 == None else v.record_variable_data.coeff1,
                            0 if v.record_variable_data.coeff2 == None else v.record_variable_data.coeff2,
                            0 if v.record_variable_data.coeff3 == None else v.record_variable_data.coeff3]
                    await cursor.execute(sql, val)
            
            # Now we need the record definition, with its variables
            sql = """
                SELECT
                    v.name,
                    v.size,
                    v.number_of_elements,
                    vt.name AS var_type
                FROM
                    data_tables_variables AS dtv
                    LEFT JOIN variables AS v ON dtv.variables_id = v.id
                    LEFT JOIN variables_types AS vt ON v.variables_types_id = vt.id
                WHERE
                    dtv.data_tables_id = %s
                    AND dtv.calculated = 0
            """
            await cursor.execute(sql, [table_number])
            columns = await cursor.fetchall()
            sql = f"""
                CREATE TABLE IF NOT EXISTS `z_data_{table_number}` (
                    `z_data_{table_number}_id` INT NOT NULL AUTO_INCREMENT"""
            for (name, size, number_of_elements, var_type) in columns:
                column_type = ""
                if number_of_elements > 1: column_type = "BLOB"
                else:
                    if var_type == "ADI_VT_NONE": column_type = "TINYINT"
                    elif var_type == "ADI_VT_CHAR": column_type = "TINYINT"
                    elif var_type == "ADI_VT_UCHAR": column_type = "TINYINT UNSIGNED"
                    elif var_type == "ADI_VT_SHORT": column_type = "SMALLINT"
                    elif var_type == "ADI_VT_USHORT": column_type = "SMALLINT UNSIGNED"
                    elif var_type == "ADI_VT_INT": column_type = "INT"
                    elif var_type == "ADI_VT_UINT": column_type = "INT UNSIGNED"
                    elif var_type == "ADI_VT_FLOAT": column_type = "FLOAT"
                    elif var_type == "ADI_VT_DOUBLE": column_type = "DOUBLE PRECISION"
                    elif var_type == "ADI_VT_STRING": column_type = "VARCHAR(255)" if size < 255 else "TEXT"
                    elif var_type == "ADI_VT_PCHAR": column_type = "BLOB"
                    elif var_type == "ADI_VT_BINARY": column_type = "BLOB"
                    elif var_type == "ADI_VT_PBYTE": column_type = "BLOB"
                    else: column_type = "INT"
                sql += f", `{name}` {column_type}"
            sql += f", PRIMARY KEY (`z_data_{table_number}_id`)) ENGINE = InnoDB"
            await cursor.execute(sql)
            
            sql = f"""
                CREATE TABLE IF NOT EXISTS `z_bag_{table_number}` (
                    `id` INT NOT NULL AUTO_INCREMENT,
                    `variables_id` INT NOT NULL,
                    `data` BLOB,
                PRIMARY KEY (`id`),
                INDEX `fk_records_variables_z_bag_{table_number}_idx` (`variables_id` ASC) VISIBLE,
                CONSTRAINT `fk_records_variables_z_bag_{table_number}`
                    FOREIGN KEY (`variables_id`)
                    REFERENCES `variables` (`id`)
                    ON DELETE NO ACTION
                    ON UPDATE NO ACTION)
                ENGINE=InnoDB
            """
            await cursor.execute(sql)
        except Exception as ex:
            pass
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()
        return table_number

    async def DatasetOpen(self, identified_client:adi.AdiDefinitions.AdiProcessClientIdentification, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, variables:list, open_mode:adi.AdiEnums.RecordOpenModes, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->None:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            sql = f"SELECT COUNT(1) FROM z_data_{adi_dataset.table_number}"
            await cursor.execute(sql)
            results = await cursor.fetchone()
            if results == None: return

            sql = "SELECT v.name, v.unit_types_id - 1, dtv.calculated FROM data_tables_variables dtv LEFT JOIN variables v ON v.id = dtv.variables_id WHERE dtv.data_tables_id = %s"
            await cursor.execute(sql, [adi_dataset.table_number])
            results = await cursor.fetchall()
            
            valid_vars = []
            for i in range(len(variables)):
                var_to_add = variables[i]
                v:adi.AdiDefinitions.AdiVariable = var_to_add["Variable"]
                var_from_db = next((x for x in results if x[0] == v.name), None)
                var_to_add["IsValid"] = var_from_db != None
                if var_from_db != None:
                    v.unit_type_id = var_from_db[1]
                    v.unit_type = adi.AdiDefinitions.UnitType(id=var_from_db[1])
                    if v.record_variable_data == None: v.record_variable_data = adi.AdiDefinitions.AdiRecordVariable(calculated=var_from_db[2])
                    else: v.record_variable_data.calculated = var_from_db[2]
                valid_vars.append(var_to_add)

            adi_dataset.variables = valid_vars
            adi_dataset.is_open = True
            adi_dataset.cursor_pos = 0
            adi_dataset.open_mode_value = open_mode

            self._v_open_datasets.append(AdiOpenDataSet(identified_client=identified_client, adi_dataset=adi_dataset, open_mode=open_mode))
        except Exception as ex:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    def DataSetClose(self, identified_client:adi.AdiDefinitions.AdiProcessClientIdentification, adi_dataset:adi.AdiDefinitions.AdiDataSetReader)->None:
        try:
            open_ds = next((x for x in self._v_open_datasets if x.identified_client == identified_client and x.adi_dataset == adi_dataset), None)
            if open_ds is not None:
                self._v_open_datasets.remove(open_ds)
                adi_dataset.is_open = False
                adi_dataset.cursor_pos = 0
                adi_dataset.variables = []
        except Exception as ex:
            return None

    def CloseDataSetsFromClient(self, identified_client:adi.AdiDefinitions.AdiProcessClientIdentification)->None:
        self._v_open_datasets = list(filter(lambda x: x.identified_client != identified_client, self._v_open_datasets))

    async def DatasetListBagDataFields(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list[adi.AdiDefinitions.AdiVariable]:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            variables = []
            sql = f"""
                SELECT v.name, v.mnemonic, v.curve_label, v.size, v.variables_types_id, v.unit_types_id, v.special, v.number_of_elements, v.number_of_decimals
                FROM
                    z_bag_{adi_dataset.table_number} dt
                    LEFT JOIN variables v ON dt.variables_id=v.id
                ORDER BY dt.id"""
            await cursor.execute(sql)
            results = await cursor.fetchall()
            if len(results) == 0: return variables

            for [name, mnemonic, curve_label, size, variables_types_id, unit_type_id, special, number_of_elements, number_of_decimals] in results:
                ut = next((x for x in self._v_unit_types if x.id == unit_type_id), None) if self._v_unit_types is not None else None
                v = adi.AdiDefinitions.AdiVariable(name=name, mnemonic=mnemonic, curve_label=curve_label, size=size,
                                variables_types_id=adi.AdiEnums.VarType(variables_types_id), unit_type=ut,
                                unit_type_id=unit_type_id, special=special, number_of_elements=number_of_elements,
                                number_of_decimals=number_of_decimals, offset=0)
                variables.append(v)

            return variables
        except Exception as ex:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def DataSetWriteBagData(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, variables:list, values:list, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->bool:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            # Remember that "variables" is an array of dictionaries
            # containing the keys "Variable" and "UnitOption"
            #
            # For bag data, we don't receive anything from variable,
            # except its name, so we need to retrieve details first
            for i in range(len(variables)):
                v:adi.AdiDefinitions.AdiVariable = variables[i]["Variable"]
                
                v = await self.GetVariable(v.name, conn=conn)
                if v == None: continue
                if v.special & adi.AdiEnums.VariableSpecialHandlings.OptionList.value != 0:
                    v.options_list = await self.GetOptionsListByName(v.name, conn=conn)
                    if v.options_list == None: raise Exception(f"Options list \"{v.name}\" not found locally!")
                
                ut = v.unit_type
                uo = variables[i]["UnitOption"].id
                value = values[i]
                
                if value != None:
                    # 1 - Convert into basic types
                    value = adi.AdiCommands.AdiCommands.ConvertValueToBasicType(v, value)
                
                    # 2 - Execute unit conversions if required
                    ci = None
                    if not v.var_type in [adi.AdiEnums.VarType.ADI_VT_NONE, adi.AdiEnums.VarType.ADI_VT_STRING, adi.AdiEnums.VarType.ADI_VT_PCHAR, adi.AdiEnums.VarType.ADI_VT_BINARY, adi.AdiEnums.VarType.ADI_VT_PBYTE, adi.AdiEnums.VarType.ADI_VT_ENUM]:
                        ci = await self.GetUnitConversionInfo(unit_type_index=ut.id, unit_option_number=uo, conn=conn)
                        if ci == None: raise Exception("Invalid unit type!")
                    else: ci = adi.AdiDefinitions.ConversionInfo()

                    if v.number_of_elements > 1:
                        for k in range(len(value)):
                            if v.var_type in [adi.AdiEnums.VarType.ADI_VT_NONE, adi.AdiEnums.VarType.ADI_VT_STRING, adi.AdiEnums.VarType.ADI_VT_PCHAR, adi.AdiEnums.VarType.ADI_VT_BINARY, adi.AdiEnums.VarType.ADI_VT_PBYTE, adi.AdiEnums.VarType.ADI_VT_ENUM]:
                                value[k] = adi.AdiCommands.AdiCommands.ApplyConversionInfoToValue(ci, value[k], False)
                    else:
                        if not v.var_type in [adi.AdiEnums.VarType.ADI_VT_NONE, adi.AdiEnums.VarType.ADI_VT_STRING, adi.AdiEnums.VarType.ADI_VT_PCHAR, adi.AdiEnums.VarType.ADI_VT_BINARY, adi.AdiEnums.VarType.ADI_VT_PBYTE, adi.AdiEnums.VarType.ADI_VT_ENUM]:
                            value = adi.AdiCommands.AdiCommands.ApplyConversionInfoToValue(ci, value, False)

                # After performing all conversions...
                # If the variable is an index of an array, we need to
                # get the current data from the database, then replace
                # only the requested value
                is_expanded_array = '[' in v.name
                if is_expanded_array:
                    pattern = re.compile(r"^([^\[]+)\[([0-9]+)\]")
                    m = pattern.match(v.name)
                    var_name = m.group(1)
                    ix = int(m.group(2))
                    v = await self.GetVariable(var_name=var_name, conn=conn)
                    
                    # If user wants to write after the end of array, leave
                    if ix >= v.number_of_elements: continue
                    
                    # Getting full data, then replacing the desired index for desired value
                    full_data = await self.DataSetReadBagData(adi_dataset=adi_dataset, variables=[{"Variable": v, "UnitOption": variables[i]["UnitOption"]}], conn=conn)[0]
                    if full_data == None: full_data = [None] * v.number_of_elements
                    full_data[ix] = value

                    value = full_data
                    
                # 3 - Getting the bytes for the current data
                # [0] - Array of "values_present" for current value
                #       (if variable is array, then it will be multiple elements)
                # [1] - Content in bytes for the value
                # [2] - If this variable requires to add data to BLOB area, then
                #       blob data will be here
                [values_present, content_data, blob_data] = adi.AdiCommands.AdiCommands.BuildBytesForVariableValue(v, value)

                bytes_to_write = None
                for value_present in values_present:
                    if value_present:
                        bytes_to_write = content_data + blob_data
                        break

                #-----------------------------------------
                # Specific to BAG DATA!!!
                #-----------------------------------------
                # In the beginning we will add the "field bit test" bytes
                #
                # At the same time, if all values are null, then we set the
                # full thing as null, and it will be removed from the database
                if bytes_to_write != None:
                    # len(values_present) is same as v.number_of_elements
                    number_bytes_bit_test = math.ceil(float(len(values_present)) / 8.0)
                    fields_bit_test = bytearray([0] * number_bytes_bit_test)
                    if len(values_present) == 1 and value != None:
                        fields_bit_test[0] = 0x01
                    else:
                        for k in range(len(values_present)):
                            if value[k] != None:
                                fields_bit_test[math.floor(k / 8.0)] |= 1 << (k % 8)
                    bytes_to_write = fields_bit_test + bytes_to_write
                
                # Checking if the variable already exists in the database
                await cursor.execute(f"SELECT COUNT(1) FROM z_bag_{adi_dataset.table_number} WHERE variables_id=%s", [v.id])
                if (await cursor.fetchone())[0] == 0:
                    if bytes_to_write == None:
                        # Do nothing! We will not store NULL data
                        # cursor.execute(f"INSERT INTO z_bag_{adi_dataset.table_number} (variables_id) VALUES (%s)", [v.id])
                        pass
                    else:
                        sql = f"INSERT INTO z_bag_{adi_dataset.table_number} (variables_id, data) VALUES (%s, %s)"
                        await cursor.execute(sql, [v.id, bytes_to_write])
                else:
                    if bytes_to_write == None:
                        await cursor.execute(f"DELETE FROM z_bag_{adi_dataset.table_number} WHERE variables_id=%s", [v.id])
                    else:
                        await cursor.execute(f"UPDATE z_bag_{adi_dataset.table_number} SET data=%s WHERE variables_id=%s", [bytes_to_write, v.id])
            return True
        except Exception as ex:
            raise ex
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def DataSetReadBagData(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, variables:list, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list:
        owns_conn = conn is None
        """
        variables: list like:
        [
            { "Variable": <AdiVariable>, "UnitOption": { "id": int } },
            ...
        ]
        Returns: list of converted values in the SAME order; missing => None
        """

        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()

            # 1) Build request pairs (name, unit_idx) in order
            if not variables:
                return []

            # Build one JSON param with the request list + stable ordinal
            req = [
                {"var_name": it["Variable"].name, "unit_idx": it["UnitOption"].id, "ord": i}
                for i, it in enumerate(variables)
            ]
            req_json = json.dumps(req)

            sql = f"""
                WITH
                req AS (
                    SELECT jt.var_name, jt.unit_idx, jt.ord
                    FROM (SELECT CAST(%s AS JSON) AS js) AS p
                    JOIN JSON_TABLE(
                    p.js, '$[*]'
                    COLUMNS (
                        var_name  VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci PATH '$.var_name',
                        unit_idx  INT          PATH '$.unit_idx',
                        ord       INT          PATH '$.ord'
                    )
                    ) AS jt
                ),
                vars_req AS (
                    SELECT v.id, v.name, v.unit_types_id, v.size, r.unit_idx, r.ord
                    FROM req r
                    LEFT JOIN variables v ON v.name = r.var_name
                ),
                conv_info AS (
                    SELECT
                    vr.id AS variables_id,
                    ROW_NUMBER() OVER (PARTITION BY vr.id ORDER BY u.id) - 1 AS idx,
                    u.function_type, u.arg1, u.arg2
                    FROM vars_req vr
                    JOIN unit_types ut           ON vr.unit_types_id = ut.id
                    JOIN measurement_classes mc  ON ut.measurement_classes_id = mc.id
                    JOIN mc_units u              ON u.measurement_classes_id = mc.id
                    WHERE vr.id IS NOT NULL
                )
                SELECT
                dt.data,
                vr.size,
                COALESCE(ci.function_type, 0) AS function_type,
                COALESCE(ci.arg1, 0)          AS arg1,
                COALESCE(ci.arg2, 0)          AS arg2,
                vr.name,
                r.unit_idx,
                r.ord
                FROM req r
                LEFT JOIN vars_req vr              ON vr.ord = r.ord
                LEFT JOIN z_bag_{adi_dataset.table_number} dt  ON dt.variables_id = vr.id
                LEFT JOIN conv_info ci             ON ci.variables_id = vr.id AND ci.idx = r.unit_idx
                ORDER BY r.ord;
            """

            # 3) Execute once
            cursor = await conn.cursor(prepared=True)
            await cursor.execute(sql, (req_json,))
            rows = await cursor.fetchall()

            # Local bindings for speed
            Extract = adi.AdiCommands.AdiCommands.ExtractDataFromBuffer
            Convert = adi.AdiCommands.AdiCommands.ApplyConversionInfoToValue
            VarType = adi.AdiEnums.VarType
            ConvInfo= adi.AdiDefinitions.ConversionInfo

            non_conv = {
                VarType.ADI_VT_NONE, VarType.ADI_VT_STRING, VarType.ADI_VT_PCHAR,
                VarType.ADI_VT_BINARY, VarType.ADI_VT_PBYTE, VarType.ADI_VT_ENUM
            }

            result = [None] * len(variables)

            for (value_bytes, size, ftype, arg1, arg2, _name, _unit_idx, ord_) in rows:
                item = variables[ord_]
                v = item["Variable"]

                if value_bytes is None:
                    result[ord_] = None
                    continue

                # Save/restore fields you mutate
                prev_size, prev_off = getattr(v, "size", None), v.offset
                v.size, v.offset = size, 0

                try:
                    num_vals = v.number_of_elements
                    num_bytes_bit = math.ceil(num_vals / 8.0)
                    extracted = Extract(
                        value_bytes,
                        num_bytes_bit,
                        len(value_bytes) - num_bytes_bit,
                        0,
                        [item],
                        num_vals
                    )[0]

                    if v.var_type in non_conv:
                        value = extracted
                    elif v.special & adi.AdiEnums.VariableSpecialHandlings.OptionList.value != 0:
                        # For option list, we need to convert from option index to option value
                        ol = await self.GetOptionsListByName(v.name, conn=conn)
                        if ol is None:
                            value = extracted
                        else:
                            if v.number_of_elements > 1:
                                value = [ol.options[i] if i < len(ol.options) else None for i in extracted]
                            else:
                                value = ol.options[extracted] if extracted < len(ol.options) else None
                    else:
                        ci = ConvInfo(ftype, arg1, arg2)
                        if num_vals > 1:
                            for i in range(len(extracted)):
                                extracted[i] = Convert(ci, extracted[i])
                            value = extracted
                        else:
                            value = Convert(ci, extracted)

                finally:
                    v.size, v.offset = prev_size, prev_off

                result[ord_] = value

            return result
        except Exception as ex:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def DataSetReadBagData2(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, variables:list, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            sql = f"""
                SELECT
                    dt.data,
                    v.size,
                    COALESCE(conv_info.function_type, 0) function_type,
                    COALESCE(conv_info.arg1, 0) arg1,
                    COALESCE(conv_info.arg2, 0) arg2
                FROM
                    z_bag_{adi_dataset.table_number} dt
                    LEFT JOIN variables v ON dt.variables_id=v.id
                    LEFT JOIN
                    (SELECT
                        (ROW_NUMBER() OVER(ORDER BY units.id)) - 1 id,
                        units.function_type,
                        units.arg1,
                        units.arg2,
                        v.id variables_id
                    FROM
                        variables v
                        LEFT JOIN unit_types ut ON v.unit_types_id=ut.id
                        LEFT JOIN measurement_classes mc ON ut.measurement_classes_id=mc.id
                        LEFT JOIN mc_units units ON units.measurement_classes_id=mc.id
                    WHERE v.name=%s) conv_info ON v.id=conv_info.variables_id AND conv_info.id=%s
                WHERE
                    dt.variables_id=(SELECT id FROM variables WHERE name=%s)"""
            result_data = []
            for variable in variables:
                v:adi.AdiDefinitions.AdiVariable = variable["Variable"]
                await cursor.execute(sql, [v.name, variable["UnitOption"].id, v.name])
                result_var = await cursor.fetchall()
                value = None
                value_bytes = None if len(result_var) == 0 else result_var[0][0]
                if value_bytes != None:
                    length = len(value_bytes)

                    number_values = v.number_of_elements
                    number_bytes_bit_test = math.ceil(number_values / 8.0)

                    # Adding bit field, to be able to extract from function
                    v.size = result_var[0][1]
                    
                    # Changing temporarily the offset variable to zero, due to MySQL structure
                    var_offset = v.offset
                    v.offset = 0
                    value = adi.AdiCommands.AdiCommands.ExtractDataFromBuffer(value_bytes, number_bytes_bit_test, length - number_bytes_bit_test, 0, [variable], number_values)[0]
                    v.offset = var_offset
                    
                    ci = adi.AdiDefinitions.ConversionInfo(result_var[0][2], result_var[0][3], result_var[0][4])
                    if v.number_of_elements > 1:
                        if v.var_type in [adi.AdiEnums.VarType.ADI_VT_NONE, adi.AdiEnums.VarType.ADI_VT_STRING, adi.AdiEnums.VarType.ADI_VT_PCHAR, adi.AdiEnums.VarType.ADI_VT_BINARY, adi.AdiEnums.VarType.ADI_VT_PBYTE, adi.AdiEnums.VarType.ADI_VT_ENUM]:
                            for k in range(len(value)):
                                value[k] = adi.AdiCommands.AdiCommands.ApplyConversionInfoToValue(ci, value[k])
                    else:
                        if not v.var_type in [adi.AdiEnums.VarType.ADI_VT_NONE, adi.AdiEnums.VarType.ADI_VT_STRING, adi.AdiEnums.VarType.ADI_VT_PCHAR, adi.AdiEnums.VarType.ADI_VT_BINARY, adi.AdiEnums.VarType.ADI_VT_PBYTE, adi.AdiEnums.VarType.ADI_VT_ENUM]:
                            value = adi.AdiCommands.AdiCommands.ApplyConversionInfoToValue(ci, value)
                    
                result_data.append(value)
            return result_data
        except Exception as ex:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def DatasetRead(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, direction=1, number_lines=1, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list:
        owns_conn = conn is None
        if not adi_dataset.is_open: return None
        # Open cursor in MySQL
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            variables = adi_dataset.variables
            
            # Collecting all conversions for every variable
            conversions_info = []
            for i in range(len(variables)):
                v:adi.AdiDefinitions.AdiVariable = variables[i]["Variable"]
                if not v.var_type in [adi.AdiEnums.VarType.ADI_VT_NONE, adi.AdiEnums.VarType.ADI_VT_STRING, adi.AdiEnums.VarType.ADI_VT_PCHAR, adi.AdiEnums.VarType.ADI_VT_BINARY, adi.AdiEnums.VarType.ADI_VT_PBYTE, adi.AdiEnums.VarType.ADI_VT_ENUM]:
                    ci = await self.GetUnitConversionInfo(unit_type_index=v.unit_type.id, unit_option_number=variables[i]["UnitOption"].id, conn=conn)
                    if ci == None:
                        raise Exception("Invalid unit type!")
                    conversions_info.append(ci)
                else: conversions_info.append(adi.AdiDefinitions.ConversionInfo())
                
            # Getting variables from TABLE to avoid wrong names in the SELECT    
            sql = f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = %s"""
            cursor = await conn.cursor()
            await cursor.execute(sql, [f"z_data_{adi_dataset.table_number}"])
            result_vars = await cursor.fetchall()
            all_vars = []
            for row in result_vars: all_vars.append(row[0])

            # Listing variables
            str_variables = ""
            for i in range(len(variables)):
                v:adi.AdiDefinitions.AdiVariable = variables[i]["Variable"]
                if v.special & adi.AdiEnums.VariableSpecialHandlings.Calculable.value != 0: continue
                elif not v.name in all_vars: continue
                str_variables += f"{',' if len(str_variables) > 0 else ''} `{v.name}`"
            
            # Defining the order by fields
            str_order = ""
            if "T/D Activity" in all_vars and adi_dataset.index_type == adi.AdiEnums.IndexType.Activity:
                str_order = f"`T/D Activity`, z_data_{adi_dataset.table_number}_id"
            elif "Depth" in all_vars and adi_dataset.index_type == adi.AdiEnums.IndexType.Depth:
                str_order = f"`Depth`, z_data_{adi_dataset.table_number}_id"
            elif "Time & Date" in all_vars and adi_dataset.index_type == adi.AdiEnums.IndexType.Time:
                str_order = f"`Time & Date`, z_data_{adi_dataset.table_number}_id"
            else: str_order = f"z_data_{adi_dataset.table_number}_id"
                
            # Defining the index position
            start_index = 0 if adi_dataset.cursor_pos == None else adi_dataset.cursor_pos
            if direction == -1:
                if start_index - number_lines >= 0: start_index = start_index - number_lines
                else:
                    number_lines = start_index
                    start_index = 0
                
            sql = f"""SELECT {str_variables} FROM z_data_{adi_dataset.table_number}
                ORDER BY {str_order}
                LIMIT {start_index}, {number_lines}
            """
            await cursor.execute(sql)
            lines_read = await cursor.fetchall()

            lines_to_return = []
            for line in lines_read:
                row_data = []

                # Remember that "variables" is an array of dictionaries
                # containing the keys "Variable" and "UnitOption"
                ix_col = 0
                for i in range(len(variables)):
                    v:adi.AdiDefinitions.AdiVariable = variables[i]["Variable"]
                    
                    if v.special & adi.AdiEnums.VariableSpecialHandlings.Calculable.value != 0:
                        # TODO - Perform calculations
                        value = None
                    elif not v.name in all_vars:
                        value = None
                    else:
                        value = line[ix_col]
                        ix_col += 1

                    if value != None:
                        # 1 - For complex structures, converting the bytes to data
                        if v.number_of_elements > 1 or v.var_type in [adi.AdiEnums.VarType.ADI_VT_PCHAR, adi.AdiEnums.VarType.ADI_VT_BINARY, adi.AdiEnums.VarType.ADI_VT_PBYTE]:
                            full_bytes = value + b'1'
                            var_offset = v.offset
                            v.offset = 0
                            value = adi.AdiCommands.AdiCommands.ExtractDataFromBuffer(full_bytes, 0, len(value) - 1, len(value), [variables[i]], 1)
                            if value != None and len(value) == 1: value = value[0]
                            v.offset = var_offset

                        # 2 - Execute unit conversions if required
                        if conversions_info[i] != None:
                            if value != None and v.number_of_elements > 1:
                                for k in range(len(value)):
                                    value[k] = adi.AdiCommands.AdiCommands.ApplyConversionInfoToValue(conversions_info[i], value[k], True)
                            elif value != None:
                                value = adi.AdiCommands.AdiCommands.ApplyConversionInfoToValue(conversions_info[i], value, True)

                    # Adding the value for the row data
                    row_data.append(value)

                # cursor.execute(sql, row_data)
                lines_to_return.append(row_data)

            # Updating the cursor position
            adi_dataset.cursor_pos = start_index if direction < 0 else start_index + len(lines_read)
        
            return lines_to_return

        except Exception as ex:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def DatasetWrite(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, write_modes:adi.AdiEnums.DataSetWriteModes, lines_to_write:list, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->bool:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None

        if adi_dataset.open_mode_value & adi.AdiEnums.RecordOpenModes.PostRealTimeData.value != 0:
            # Only report real time data to RT Monitors
            await self.ReportRealtimeData(adi_dataset, lines_to_write)
            return True

        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            variables = adi_dataset.variables

            # Collecting all conversions for every variable
            conversions_info = []
            for i in range(len(variables)):
                v:adi.AdiDefinitions.AdiVariable = variables[i]["Variable"]
                if not v.var_type in [adi.AdiEnums.VarType.ADI_VT_NONE, adi.AdiEnums.VarType.ADI_VT_STRING, adi.AdiEnums.VarType.ADI_VT_PCHAR, adi.AdiEnums.VarType.ADI_VT_BINARY, adi.AdiEnums.VarType.ADI_VT_PBYTE, adi.AdiEnums.VarType.ADI_VT_ENUM]:
                    ci = await self.GetUnitConversionInfo(unit_type_index=v.unit_type.id, unit_option_number=variables[i]["UnitOption"].id, conn=conn)
                    if ci == None: raise Exception("Invalid unit type!")
                    conversions_info.append(ci)
                else: conversions_info.append(adi.AdiDefinitions.ConversionInfo())

            mysql_lines_to_write = []
            for line in lines_to_write:
                row_data = []

                # Remember that "variables" is an array of dictionaries
                # containing the keys "Variable" and "UnitOption"
                for i in range(len(variables)):
                    v:adi.AdiDefinitions.AdiVariable = variables[i]["Variable"]
                    value = line[i]

                    if value != None:
                        # 1 - Convert into basic types
                        value = adi.AdiCommands.AdiCommands.ConvertValueToBasicType(v, value)

                        # 2 - Execute unit conversions if required
                        if value != None and v.number_of_elements > 1:
                            for k in range(len(value)):
                                value[k] = adi.AdiCommands.AdiCommands.ApplyConversionInfoToValue(conversions_info[i], value[k], False)
                        elif value != None:
                            value = adi.AdiCommands.AdiCommands.ApplyConversionInfoToValue(conversions_info[i], value, False)

                        # 3 - For complex structures, getting the bytes for the current data
                        # [0] - Array of "values_present" for current value
                        #       (if variable is array, then it will be multiple elements)
                        # [1] - Content in bytes for the value
                        # [2] - If this variable requires to add data to BLOB area, then
                        #       blob data will be here
                        if v.number_of_elements > 1 or v.var_type in [adi.AdiEnums.VarType.ADI_VT_PCHAR, adi.AdiEnums.VarType.ADI_VT_BINARY, adi.AdiEnums.VarType.ADI_VT_PBYTE]:
                            result_data = adi.AdiCommands.AdiCommands.BuildBytesForVariableValue(v, value)
                            if len(result_data[0]) == 1 and result_data[0][0] == False:
                                # cursor.execute(f"INSERT INTO z_bag_{self.adi_dataset.table_number} (variables_id) VALUES (%s)", [v.id])
                                value = None
                            else:
                                # sql = f"INSERT INTO z_bag_{self.adi_dataset.table_number} (variables_id, data) VALUES ((SELECT id FROM variables WHERE name=%s), %s)"
                                value = result_data[1] + result_data[2]
                                # cursor.execute(sql, (v.name, final_bytes))
                    
                    # Adding the value for the row data
                    row_data.append(value)

                # cursor.execute(sql, row_data)
                mysql_lines_to_write.append(row_data)

            if len(mysql_lines_to_write) > 0:
                sql = f"INSERT INTO z_data_{adi_dataset.table_number} ("
                for i in range(len(variables)):
                    sql += f"{',' if i != 0 else ''} `{variables[i]['Variable'].name}`"
                sql += f") VALUES ({', '.join(['%s'] * len(variables))})"

                cursor = await conn.cursor()
                await cursor.executemany(sql, mysql_lines_to_write)

                if adi.AdiEnums.DataSetWriteModes.PostRealTimeData in write_modes:
                    try:
                        await self.ReportRealtimeData(adi_dataset, lines_to_write)
                    except: pass

            return True
        except Exception as ex:
            return False
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def DatasetGetNumberOfRecords(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->int:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            sql = f"SELECT COUNT(1) FROM z_data_{adi_dataset.table_number}"
            await cursor.execute(sql)
            results = await cursor.fetchall()
            return None if len(results) == 0 else results[0][0]
        except:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def DatasetSetIndexPosition(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, mode_seek:adi.AdiEnums.SeekPositionMode=None, record_number:int=None, value_search=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->bool:
        owns_conn = conn is None
        # Logic is:
        # Put the position exactly before the record which is
        # greater or equal to the searched value
        
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            if adi_dataset == None or not adi_dataset.is_open: return False
            if mode_seek == adi.AdiEnums.SeekPositionMode.Start: adi_dataset.cursor_pos = 0
            elif mode_seek == adi.AdiEnums.SeekPositionMode.End:
                number_records = await self.DatasetGetNumberOfRecords(adi_dataset=adi_dataset, conn=conn)
                if number_records != None: adi_dataset.cursor_pos = number_records
            elif mode_seek == adi.AdiEnums.SeekPositionMode.RecordNumber: adi_dataset.cursor_pos = record_number
            elif mode_seek == adi.AdiEnums.SeekPositionMode.Depth or mode_seek == adi.AdiEnums.SeekPositionMode.Time:
                field_name = "`Depth`" if mode_seek == adi.AdiEnums.SeekPositionMode.Depth else "`Time & Date`"
                index_order = "`Depth` ASC, `Time & Date` ASC" if adi_dataset.index_type ==  adi.AdiEnums.IndexType.Depth \
                    else "`Time & Date` ASC, `Depth` ASC" if adi_dataset.index_type ==  adi.AdiEnums.IndexType.Time \
                    else "`T/D Activity`, `Time & Date` ASC, `Depth` ASC"
                tolerance = 2 if mode_seek == adi.AdiEnums.SeekPositionMode.Depth else 1
                
                sql = f"""SELECT X.ROW_NUM
                        FROM (
                            SELECT
                                ABS({field_name} - %s) DIFF,
                                ROW_NUMBER() OVER (ORDER BY {index_order}) AS ROW_NUM
                            FROM z_data_{adi_dataset.table_number}
                        ) X
                        WHERE X.DIFF < %s
                        ORDER BY X.ROW_NUM
                        LIMIT 1"""
                await cursor.execute(sql, [value_search, tolerance])
                results = await cursor.fetchall()
                if len(results) == 1: adi_dataset.cursor_pos = results[0][0]
                else:
                    number_records = await self.DatasetGetNumberOfRecords(adi_dataset=adi_dataset, conn=conn)
                    if number_records != None: adi_dataset.cursor_pos = number_records
                    else: adi_dataset.cursor_pos = 0
            return True
        except Exception as ex:
            return False
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def DatasetSearchValue(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, variable, search_direction:adi.AdiEnums.SearchDirection, start_pos:int, end_pos:int, start_value, end_value, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->int:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            v = await self.GetVariable(variable["Variable"].name, conn=conn)
            unit_option = variable["UnitOption"]
            ci = await self.GetUnitConversionInfo(unit_type_index=v.unit_type_id, unit_option_number=unit_option.id, conn=conn)
            start_value = adi.AdiCommands.AdiCommands.ConvertValueToBasicType(v, start_value)
            start_value = adi.AdiCommands.AdiCommands.ApplyConversionInfoToValue(ci, start_value, False)
            end_value = adi.AdiCommands.AdiCommands.ConvertValueToBasicType(v, end_value)
            end_value = adi.AdiCommands.AdiCommands.ApplyConversionInfoToValue(ci, end_value, False)
            
            # Logic is:
            # Put the position exactly before (or after if direction is oposite) the record which is
            # lies between the start_value and end_value
            field_name = f"`{v.name}`"
            order = "ASC" if search_direction == adi.AdiEnums.SearchDirection.Down else "DESC"
            index_order = f"`{v.name}` {order}"
            
            sql = f"""SELECT X.ROW_NUM
                    FROM (
                        SELECT
                            {field_name},
                            ROW_NUMBER() OVER (ORDER BY {index_order}) AS ROW_NUM
                        FROM z_data_{adi_dataset.table_number}
                    ) X
                    WHERE
                        {field_name} >= %s AND {field_name} <= %s
                        AND X.ROW_NUM >= %s AND (X.ROW_NUM <= %s OR %s = 0)
                    ORDER BY X.ROW_NUM
                    LIMIT 1"""
            cursor = await conn.cursor()
            await cursor.execute(sql, [start_value, end_value, start_pos, end_pos, end_pos])
            results = await cursor.fetchall()
            if len(results) == 1: adi_dataset.cursor_pos = results[0][0]
            else:
                number_records = await self.DatasetGetNumberOfRecords(adi_dataset=adi_dataset, conn=conn)
                if number_records != None: adi_dataset.cursor_pos = number_records
                else: adi_dataset.cursor_pos = 0
                return -1
            return adi_dataset.cursor_pos
        except Exception as ex:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def DatasetReadComments(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->str:
        owns_conn = conn is None
        # Not implemented!
        return None

    async def DatasetAppendComments(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, comments:str, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->bool:
        owns_conn = conn is None
        # Not implemented!
        return True

    async def DatasetReadFile(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, entry_name:str, start_position:int=0, number_bytes:int=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->adi.AdiDefinitions.AdiDataSetFile:
        owns_conn = conn is None
        '''
        Returns an object with properties file_size and data filled in, or None if file does not exist
        '''
        # Not implemented!
        return None

    async def DataSetGetFilesList(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list[adi.AdiDefinitions.AdiDataSetFile]:
        owns_conn = conn is None
        return []

    async def DataSetWriteVectorAttributes(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, variables:list[adi.AdiDefinitions.AdiVariable], conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->bool:
        owns_conn = conn is None
        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()

            sql="""
                INSERT INTO variables_vector_attributes (data_tables_id, variables_id, unit_types_id, variables_vector_types_id, bin_start, bin_end)
                SELECT dt.id,
                    (SELECT id FROM variables WHERE name=%s),
                    (SELECT id FROM unit_types WHERE name=%s),
                    %s, %s, %s
                FROM
                    data_tables AS dt
                    LEFT JOIN wells AS w ON dt.wells_id=w.id
                    LEFT JOIN runs ON dt.runs_id=runs.id
                    LEFT JOIN records ON dt.records_id=records.id
                WHERE
                    dt.wells_id=(SELECT id FROM wells WHERE name=%s)
                    AND runs.run_alias=%s
                    AND records.name=%s
                    AND description=%s"""

            await conn.start_transaction()
            for v in variables:
                await cursor.execute(sql, (v.name, v.vector_unit_type.name, v.vector_var_type.value, v.vector_bin_start, v.vector_bin_end, adi_dataset.well, adi_dataset.run_alias, adi_dataset.record, adi_dataset.description))
            await conn.commit()
        except Exception as ex:
            if owns_conn and conn is not None:
                await conn.rollback()
            return False
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def DataSetReadVectorAttributes(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, variables:list, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->list:
        owns_conn = conn is None
        raise Exception("Not implemented!")

    async def DataSetPrepareComplex(self, keys=None, filter_activities_per_key=None, variables=None, coercion_types=None, iv=None, every_data_point=False, output_resolution=None, vars_key_indexes=None, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->bool:
        owns_conn = conn is None
        return False

    async def AddRTMonitor(self, rt_monitor:adi.AdiDefinitions.AdiRTMonitor)->bool:
        # All requested variables should be loaded, so we have all the information
        # to be able to report real time data to the monitor when it is required.
        for variable in rt_monitor.variables_list:
            v:adi.AdiDefinitions.AdiVariable = await self.GetVariable(variable["Variable"].name)
            if v == None or v.size != variable["Variable"].size: return False
            v.unit_type = await self.GetUnitTypeById(v.unit_type_id)
            v.offset = variable["Variable"].offset
            variable["Variable"] = v
            if variable["UnitOption"] != None and variable["UnitOption"].id != None and variable["UnitOption"].id >= 0 and variable["UnitOption"].id < len(v.unit_type.unit_options):
                variable["UnitOption"] = v.unit_type.unit_options[variable["UnitOption"].id]
            else:
                variable["UnitOption"] = v.unit_type.unit_option
        self._v_rt_monitors.append(rt_monitor)
        return True

    async def StopAllRtMonitorFromClient(self, adi_client)->bool:
        self._v_rt_monitors = list(filter(lambda x: x.adi_client != adi_client, self._v_rt_monitors))
        return True

    async def ReportRealtimeData(self, adi_dataset:adi.AdiDefinitions.AdiDataSetReader, lines_to_write:list)->bool:
        for rt_monitor in self._v_rt_monitors:
            if rt_monitor.well == adi_dataset.well and rt_monitor.run_number == adi_dataset.run_number and rt_monitor.record == adi_dataset.record and rt_monitor.description == adi_dataset.description:
                try:
                    await rt_monitor.ReportRealtimeData(adi_dataset, lines_to_write)
                except: pass
        return True

    async def GetUnitsetFile(self, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->str:
        owns_conn = conn is None
        if self._v_current == None or self._v_current.unitset == None: return None
        if not self._v_running: return None

        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()

            sql = """
            SELECT
                ut.unit_type_index,
                ut.name,
                mu.unit_option_number,
                mu.name_long,
                mu.name_short
            FROM
                current_job cj
                JOIN unitsets_options AS uo ON cj.unitsets_id=uo.unitsets_id
                JOIN (SELECT id, (ROW_NUMBER() OVER(ORDER BY id)) - 1 AS unit_type_index, name, measurement_classes_id FROM unit_types) AS ut ON uo.unit_types_id=ut.id
                LEFT JOIN LATERAL (SELECT id, (ROW_NUMBER() OVER(ORDER BY mc_units.id)) - 1 AS unit_option_number, name_long, name_short FROM mc_units WHERE measurement_classes_id=ut.measurement_classes_id) mu ON mu.id=uo.mc_units_id
            WHERE cj.id=1"""

            await cursor.execute(sql)
            results = await cursor.fetchall()

            contents = f"#Number of Unit Types\n{len(results)}\n# Unit Type Number; Unit Type; Unit Option Number; Option Long Name; Option Short Name\n"
            for row in results:
                contents += f"{row[0]:>3}; {row[1]:>16}; {row[2]:>2}; {row[3]:>16}; {row[4]:>5};\n"

            return contents
        except Exception as ex:
            return None
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def UploadUnitsetFile(self, filename:str, file_contents:str, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->bool:
        owns_conn = conn is None
        if not self._v_running: return False

        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            lines = file_contents.splitlines()
            if len(lines) < 4 \
                or not lines[0].lower().startswith("#number") \
                or not lines[1].isdigit() \
                or not lines[2].startswith("#"):
                raise Exception("Invalid file format!")

            # First line is number of unit types
            num_unit_types = int(lines[1].strip())
            if num_unit_types <= 0: raise Exception("Invalid file format!")

            unit_types = []
            for i in range(3, num_unit_types + 3):
                parts = [p.strip() for p in lines[i].split(";")]
                if len(parts) < 5 or len(parts) > 6: raise Exception("Invalid file format!")
                unit_type_index = int(parts[0])
                unit_type_name = parts[1]
                unit_option_number = int(parts[2])
                option_long_name = parts[3]
                option_short_name = parts[4]
                unit_types.append({
                    "unit_type_index": unit_type_index,
                    "unit_type_name": unit_type_name,
                    "unit_option_number": unit_option_number,
                    "option_long_name": option_long_name,
                    "option_short_name": option_short_name
                })

            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            await conn.start_transaction()

            # Retrieving unitset name from filename
            filename_with_extension = os.path.basename(filename)
            filename_without_extension = os.path.splitext(filename_with_extension)[0]
            unitset_name = filename_without_extension

            # Checking if there is a unitset with the requested name
            await cursor.execute("SELECT id FROM unitsets WHERE name=%s", (unitset_name,))

            result = await cursor.fetchall()
            if len(result) == 0:
                # Inserting new unitset
                await cursor.execute("INSERT INTO unitsets (name) VALUES (%s)", (unitset_name,))
                unitsets_id = cursor.lastrowid
            else:
                unitsets_id = result[0][0]
            
                # Deleting all current options
                await cursor.execute("DELETE FROM unitsets_options uo WHERE uo.unitsets_id=%s", (unitsets_id,))


            await cursor.execute("SELECT id, name FROM unitsets")
            all_unitsets = await cursor.fetchall()

            # Inserting new options
            # sql = """
            #     INSERT INTO unitsets_options (unitsets_id, unit_types_id, mc_units_id)
            #     SELECT
            #         %s AS unitsets_id,
            #         ut.id,
            #         mu.id AS mc_units_id
            #     FROM
            #         (SELECT id, measurement_classes_id, (ROW_NUMBER() OVER(ORDER BY id)) - 1 AS unit_type_index, name FROM unit_types) AS ut
            #         LEFT JOIN LATERAL (SELECT id, measurement_classes_id, (ROW_NUMBER() OVER(ORDER BY id)) - 1 AS unit_option_number, name_long, name_short FROM mc_units WHERE measurement_classes_id=ut.measurement_classes_id) mu ON mu.measurement_classes_id=ut.measurement_classes_id
            #     WHERE
            #         ut.unit_type_index=%s
            #         AND ut.name=%s
            #         AND mu.unit_option_number=%s
            #         AND mu.name_long=%s
            #         AND mu.name_short=%s"""
            sql = """
                INSERT INTO unitsets_options (unitsets_id, unit_types_id, mc_units_id)
                SELECT
                    %s AS unitsets_id,
                    ut.id,
                    mu.id AS mc_units_id
                FROM
                    (SELECT id, measurement_classes_id, (ROW_NUMBER() OVER(ORDER BY id)) - 1 AS unit_type_index, name FROM unit_types) AS ut
                    LEFT JOIN LATERAL (SELECT id, measurement_classes_id, (ROW_NUMBER() OVER(ORDER BY id)) - 1 AS unit_option_number, name_long, name_short FROM mc_units WHERE measurement_classes_id=ut.measurement_classes_id) mu ON mu.measurement_classes_id=ut.measurement_classes_id
                WHERE
                    ut.name=%s
                    AND mu.unit_option_number=%s
                    AND mu.name_long=%s
                    AND mu.name_short=%s"""
            for ut in unit_types:
                await cursor.execute(sql, (unitsets_id, ut["unit_type_name"], ut["unit_option_number"], ut["option_long_name"], ut["option_short_name"]))

            # Changing the current unitset for the ADI Server
            await cursor.execute("UPDATE current_job SET unitsets_id=%s WHERE id=1", (unitsets_id,))

            await conn.commit()

            self._v_current.unitset = unitset_name
            await self.__LoadUnitOptionsFromUnitset(conn)
            await self._v_control.GenerateEvent(rigs_control.rigs.EventType.ADI_SERVERS_CHANGED)

            return True
        except Exception as ex:
            raise ex
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def ChangeUnitset(self, unitset_name:str, conn: mysql.connector.abstracts.MySQLConnectionAbstract = None)->bool:
        owns_conn = conn is None
        if not self._v_running: return False

        cursor: mysql.connector.abstracts.MySQLCursorAbstract = None
        try:
            if conn is None: conn = await self.__GetDatabaseConnection()
            cursor = await conn.cursor()
            await cursor.execute("SELECT id, name FROM unitsets WHERE name=%s", (unitset_name,))
            result = await cursor.fetchall()
            if len(result) == 0: return False
            unitsets_id = result[0][0]
            await cursor.execute("UPDATE current_job SET unitsets_id=%s WHERE id=1", (unitsets_id,))
            self._v_current.unitset = result[0][1]
            await self.__LoadUnitOptionsFromUnitset(conn)
            return True
        except Exception as ex:
            return False
        finally:
            if cursor is not None:
                await cursor.close()
            if owns_conn and conn is not None:
                await conn.close()

    async def TestDataTransfer(self, adi_data_transfer:adi.AdiDefinitions.AdiDataTransfer)->bool:
        if adi_data_transfer == None: raise Exception("Invalid data transfer!")
        if adi_data_transfer.remote_host == None or adi_data_transfer.remote_host.strip() == "": raise Exception("Invalid remote host!")
        if adi_data_transfer.adi_type not in [adi.AdiEnums.DataTransferAdiType.InsiteAdi, adi.AdiEnums.DataTransferAdiType.LocalAdi]: raise Exception("Invalid ADI type!")
        if adi_data_transfer.direction not in [adi.AdiEnums.DataTransferDirection.Upload, adi.AdiEnums.DataTransferDirection.Download]: raise Exception("Invalid direction!")

        try:
            import adi.AdiClientToRemote
            adi_client = adi.AdiClientToRemote.AdiClientToRemote(loop=self._v_loop, host=adi_data_transfer.remote_host, enabled=True, realtime=False)
            for _ in range(50):
                if adi_client.connection_state == adi.AdiClientToRemote.ConnectionState.CONNECTED: break
                await asyncio.sleep(0.1)
            success = adi_client.connection_state == adi.AdiClientToRemote.ConnectionState.CONNECTED
            await adi_client.Stop()
            return success
        except Exception as ex:
            raise ex

    async def GetDataTransfers(self)->list[adi.AdiDefinitions.AdiDataTransfer]:
        curr_data_transfers = []
        # Testing data only
        fake_transfer = adi.AdiDefinitions.AdiDataTransfer(
            remote_host="10.10.10.10",
            adi_type=adi.AdiEnums.DataTransferAdiType.InsiteAdi,
            direction=adi.AdiEnums.DataTransferDirection.Upload,
            rt_stored_type=adi.AdiEnums.DataTransferRtStoredType.StoredOnly,
            datasets_type=adi.AdiEnums.DataTransferDatasetsType.ActiveWell,
            datasets_list=None,
            records_exception_list=None
        )
        fake_transfer.enabled = False
        curr_data_transfers.append(fake_transfer)
        return curr_data_transfers

    async def AddDataTransfer(self, adi_data_transfer:adi.AdiDefinitions.AdiDataTransfer)->bool:
        if adi_data_transfer == None: raise Exception("Invalid data transfer!")
        if adi_data_transfer.remote_host == None or adi_data_transfer.remote_host.strip() == "": raise Exception("Invalid remote host!")
        if not isinstance(adi_data_transfer.adi_type, adi.AdiEnums.DataTransferAdiType): raise Exception("Invalid ADI type!")
        if not isinstance(adi_data_transfer.direction, adi.AdiEnums.DataTransferDirection): raise Exception("Invalid direction!")
        if not isinstance(adi_data_transfer.rt_stored_type, adi.AdiEnums.DataTransferRtStoredType): raise Exception("Invalid RT/Stored type!")
        if not isinstance(adi_data_transfer.datasets_type, adi.AdiEnums.DataTransferDatasetsType): raise Exception("Invalid datasets type!")
        if adi_data_transfer.datasets_type == adi.AdiEnums.DataTransferDatasetsType.SelectedDatasets and (adi_data_transfer.datasets_list == None or len(adi_data_transfer.datasets_list) == 0): raise Exception("Invalid datasets!")
        self.data_transfers.append(adi_data_transfer)
        return True

    def GetJsonObject(self):
        return {
            "Id": self.id,
            "Name": self.name,
            "Online": False if self == None else self.enabled,
            "DBName": self.db_name,
            "ListenToTcp": False if self == None else self.listen_to_tcp,
            "Well": None if self._v_current == None else self._v_current.well,
            "Run": None if self._v_current == None else self._v_current.run,
            "Activity": None if self._v_current == None or self._v_current.activity > len(self._v_activities) - 1 else self._v_activities[self._v_current.activity],
            "BitDepth": None if self._v_current == None else self._v_current.bit_depth,
            "HoleDepth": None if self._v_current == None else self._v_current.hole_depth,
            "UnitSet": None if self._v_current == None else self._v_current.unitset
        }
