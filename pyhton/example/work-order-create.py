import adi.AdiClientToRemote
import adi.AdiCommands
import adi.AdiDefinitions
import adi.AdiEnums
import asyncio
import os

HOST = "192.168.1.67"
WELL = "25_1-14CT2"
PDT = "Memory"

# file_name = os.path.join(os.getcwd(), "25_1-14A RTWO Existing.txt")
file_name = "C:\\temp\\book2.txt"

def GetMappingText(well:str, run:str, record:str, description:str, tool_record:str, variable:str)->str:
    return f"0 | {record} | {description} | {tool_record} | {variable} |  | "

async def main():
    work_order = []
    with open(file_name, "r") as f:
        work_order = f.read().splitlines()

    adi_client:adi.AdiClientToRemote.AdiClientToRemote = adi.AdiClientToRemote.AdiClientToRemote(asyncio.get_event_loop(), host=HOST, enabled=True)
    while adi_client.connection_state != adi.AdiDefinitions.ConnectionState.CONNECTED: await asyncio.sleep(0.1)

    data_lines = []
    ds:adi.AdiDefinitions.AdiDataSetReader = await adi_client.OpenDataSet(well=WELL, run_alias="Well Based", record="PublicDataTable", description=PDT, variables_list=["PDTLongMnemonic"])
    if ds is not None:
        number_lines = await ds.GetNumberOfRecords()
        data_lines = await ds.ReadNext(number_lines)
        await ds.Close()
    existing_mnemonics = [line[0] for line in data_lines]

    variables = ["PDT Enable", "PDT Curve Name", "PDT Time Map", "PDT Depth Map", "PDT Time Map2", "PDT Depth Map2", "PDTLongMnemonic"]
    ds = await adi_client.OpenDataSet(well=WELL, run_alias="Well Based", record="PublicDataTable", description=PDT, variables_list=variables, open_mode_value=adi.AdiDefinitions.RecordOpenModes.Write)
    counter = 0
    for line in work_order:
        [a1, a2, a3, a4, a5, a6, a7, a8, trace_label, tool, record, variable, mnemonic, desc_depth, desc_time, desc_depth_name, desc_time_name, is_time, is_depth] = line.split("\t")
        if mnemonic in existing_mnemonics: continue
        time_map_text = GetMappingText(well=WELL, run="Well Based", record=f"{desc_time} Time", description=desc_time_name, tool_record=record, variable=variable) if is_time.lower().strip() == "x" else ""
        depth_map_text = GetMappingText(well=WELL, run="Well Based", record=f"{desc_depth} Depth", description=desc_depth_name, tool_record=record, variable=variable) if is_depth.lower().strip() == "x" else ""
        await ds.WriteLines(write_mode_value=adi.AdiEnums.DataSetWriteModes.Insert, lines=[[1, trace_label, time_map_text, depth_map_text, time_map_text, depth_map_text, mnemonic]])
        counter += 1
        existing_mnemonics.append(mnemonic)
    await ds.Close()
    await adi_client.Stop()
    print(f"Done! Processed {counter} lines.")

asyncio.run(main())
