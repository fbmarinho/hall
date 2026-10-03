from __future__ import annotations
import asyncio
from collections import defaultdict, deque
from datetime import datetime
from enum import Enum
import os
import socket
import time
from typing import TYPE_CHECKING, Tuple

from adi.AdiCommands import AdiCommands
from adi.AdiDefinitions import AdiDataSetReader, AdiProcessClientIdentification, AdiVariable, UnitOption, UnitType
from adi.AdiEnums import RecordOpenModes, DataSetWriteModes
if TYPE_CHECKING:
    from adi.AdiServer import AdiServer
import adi.AdiDefinitions
from adi.EventEmitter import EventEmitter

class IrisVariable:
    def __init__(self, name:str, unit_type_name:str, value:any=None):
        self.name = name
        self.unit_type_name = unit_type_name
        self.value = value

    def SetValue(self, value:any, unit_option:UnitOption=None):
        if unit_option is not None:
            self.value = AdiCommands.ApplyConversionInfoToValue(unit_option, value, False)
        else:
            self.value = value

    def to_dict(self, unit_option:UnitOption=None):
        return {
            "Name": self.name,
            "Unit": None if unit_option is None else unit_option.short_name,
            "Value": self.value if unit_option is None else AdiCommands.ApplyConversionInfoToValue(unit_option, self.value, True)
        }

class IrisRecordMonitoredType(Enum):
    Time = 1
    DepthWhileDrilling = 2

class IrisAveragingType(Enum):
    Mean = 1
    StDev = 2
    Max = 3
    Min = 4
    First = 5
    Last = 6

class IrisSlipStatus(Enum):
    N_A = 0
    NoSlip = 1
    Slip = 2

class IrisBottomStatus(Enum):
    N_A = 0
    OffBottom = 1
    OnBottom = 2

class IrisCirculatingStatus(Enum):
    N_A = 0
    NotCirculating = 1
    Circulating = 2

class IrisRecordMonitored:
    def __init__(self, record_name:str, description:str, monitored_type:IrisRecordMonitoredType, interval_cycle:float):
        self.record_name = record_name
        self.description = description
        self.monitored_type = monitored_type
        self.interval_cycle = interval_cycle
        self.last_generated_time:float = 0.0
        self.variables_monitored:list[IrisRecordVariableMonitored] = []

    def copy(self):
        new_copy = IrisRecordMonitored(self.record_name, self.description, self.monitored_type, self.interval_cycle)
        new_copy.last_generated_time = self.last_generated_time
        new_copy.variables_monitored = [v.copy() for v in self.variables_monitored]
        return new_copy

    def to_dict(self):
        return {
            "RecordName": self.record_name,
            "Description": self.description,
            "MonitoredType": self.monitored_type.name,
            "IntervalCycle": self.interval_cycle,
            "VariablesMonitored": [v.to_dict() for v in self.variables_monitored]
        }

    @classmethod
    def from_dict(cls, data: dict):
        record = cls(
            record_name=data["RecordName"],
            description=data["Description"],
            monitored_type=IrisRecordMonitoredType[data["MonitoredType"]],
            interval_cycle=float(data["IntervalCycle"])
        )
        record.last_generated_time = float(data.get("LastGeneratedTime", 0.0))
        record.variables_monitored = [
            IrisRecordVariableMonitored.from_dict(v.__dict__)
            for v in data.get("VariablesMonitored", [])
        ]
        return record

    def GenerateNewLine(self, current_time:datetime, iris_variables:list[IrisVariable], iris_variable_values_history:dict[str, list[HistoricalVariableValue]]) -> list[IrisRecordDataLine]:
        current_depth = next((v.value for v in iris_variables if v.name == "Depth"), None)
        current_activity = next((v.value for v in iris_variables if v.name == "T/D Activity"), None)
        # variable_values:list = [
        #     current_time,       # [0] = Time & Date
        #     current_depth,      # [1] = Depth
        #     current_activity    # [2] = T/D Activity
        # ]
        variable_values:list = []
        for variable in self.variables_monitored:
            values_history = [] if variable.variable_name not in iris_variable_values_history else iris_variable_values_history[variable.variable_name]
            values_history = [v.value for v in values_history if v.value is not None and (
                (
                    (self.monitored_type == IrisRecordMonitoredType.Time and (current_time - v.timestamp).total_seconds() <= self.interval_cycle)
                    or
                    (self.monitored_type == IrisRecordMonitoredType.DepthWhileDrilling and abs(v.depth - current_depth) <= self.interval_cycle)
                )
                and
                (
                    (variable.slips_status == IrisSlipStatus.N_A)
                    or
                    (variable.slips_status == IrisSlipStatus.Slip and v.slips_status == IrisSlipStatus.Slip)
                    or
                    (variable.slips_status == IrisSlipStatus.NoSlip and v.slips_status == IrisSlipStatus.NoSlip)
                )
                and
                (
                    (variable.bottom_status == IrisBottomStatus.N_A)
                    or
                    (variable.bottom_status == IrisBottomStatus.OnBottom and v.bottom_status == IrisBottomStatus.OnBottom)
                    or
                    (variable.bottom_status == IrisBottomStatus.OffBottom and v.bottom_status == IrisBottomStatus.OffBottom)
                )
                and
                (
                    (variable.circulating_status == IrisCirculatingStatus.N_A)
                    or
                    (variable.circulating_status == IrisCirculatingStatus.Circulating and v.circulating_status == IrisCirculatingStatus.Circulating)
                    or
                    (variable.circulating_status == IrisCirculatingStatus.NotCirculating and v.circulating_status == IrisCirculatingStatus.NotCirculating)
                )
            )]

            if len(values_history) == 0:
                value = None
            elif variable.interval_averaging == IrisAveragingType.Mean:
                value = sum(values_history) / len(values_history)
            elif variable.interval_averaging == IrisAveragingType.StDev:
                mean = sum(values_history) / len(values_history)
                value = (sum([(x - mean) ** 2 for x in values_history]) / len(values_history)) ** 0.5
            elif variable.interval_averaging == IrisAveragingType.Max:
                value = max(values_history)
            elif variable.interval_averaging == IrisAveragingType.Min:
                value = min(values_history)
            elif variable.interval_averaging == IrisAveragingType.First:
                value = values_history[0]
            elif variable.interval_averaging == IrisAveragingType.Last:
                value = values_history[-1]
            else:
                value = values_history[-1]  # default to last value if no averaging type is specified
            variable_values.append(value)

        return [IrisRecordDataLine(variable_values)]

