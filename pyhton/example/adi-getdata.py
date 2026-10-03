class DataSet:
    def __init__(self, record, description, var_name):
        self.record = record
        self.description = description
        self.variables = ["Time & Date", var_name]
        self.results = None

import datetime
import sys

host = sys.argv[1]
filename = sys.argv[2]
date_str = sys.argv[3]
datasets = sys.argv[4].split('|')

# Combining datasets to be opened only once and to collect all variables
records:list[DataSet] = []
for i in range(int(len(datasets) / 3)):
    record, description, var_name = datasets[i * 3 + 0], datasets[i * 3 + 1], datasets[i * 3 + 2]
    rec = next((x for x in records if x.record == record and x.description == description), None)
    if rec == None: records.append(DataSet(record, description, var_name))
    else: rec.variables.append(var_name)

dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

import asyncio
import adi.AdiClientToRemote
import adi.AdiDefinitions
import adi.AdiEnums

async def GetData():
    loop = asyncio.get_running_loop()
    adi_client = adi.AdiClientToRemote.AdiClientToRemote(loop, host, realtime=False)
    while adi_client.connection_state != adi.AdiEnums.ConnectionState.CONNECTED: await asyncio.sleep(0.1)
    
    ds:adi.AdiDefinitions.AdiDataSetReader = None
    try:
        dataset:DataSet
        for dataset in records:
            ds = await adi_client.OpenDataSet(record=dataset.record, description=dataset.description, variables_list=dataset.variables)
            search = await ds.SearchLineFromVariable(start_pos=0, variable="Time & Date", start_value=dt - datetime.timedelta(seconds=1), end_value=dt)
            if search["Success"]: dataset.results = (await ds.ReadNext(1))[0]
            else: dataset.results = [None] * len(dataset.variables)
    finally:
        if ds != None and ds.is_open: await ds.Close()

    str_final:str = ""
    for i in range(int(len(datasets) / 3)):
        record, description, var_name = datasets[i * 3 + 0], datasets[i * 3 + 1], datasets[i * 3 + 2]
        rec = next((x for x in records if x.record == record and x.description == description), None)
        ix = rec.variables.index(var_name)
        str_final += ("" if len(str_final) == 0 else "|") + ("" if rec.results[ix] == None else str(rec.results[ix]))
        
    # str_final += "|" + str(records[0].results[0])

    file = open(filename, "w")
    file.write(str_final)
    file.close()
    
    print(str_final)

asyncio.run(GetData())
