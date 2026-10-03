import adi.AdiClientToRemote
import adi.AdiCommands
import adi.AdiDefinitions
import adi.AdiEnums
import asyncio
import os

HOST = "10.119.254.31"
WELL = "25_1-14A"

async def CheckDataSetExistsWithVariable(adi_client:adi.AdiClientToRemote.AdiClientToRemote, well:str, run:str, record:str, description:str, tool_record:str, variable:str)->bool:
    ds:adi.AdiDefinitions.AdiDataSetReader = await adi_client.OpenDataSet(well=well, run_alias=run, record=record, description=description, variables_list=["Description"])
    lines = []
    if ds is not None:
        num_lines = await ds.GetNumberOfRecords()
        lines = await ds.ReadNext(num_lines)
        await ds.Close()
    [record_exists, var_exists] = [False, False]
    if len(lines) > 0:
        for line in lines:
            result = await adi_client.SendNewCommand(adi.AdiCommands.AdiCommands.QueryRecordsList(adi_client, 0x0c, well, description=line[0]))
            if result is None or not result["Success"] or tool_record not in result["Records"]:
                continue
            record_exists = True
            # Tool record found! Now let's see if the variable exists on it
            result = await adi_client.SendNewCommand(adi.AdiCommands.AdiCommands.QueryRecordVariables(adi_client, tool_record))
            if result is not None and result["Success"] and variable in (v.name for v in result["Variables"]):
                var_exists = True
                return [record_exists, var_exists]
    return [record_exists, var_exists]

records_not_existing_time = []
records_not_existing_depth = []
async def main():
    work_order = []
    with open(os.path.join(os.getcwd(), "25_1-14A RTWO Memory.txt"), "r") as f:
        work_order = f.read().splitlines()

    adi_client:adi.AdiClientToRemote.AdiClientToRemote = adi.AdiClientToRemote.AdiClientToRemote(asyncio.get_event_loop(), host=HOST, enabled=True)
    while adi_client.connection_state != adi.AdiDefinitions.ConnectionState.CONNECTED: await asyncio.sleep(0.1)

    existing_lines = []
    for line in work_order:
        [trace_label, tool, record, variable, mnemonic, desc_depth, desc_time, desc_depth_name, desc_time_name, is_time, is_depth] = line.split("\t")
        [record_exists, var_exists] = [False, False]
        
        str_time = f"{desc_time} Time\\{record}"
        str_depth = f"{desc_depth} Depth\\{record}"
        if is_time.lower().strip() == "x" and str_time not in records_not_existing_time:
            [record_exists, var_exists] = await CheckDataSetExistsWithVariable(adi_client, well=WELL, run="Well Based", record=f"{desc_time} Time", description=desc_time_name, tool_record=record, variable=variable)
            if not record_exists: records_not_existing_time.append(str_time)
            
        if not var_exists and is_depth.lower().strip() == "x" and str_depth not in records_not_existing_depth:
            [record_exists, var_exists] = await CheckDataSetExistsWithVariable(adi_client, well=WELL, run="Well Based", record=f"{desc_depth} Depth", description=desc_depth_name, tool_record=record, variable=variable)
            if not record_exists: records_not_existing_depth.append(str_depth)

        if var_exists:
            existing_lines.append(line)
            print(f"Record \\ variable Exists: {record} \\ {variable}")
        else:
            print(f"Record \\ variable DOES NOT exist: {record}")
    with open(os.path.join(os.getcwd(), "25_1-14A RTWO Existing.txt"), "w") as f:
        f.write("\n".join(existing_lines))
    await adi_client.Stop()
    print("Done!")

asyncio.run(main())