class IrisRecordVariableMonitored:
    def __init__(self, variable_name:str, iris_item:str, interval_averaging:IrisAveragingType=None, \
                 slips_status:IrisSlipStatus=IrisSlipStatus.N_A, bottom_status:IrisBottomStatus=IrisBottomStatus.N_A, circulating_status:IrisCirculatingStatus=IrisCirculatingStatus.N_A):
        self.variable_name = variable_name
        self.iris_item = iris_item
        self.interval_averaging = interval_averaging
        self.slips_status = slips_status
        self.bottom_status = bottom_status
        self.circulating_status = circulating_status

    def copy(self):
        return IrisRecordVariableMonitored(
            variable_name=self.variable_name,
            iris_item=self.iris_item,
            interval_averaging=self.interval_averaging,
            slips_status=self.slips_status,
            bottom_status=self.bottom_status,
            circulating_status=self.circulating_status
        )

    def load_from_object(self, obj:IrisRecordVariableMonitored):
        if obj is None: return
        self.variable_name = obj.variable_name
        self.iris_item = obj.iris_item
        self.interval_averaging = obj.interval_averaging
        self.slips_status = obj.slips_status
        self.bottom_status = obj.bottom_status
        self.circulating_status = obj.circulating_status

    def to_dict(self):
        return {
            "VariableName": self.variable_name,
            "IrisItem": self.iris_item,
            "IntervalAveraging": self.interval_averaging.name if self.interval_averaging else None,
            "SlipsStatus": self.slips_status.name,
            "BottomStatus": self.bottom_status.name,
            "CirculatingStatus": self.circulating_status.name,
        }

    @classmethod
    def from_dict(cls, data: dict):
        interval_averaging_name = data.get("IntervalAveraging")
        interval_averaging = (
            IrisAveragingType[interval_averaging_name]
            if interval_averaging_name else None
        )

        return cls(
            variable_name=data["VariableName"],
            iris_item=data["IrisItem"],
            interval_averaging=interval_averaging,
            slips_status=IrisSlipStatus[data.get("SlipsStatus", "N_A")],
            bottom_status=IrisBottomStatus[data.get("BottomStatus", "N_A")],
            circulating_status=IrisCirculatingStatus[data.get("CirculatingStatus", "N_A")]
        )

