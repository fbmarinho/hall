import adi.AdiClientToRemote
import adi.AdiDefinitions
import asyncio

async def example1():
    adi_client:adi.AdiClientToRemote.AdiClientToRemote = adi.AdiClientToRemote.AdiClientToRemote(asyncio.get_event_loop(), host="192.168.50.63", enabled=True)
    while adi_client.connection_state != adi.AdiDefinitions.ConnectionState.CONNECTED: await asyncio.sleep(0.1)
    
    ds:adi.AdiDefinitions.AdiDataSetReader = await adi_client.OpenDataSet(well=None, run_alias=None, record="Time SDL Fast", description="", variables_list=["Time & Date", "Depth"])
    number_records = await ds.GetNumberOfRecords()
    print(f"Number of records: {number_records}")
    data = await ds.ReadNext(1)
    await ds.Close()
    print(data)


async def example2():
    async def RtDataArrived(msg, record, data):
        print(f"New data arrived for record {record}: {data}")
    
    adi_client:adi.AdiClientToRemote.AdiClientToRemote = adi.AdiClientToRemote.AdiClientToRemote(asyncio.get_event_loop(), host="192.168.50.63", enabled=True)
    while adi_client.connection_state != adi.AdiDefinitions.ConnectionState.CONNECTED: await asyncio.sleep(0.1)
    
    # well = None means ANY well, run_alias = None means ANY run
    monitor = await adi_client.AddRtMonitor(well=None, run_alias=None, record="Time SDL Fast", description="", variables_list=["Time & Date", "Depth"])
    monitor.add_event_listener("message_received", RtDataArrived)
    await asyncio.sleep(10)
    monitor.Stop()

asyncio.run(example2())
