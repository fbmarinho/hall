import adi.AdiClientToRemote
import adi.AdiDefinitions
import asyncio

ip_insite = "127.0.0.1"

async def main():
    adi_client:adi.AdiClientToRemote.AdiClientToRemote = adi.AdiClientToRemote.AdiClientToRemote(asyncio.get_event_loop(), host=ip_insite, enabled=True)
    while adi_client.connection_state != adi.AdiDefinitions.ConnectionState.CONNECTED: await asyncio.sleep(0.1)

    ds:adi.AdiDefinitions.AdiDataSetReader = await adi_client.OpenDataSet(well=None, run_alias=None, record="Time SDL Fast", description="", variables_list=["Time & Date", "Depth"], open_mode_value=adi.AdiDefinitions.RecordOpenModes.Read)
    await ds.SetIndexPosition(adi.AdiDefinitions.SeekPositionMode.End)
    print(str((await ds.ReadPrevious())[0]))
    number_records = await ds.GetNumberOfRecords()
    print(f"Number of records: {number_records}")
    for i in range(30):
        await asyncio.sleep(5)
        number_records = await ds.GetNumberOfRecords()
        print(f"Number of records: {number_records}")
        await ds.SetIndexPosition(adi.AdiDefinitions.SeekPositionMode.End)
        print(str((await ds.ReadPrevious())[0]))


async def example_itom():
    adi_client:adi.AdiClientToRemote.AdiClientToRemote = adi.AdiClientToRemote.AdiClientToRemote(asyncio.get_event_loop(), host="11.11.0.102", enabled=True)
    while adi_client.connection_state != adi.AdiDefinitions.ConnectionState.CONNECTED: await asyncio.sleep(0.1)
    ds = await adi_client.OpenDataSet(record="iTom Save", description="CurrentData", bag_mode=True)
    files = await ds.GetFilesList()
    data = await ds.ReadFile(files[0]['EntryName'])
    await ds.Close()
    import json
    itom_json = json.loads(data.decode('utf8'))


asyncio.run(main())
