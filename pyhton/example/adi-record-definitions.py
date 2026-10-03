import adi.AdiClientToRemote
import adi.AdiCommands
import adi.AdiDefinitions
import adi.AdiEnums
import asyncio

async def main():
    adi_client:adi.AdiClientToRemote.AdiClientToRemote = adi.AdiClientToRemote.AdiClientToRemote(asyncio.get_event_loop(), host="192.168.1.11", enabled=True, realtime=False)
    while adi_client.connection_state != adi.AdiDefinitions.ConnectionState.CONNECTED: await asyncio.sleep(0.1)

    ds:adi.AdiDefinitions.AdiDataSetReader = await adi_client.OpenDataSet(well="25_1-14A", run_alias="1000", record="RG DDSr Burst", description="Insite Read", open_mode_value=adi.AdiDefinitions.RecordOpenModes.Read)
    await ds.Close()

    lines:str = ":Variables\n"
    for v in ds.variables:
        adi_var = await adi_client.SendNewCommand(adi.AdiCommands.AdiCommands.QueryVariable(adi_client, v["Variable"].name))
        variable:adi.AdiDefinitions.AdiVariable = adi_var["Variable"]

        v_name = variable.name
        v_mnemonic = "" if variable.mnemonic is None else variable.mnemonic
        v_curve_label = "" if variable.curve_label is None else variable.curve_label
        unit_type_name = variable.unit_type.name
        v_data_type = variable.GetVariableDataType()
        v_specials = variable.GetSpecialsString()
        v_decimal_places = None if variable.number_of_decimals is None else str(v["Variable"].number_of_decimals)
        v_mnemonic32 = "" if variable.mnemonic32 is None else variable.mnemonic32

        line = f"{v_name:<17};{v_mnemonic:<5};{v_curve_label:<26};{unit_type_name:<16};{v_data_type:<7};{v_specials};{v_decimal_places:<3};{v_mnemonic32}"

        lines += f"{line}\n"

    lines += ":Records\n"
    
    result = await adi_client.SendNewCommand(adi.AdiCommands.AdiCommands.QueryRecordAttributesEx(adi_client, ds.record))
    record:adi.AdiDefinitions.AdiRecord = result["Record"]
    rec_name = record.name
    rec_type = record.record_type_id
    rec_index_types = record.GetIndexTypesString()
    rec_category = record.category
    well_pk = "2" if (record.primary_keys & adi.AdiEnums.RecordPrimaryKeys.Well.value) != 0 else "0"
    run_pk = "2" if (record.primary_keys & adi.AdiEnums.RecordPrimaryKeys.BitRun.value) != 0 else "0"
    desc_pk = "2" if (record.primary_keys & adi.AdiEnums.RecordPrimaryKeys.Description.value) != 0 else "0"
    psl_types = record.psl_types
    hidden = "1" if (record.attributes & adi.AdiEnums.RecordAttributes.Hidden.value) != 0 else "0"
    read_only = "1" if (record.attributes & adi.AdiEnums.RecordAttributes.ReadOnly.value) != 0 else "0"
    locked = "1" if (record.attributes & adi.AdiEnums.RecordAttributes.Locked.value) != 0 else "0"
    lines += f"{rec_name}; {rec_type}; {rec_index_types}; {rec_category}; {well_pk}; {run_pk}; {desc_pk}; {psl_types}; {hidden}; {read_only}; {locked}\n"
    vars = await adi_client.SendNewCommand(adi.AdiCommands.AdiCommands.QueryRecordVariables(adi_client, record.name))
    variable:adi.AdiDefinitions.AdiVariable = None
    for variable in vars["Variables"]:
        v_name = variable.name
        v_calc = "1" if (variable.special & adi.AdiEnums.VariableSpecialHandlings.Calculable.value) != 0 else "0"
        v_mnemonic = "" if variable.mnemonic is None else variable.mnemonic
        v_curve_label = "" if variable.curve_label is None else variable.curve_label
        v_mnemonic32 = "" if variable.mnemonic32 is None else variable.mnemonic32
        v_algorithm = "" if variable.record_variable_data.algorithm is None else variable.record_variable_data.algorithm
        v_ref_variable = "" if variable.record_variable_data.ref_variable is None else variable.record_variable_data.ref_variable
        v_coeff1 = "0" if variable.record_variable_data.coeff1 == 0 else str(variable.record_variable_data.coeff1)
        v_coeff2 = "0" if variable.record_variable_data.coeff2 == 0 else str(variable.record_variable_data.coeff2)
        v_coeff3 = "0" if variable.record_variable_data.coeff3 == 0 else str(variable.record_variable_data.coeff3)

        line = f"{v_name:>23};{(v_calc):>2};{v_mnemonic:<5};{v_curve_label:<26};{v_mnemonic32:<32};{v_algorithm:<15};{v_ref_variable:<15};{v_coeff1:<12};{v_coeff2:<12};{v_coeff3:<12}"
        lines += f"{line}\n"

    print(lines)
    await adi_client.Stop()
    print("Finished!")

asyncio.run(main())