class HistoricalVariableValue:
    def __init__(self, value:float, timestamp:datetime, depth:float=None, slips_status:IrisSlipStatus=IrisSlipStatus.N_A, bottom_status:IrisBottomStatus=IrisBottomStatus.N_A, circulating_status:IrisCirculatingStatus=IrisCirculatingStatus.N_A):
        self.value = value
        self.timestamp = timestamp
        self.depth = depth
        self.slips_status = slips_status
        self.bottom_status = bottom_status
        self.circulating_status = circulating_status

class IrisRecordDataLine:
    def __init__(self, variable_values:dict[str, any]):
        self.variable_values = variable_values

class IrisCalculatingParameters:
    def __init__(self, off_bottom_ref_length:float, in_slips_hookload_threshold_drilling:float, in_slips_hookload_threshold_tripping:float):
        self.off_bottom_ref_length = off_bottom_ref_length
        self.in_slips_hookload_threshold_drilling = in_slips_hookload_threshold_drilling
        self.in_slips_hookload_threshold_tripping = in_slips_hookload_threshold_tripping

    def SetValues(self, calculating_parameters:IrisCalculatingParameters, unit_option_depth:UnitOption=None, unit_option_hookload:UnitOption=None):
        self.off_bottom_ref_length = AdiCommands.ApplyConversionInfoToValue(unit_option_depth, calculating_parameters.off_bottom_ref_length, False) if unit_option_depth else calculating_parameters.off_bottom_ref_length
        self.in_slips_hookload_threshold_drilling = AdiCommands.ApplyConversionInfoToValue(unit_option_hookload, calculating_parameters.in_slips_hookload_threshold_drilling, False) if unit_option_hookload else calculating_parameters.in_slips_hookload_threshold_drilling
        self.in_slips_hookload_threshold_tripping = AdiCommands.ApplyConversionInfoToValue(unit_option_hookload, calculating_parameters.in_slips_hookload_threshold_tripping, False) if unit_option_hookload else calculating_parameters.in_slips_hookload_threshold_tripping

    @staticmethod
    def from_dict(data: dict, unit_option_depth:UnitOption=None, unit_option_hookload:UnitOption=None):
        off_bottom_ref_length = data.get("OffBottomRefLength", 0.4)
        if unit_option_depth is not None:
            off_bottom_ref_length = AdiCommands.ApplyConversionInfoToValue(unit_option_depth, off_bottom_ref_length, False)
        in_slips_hookload_threshold_drilling = data.get("InSlipsHookloadThresholdDrilling", 108.0)
        if unit_option_hookload is not None:
            in_slips_hookload_threshold_drilling = AdiCommands.ApplyConversionInfoToValue(unit_option_hookload, in_slips_hookload_threshold_drilling, False)
        in_slips_hookload_threshold_tripping = data.get("InSlipsHookloadThresholdTripping", 100.0)
        if unit_option_hookload is not None:
            in_slips_hookload_threshold_tripping = AdiCommands.ApplyConversionInfoToValue(unit_option_hookload, in_slips_hookload_threshold_tripping, False)

        return IrisCalculatingParameters(
            off_bottom_ref_length=off_bottom_ref_length,
            in_slips_hookload_threshold_drilling=in_slips_hookload_threshold_drilling,
            in_slips_hookload_threshold_tripping=in_slips_hookload_threshold_tripping
        )

    def to_dict(self, unit_option_depth:UnitOption=None, unit_option_hookload:UnitOption=None):
        return {
            "OffBottomRefLength": self.off_bottom_ref_length if unit_option_depth is None else AdiCommands.ApplyConversionInfoToValue(unit_option_depth, self.off_bottom_ref_length, True),
            "OffBottomRefLengthUnit": None if unit_option_depth is None else unit_option_depth.short_name,
            "InSlipsHookloadThresholdDrilling": self.in_slips_hookload_threshold_drilling if unit_option_hookload is None else AdiCommands.ApplyConversionInfoToValue(unit_option_hookload, self.in_slips_hookload_threshold_drilling, True),
            "InSlipsHookloadThresholdDrillingUnit": None if unit_option_hookload is None else unit_option_hookload.short_name,
            "InSlipsHookloadThresholdTripping": self.in_slips_hookload_threshold_tripping if unit_option_hookload is None else AdiCommands.ApplyConversionInfoToValue(unit_option_hookload, self.in_slips_hookload_threshold_tripping, True),
            "InSlipsHookloadThresholdTrippingUnit": None if unit_option_hookload is None else unit_option_hookload.short_name
        }

class AdiServerIris(EventEmitter, AdiProcessClientIdentification):
    def __init__(self, adi_server:AdiServer=None):
        EventEmitter.__init__(self)
        AdiProcessClientIdentification.__init__(self, exec_name ="Iris Server", host_name=socket.gethostname(), user_name=os.getlogin())

        self.monitored_records: list[IrisRecordMonitored] = list([
            IrisRecordMonitored("Time/Depth", "Master", IrisRecordMonitoredType.Time, 1.0),
            IrisRecordMonitored("Time SDL Fast", "", IrisRecordMonitoredType.Time, 1.0),
            IrisRecordMonitored("Logging", "", IrisRecordMonitoredType.DepthWhileDrilling, 0.5 / 0.3048) # in ft
        ])

        self.iris_variables:list[IrisVariable] = list([
            IrisVariable("Time & Date", unit_type_name="Time & Date", value=0.0),
            IrisVariable("Depth", unit_type_name="Depth", value=0.0),
            IrisVariable("T/D Activity", unit_type_name="Unitless", value=0.0),
            IrisVariable("Block Position", unit_type_name="Depth", value=0.0),
            IrisVariable("Hole Depth", unit_type_name="Depth", value=0.0),
            IrisVariable("Virtual Depth", unit_type_name="Depth", value=0.0),
            IrisVariable("Change Act Auto", unit_type_name="Unitless", value=0.0),
            IrisVariable("Off Btm Drilling", unit_type_name="Unitless", value=0.0),
            IrisVariable("On Btm Status", unit_type_name="Unitless", value=0.0),
            IrisVariable("Pump State", unit_type_name="Unitless", value=0.0),
            IrisVariable("In Slips", unit_type_name="Unitless", value=0.0),
            IrisVariable("Hookload", unit_type_name="Hook weights", value=0.0)
        ])

        self.calculating_parameters = IrisCalculatingParameters(
            0.4 / 0.3048,   # 0.4m in feet, used as reference for calculating on bottom status based on block position and hole depth
            108.0,          # Hookload threshold in mton for considering we are in slips while drilling, used for calculating slips status
            100.0           # Hookload threshold in mton for considering we are in slips while tripping, used for calculating slips status
        )

        self.enabled = False
        self._v_adi_server:AdiServer = adi_server

    def _setup_volatiles(self, adi_server:AdiServer=None):
        self._v_adi_server = adi_server

        # The values below will be updated every time we open any dataset
        self._v_act_drilling = 1.0
        self._v_act_off_bottom_drilling = -1.0

        # Storage for all variable values over the maximum interval of all monitored records, to be used for averaging
        self._v_variable_values_history_time:dict[str, list[HistoricalVariableValue]] = {}
        self._v_variable_values_history_depth_drilling:dict[str, list[HistoricalVariableValue]] = {}
        self._v_opened_datasets:dict[Tuple[str, str], adi.AdiDefinitions.AdiDataSetReader] = {}

        self._v_pending_by_record_description:dict[Tuple[str, str], int] = {}
        self._v_pending_lock = asyncio.Lock()
        self._v_max_lines_per_record = 10000   # example cap

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._setup_volatiles(None)

    def Start(self, loop:asyncio.AbstractEventLoop):
        if hasattr(self, '_v_running') and self._v_running: raise Exception("RigsStats is already running!")

        self._v_loop = loop
        self.enabled = True

        self._v_adi_server.add_event_listener("WELL_CHANGED", self.__WellRunChangeHandler)
        self._v_adi_server.add_event_listener("RUN_CHANGED", self.__WellRunChangeHandler)
        self._v_adi_server.add_event_listener("UNITSET_CHANGED", self.__UnitsetChangeHandler)

        self._v_running:bool = True
        self._v_task = self._v_loop.create_task(self.__IrisProcess())
        self._v_writer_task = self._v_loop.create_task(self.__WriterLoop())
        self._v_max_pending_lines = 100_000   # example protection
        self._v_pending_count = 0

    async def Stop(self):
        if not hasattr(self, '_v_running') or not self._v_running: raise Exception("RigsStats is not running!")

        self.enabled = False
        self._v_running = False

        self._v_adi_server.remove_event_listener("WELL_CHANGED", self.__WellRunChangeHandler)
        self._v_adi_server.remove_event_listener("RUN_CHANGED", self.__WellRunChangeHandler)
        self._v_adi_server.remove_event_listener("UNITSET_CHANGED", self.__UnitsetChangeHandler)

        await self._v_task
        await self._v_writer_task

    async def GetMonitoredRecords(self):
        return [record.to_dict() for record in self.monitored_records]

    async def SetMonitoredRecords(self, records_monitored:list[IrisRecordMonitored]):
        try:
            self._v_adi_server.db.update_adi_server_iris(self._v_adi_server)
            self.monitored_records = list(records_monitored)
            self._v_adi_server.CloseDataSetsFromClient(self)
            self._v_opened_datasets = {}
        except Exception as e:
            return False
        return True

    async def UpdateRecordsMonitored(self, records_monitored:list[IrisRecordMonitored]):
        try:
            # Update the monitored records list with the new one, but keep the existing monitored variables if the record already exists
            updated_records = []
            for new_record in records_monitored:
                existing_record = next((r for r in self.monitored_records if r.record_name == new_record.record_name), None)
                if existing_record:
                    new_record.variables_monitored = [v.copy() for v in existing_record.variables_monitored]
                updated_records.append(new_record)
            await self.SetMonitoredRecords(updated_records)
        except Exception as e:
            raise e
        return True

    async def UpdateRecordVariablesMapping(self, record_name:str, record_variables:list[IrisRecordVariableMonitored]):
        # Create a copy of the current monitored records, modify it, then call SetMonitoredRecords
        try:
            records_copy = [r.copy() for r in self.monitored_records]
            record = next((r for r in records_copy if r.record_name == record_name), None)
            if record is None: raise Exception(f"Record {record_name} not in monitored list.")

            record.variables_monitored = record_variables
            await self.SetMonitoredRecords(records_copy)
        except Exception as e:
            raise e
        return True

    async def AddOrUpdateIrisRecordVariable(self, record_name:str, record_variable:IrisRecordVariableMonitored):
        # Create a copy of the current monitored records, modify it, then call SetMonitoredRecords
        try:
            records_copy = [r.copy() for r in self.monitored_records]
            record = next((r for r in records_copy if r.record_name == record_name), None)
            if record is None: raise Exception(f"Record {record_name} not in monitored list.")

            existing_variable = next((var for var in record.variables_monitored if var.variable_name == record_variable.variable_name), None)
            if existing_variable:
                existing_variable.load_from_object(record_variable)
            else:
                record.variables_monitored.append(record_variable)
            await self.SetMonitoredRecords(records_copy)
        except Exception as e:
            raise e
        return True

    async def GetCalculatingParameters(self)->IrisCalculatingParameters:
        unit_option_depth = await self._v_adi_server.GetUnitOptionByUnitTypeName("Depth")
        unit_option_hookload = await self._v_adi_server.GetUnitOptionByUnitTypeName("Hook weights")
        return self.calculating_parameters.to_dict(unit_option_depth, unit_option_hookload)

    async def SetCalculatingParameters(self, calculating_parameters:IrisCalculatingParameters):
        if calculating_parameters.off_bottom_ref_length is None or calculating_parameters.in_slips_hookload_threshold_drilling is None or calculating_parameters.in_slips_hookload_threshold_tripping is None:
            raise Exception("All calculating parameters must be provided.")
        try:
            unit_option_depth = await self._v_adi_server.GetUnitOptionByUnitTypeName("Depth")
            unit_option_hookload = await self._v_adi_server.GetUnitOptionByUnitTypeName("Hook weights")
            self.calculating_parameters.SetValues(calculating_parameters, unit_option_depth, unit_option_hookload)
            self._v_adi_server.db.update_adi_server_iris(self._v_adi_server)
        except Exception as e:
            raise e
        return True

    async def GetIrisVariables(self):
        return [var.to_dict(await self._v_adi_server.GetUnitOptionByUnitTypeName(var.unit_type_name)) for var in self.iris_variables]

    async def SetIrisVariableValue(self, variable_name:str, value:float):
        for var in self.iris_variables:
            if var.name == variable_name:
                unit_option = await self._v_adi_server.GetUnitOptionByUnitTypeName(var.unit_type_name)
                var.SetValue(value, unit_option)
                return True
        return False

    def __WellRunChangeHandler(self, event_name:str, data:any):
        # Clear opened datasets as they are specific for each well and run
        self._v_opened_datasets = {}

    async def __UnitsetChangeHandler(self, event_name:str):
        # Update calculating parameters unit based on new unitset
        unit_option_depth = await self._v_adi_server.GetUnitOptionByUnitTypeName("Depth")
        unit_option_hookload = await self._v_adi_server.GetUnitOptionByUnitTypeName("Hook weights")

    async def __CalculateAutomaticValues(self):
        # Iris Variables updated on this logic: T/D Activity, Hole Depth, On Btm Status, In Slips, Off Btm Drilling, Virtual Depth
        # Iris Variables values used: Hookload, Block Position

        # Premise: all variables exist
        depth_var = next((var for var in self.iris_variables if var.name == "Depth"), None)
        hole_depth_var = next((var for var in self.iris_variables if var.name == "Hole Depth"), None)
        td_activity_var = next((var for var in self.iris_variables if var.name == "T/D Activity"), None)
        block_position_var = next((var for var in self.iris_variables if var.name == "Block Position"), None)
        hookload_var = next((var for var in self.iris_variables if var.name == "Hookload"), None)
        in_slips_var = next((var for var in self.iris_variables if var.name == "In Slips"), None)
        on_bottom_var = next((var for var in self.iris_variables if var.name == "On Btm Status"), None)
        on_btm_status_var = next((var for var in self.iris_variables if var.name == "On Btm Status"), None)
        virtual_drilling_var = next((var for var in self.iris_variables if var.name == "Off Btm Drilling"), None)
        virtual_depth_var = next((var for var in self.iris_variables if var.name == "Virtual Depth"), None)
        if td_activity_var is None or hookload_var is None or in_slips_var is None or on_bottom_var is None or \
            depth_var is None or block_position_var is None or hole_depth_var is None or on_btm_status_var is None or \
            virtual_drilling_var is None or virtual_depth_var is None:
            return

        td_activity = td_activity_var.value
        is_drilling_activity = td_activity == self._v_act_drilling or td_activity == self._v_act_off_bottom_drilling
        is_virtual_drilling = virtual_drilling_var.value == 1.0
        auto_change_activity = next((var.value for var in self.iris_variables if var.name == "Change Act Auto"), 1.0) == 1.0

        # Calculating Slips Status based on drilling activity and Hookload
        # Only if there is a change in Hookload we will recalculate slip status
        in_slips_threshold = self.calculating_parameters.in_slips_hookload_threshold_drilling if is_drilling_activity else self.calculating_parameters.in_slips_hookload_threshold_tripping
        hookload_value = hookload_var.value
        in_slips_value = in_slips_var.value
        if hookload_value is not None:
            in_slips_value = 1.0 if hookload_value < in_slips_threshold else 0.0
            in_slips_var.value = in_slips_value

        on_bottom = on_bottom_var.value

        # Updating bit depth based on block position if not in slips (None represents unknown state, so no updates)
        if in_slips_value is not None and not in_slips_value and block_position_var.value is not None:
            block_position = block_position_var.value
            block_position_previous = next((v.value for v in self._v_variable_values_history_time.get("Block Position", [])[-2:][:-1]), block_position) # Get previous block position value from history
            
            depth_var.value += block_position_previous - block_position

            # if new bit depth is higher than hole depth, hole depth shall be incremented
            if depth_var.value > hole_depth_var.value:
                hole_depth_var.value = depth_var.value

                on_bottom = 1.0 # On Bottom
                on_bottom_var.value = on_bottom

                # if we were in off btm drilling, disable it as we are now at bottom
                if is_virtual_drilling:
                    is_virtual_drilling = False
                    virtual_drilling_var.value = 0.0 # Not Off Btm Drilling anymore

                # if auto-change, t/d activity immediately to be changed to drilling (if not already)
                if not is_drilling_activity and auto_change_activity:
                    td_activity_var.value = self._v_act_drilling # Drilling
                    is_drilling_activity = True

            # if auto-change, then remove drilling activity if bit is too far from bottom
            elif is_drilling_activity and depth_var.value < hole_depth_var.value - self.calculating_parameters.off_bottom_ref_length and auto_change_activity:
                td_activity_var.value = 0.0 # None
                is_drilling_activity = False

            if is_virtual_drilling:
                if depth_var.value > virtual_depth_var.value:
                    virtual_depth_var.value = depth_var.value

                    on_bottom = 1.0 # On Bottom
                    on_bottom_var.value = on_bottom

                    if not is_drilling_activity and auto_change_activity:
                        td_activity_var.value = self._v_act_off_bottom_drilling # OffBottom Drilling
                        is_drilling_activity = True

                # if auto-change, then remove drilling activity if bit is too far from bottom
                elif is_drilling_activity and depth_var.value < virtual_depth_var.value - self.calculating_parameters.off_bottom_ref_length and auto_change_activity:
                    td_activity_var.value = 0.0 # None
                    is_drilling_activity = False

    def __StoreHistoricalValues(self, current_time:datetime):
        # if record is type Time, ger max interval cycle
        max_time_interval = max([r.interval_cycle for r in self.monitored_records if r.monitored_type == IrisRecordMonitoredType.Time], default=0)
        max_depth_drilling_interval = max([r.interval_cycle for r in self.monitored_records if r.monitored_type == IrisRecordMonitoredType.DepthWhileDrilling], default=0)

        current_depth = next((v.value for v in self.iris_variables if v.name == "Depth"), None)
        current_slips_status = next((v.value for v in self.iris_variables if v.name == "T/D Activity"), None)
        current_bottom_status = next((v.value for v in self.iris_variables if v.name == "On Btm Status"), None)
        current_circulating_status = next((v.value for v in self.iris_variables if v.name == "Pump State"), None)
        for variable in self.iris_variables:
            if variable.name not in self._v_variable_values_history_time:
                self._v_variable_values_history_time[variable.name] = []

            var_value = current_time if variable.name == "Time & Date" else variable.value
            if variable.name == "T/D Activity" and var_value is None:
                var_value = 0.0

            self._v_variable_values_history_time[variable.name].append(HistoricalVariableValue(var_value, current_time, current_depth, current_slips_status, current_bottom_status, current_circulating_status))
            # Remove old values that are outside the maximum interval of all monitored records
            self._v_variable_values_history_time[variable.name] = [v for v in self._v_variable_values_history_time[variable.name] if (current_time - v.timestamp).total_seconds() <= max_time_interval]

    async def __AddPendingLines(self, record_name, description, lines):
        async with self._v_pending_lock:
            if (record_name, description) not in self._v_pending_by_record_description:
                self._v_pending_by_record_description[(record_name, description)] = []
            current = self._v_pending_by_record_description[(record_name, description)]
            free_slots = self._v_max_lines_per_record - len(current)

            if free_slots <= 0:
                return  # queue for this record is full

            current.extend(lines[:free_slots])

    async def __WriteRecordBatch(self, dataset:AdiDataSetReader, lines):
        """
        Return True if the whole batch was written successfully,
        False if it should be retried.
        """
        lines_values = [line.variable_values for line in lines]
        result = await self._v_adi_server.DatasetWrite(dataset, DataSetWriteModes.Insert | DataSetWriteModes.PostRealTimeData, lines_values)
        return result

    async def __WriterLoop(self):
        def _chunked(seq, size):
            for i in range(0, len(seq), size):
                yield seq[i:i + size]

        while self._v_running:
            try:
                await asyncio.sleep(1.0)

                async with self._v_pending_lock:
                    if not self._v_pending_by_record_description:
                        continue

                    batch_map = self._v_pending_by_record_description
                    self._v_pending_by_record_description = {}

                failed_map = defaultdict(list)
                records_snapshot = list(self.monitored_records)

                for (record_name, description), lines in batch_map.items():
                    if not lines:
                        continue

                    dataset:AdiDataSetReader = None if (record_name, description) not in self._v_opened_datasets else self._v_opened_datasets[(record_name, description)]
                    try:
                        variables = next((r.variables_monitored for r in records_snapshot if r.record_name == record_name), [])
                        if len(variables) == 0: continue
                        # Check if dataset is open
                        if dataset is None:
                            # Try to open the dataset once
                            var_to_open = [{"Variable": (await self._v_adi_server.GetVariable(v.variable_name)), "UnitOption": (await self._v_adi_server.GetUnitOptionByUnitTypeName(next(item.unit_type_name for item in self.iris_variables if item.name == v.variable_name)))} for v in variables]
                            dataset = await self._v_adi_server.DatasetPrepare(self._v_adi_server._v_current.well, int(self._v_adi_server._v_current.run), record_name, description, create_if_not_exists=True)
                            await self._v_adi_server.DatasetOpen(self, dataset, variables=var_to_open, open_mode=RecordOpenModes.Write | RecordOpenModes.Create | RecordOpenModes.NoTruncate)
                            if dataset is None:
                                # record no longer exists
                                raise Exception(f"Dataset {record_name} could not be opened for writing.")
                            self._v_opened_datasets[(record_name, description)] = dataset
                        if len(self._v_opened_datasets[(record_name, description)].variables) != len(variables):
                            # This can happen if the record was recreated with different variables, so we need to reopen it
                            await self._v_adi_server.DataSetClose(self, self._v_opened_datasets[(record_name, description)])
                            del self._v_opened_datasets[(record_name, description)]
                            raise Exception("Dataset variables count mismatch, reopening dataset.")
                    except Exception:
                        # decide what to do with old lines
                        # continue   # discard them
                        # or failed_map[record_name].extend(lines) to keep retrying, but that may create undead backlog
                        failed_map[(record_name, description)].extend(lines)
                        dataset = None

                    try:
                        if dataset is not None:
                            for chunk in _chunked(lines, 1000):
                                ok = await self.__WriteRecordBatch(dataset, chunk)
                                if not ok:
                                    failed_map.setdefault((record_name, description), []).extend(chunk)
                                    break
                    except Exception:
                        failed_map[(record_name, description)].extend(lines)

                if failed_map:
                    async with self._v_pending_lock:
                        for (record_name, description), lines in failed_map.items():
                            if (record_name, description) not in self._v_pending_by_record_description:
                                self._v_pending_by_record_description[(record_name, description)] = []
                            current = self._v_pending_by_record_description[(record_name, description)]
                            free_slots = self._v_max_lines_per_record - len(current)
                            if free_slots > 0:
                                current.extend(lines[:free_slots])

            except Exception as e:
                print(f"Error in writer loop: {e}")

    async def __IrisProcess(self):
        # Getting the activity codes from server
        td_act = await self._v_adi_server.GetOptionsListByName("T/D Activity")
        if td_act is not None and isinstance(td_act, adi.AdiDefinitions.OptionsList):
            self._v_act_drilling = td_act.options.index("Drilling") if "Drilling" in td_act.options else 1.0
            self._v_act_off_bottom_drilling = td_act.options.index("OffBottom Drilling") if "OffBottom Drilling" in td_act.options else -1.0

        while self._v_running:
            try:
                current_monotonic = time.monotonic()
                now_dt = datetime.now()

                # Process and calculate current data
                await self.__CalculateAutomaticValues()

                # Store current variable values with timestamps for averaging
                self.__StoreHistoricalValues(now_dt)

                # Grab a snapshot reference of the monitored records, in case they are changed while we are processing them
                records_snapshot = list(self.monitored_records)

                for r in records_snapshot:
                    if current_monotonic - r.last_generated_time > r.interval_cycle:
                        new_line = r.GenerateNewLine(now_dt, self.iris_variables, self._v_variable_values_history_time)
                        if new_line is not None:
                            await self.__AddPendingLines(r.record_name, r.description, new_line)
                        r.last_generated_time = current_monotonic

            except Exception as e:
                print(f"Error in Iris Process loop: {e}")
            await asyncio.sleep(0.1)
