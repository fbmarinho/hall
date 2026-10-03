import adi.AdiClientToRemote
import adi.AdiDefinitions
import adi.AdiEnums
import asyncio

async def main():
    well = "2_8-C-20"
    run = "0300"
    record = "BGamma RT"
    description_source = "Realtime2"
    description_output = "Realtime"

    adi_client:adi.AdiClientToRemote.AdiClientToRemote = adi.AdiClientToRemote.AdiClientToRemote(asyncio.get_event_loop(), host="192.168.1.50", enabled=True, realtime=False)
    while adi_client.connection_state != adi.AdiDefinitions.ConnectionState.CONNECTED:
        await asyncio.sleep(0.1)

    ds_src:adi.AdiDefinitions.AdiDataSetReader = await adi_client.OpenDataSet(well=well, run_alias=run, record=record, description=description_source)

    if ds_src is None:
        print("Source dataset not found")
        await adi_client.Stop()
        return

    ds_out:adi.AdiDefinitions.AdiDataSetReader = await adi_client.OpenDataSet(well=well, run_alias=run, record=record, description=description_output, open_mode_value=adi.AdiEnums.RecordOpenModes.Write)
    if ds_out is None:
        ds_out:adi.AdiDefinitions.AdiDataSetReader = await adi_client.OpenDataSet(well=well, run_alias=run, record=record, description=description_output, open_mode_value=adi.AdiEnums.RecordOpenModes.Write | adi.AdiEnums.RecordOpenModes.Create)
    if ds_out is None:
        print("Output dataset could not be created")
        await ds_src.Close()
        await adi_client.Stop()
        return

    array_indexes_converted = []
    vars_source = list(map(lambda v: v["Variable"].name, ds_src.variables))
    for v in ds_out.variables:
        v_name = v["Variable"].name
        if v_name in vars_source:
            array_indexes_converted.append(vars_source.index(v_name))
        else: array_indexes_converted.append(-1)

    number_records = await ds_src.GetNumberOfRecords()
    records_written = 0
    while records_written < number_records:
        records = await ds_src.ReadNext(1024)
        if len(records) == 0: break

        data_to_write = []
        for record in records:
            line = []
            for idx in array_indexes_converted:
                if idx >= 0:
                    line.append(record[idx])
                else:
                    if ds_out.variables[len(line)]["Variable"].name in ["BitDiameter", "RunDiameter"]:
                        line.append(12.25)
                    else:
                        line.append(None)
            data_to_write.append(line)

        try:
            await ds_out.WriteLines(write_mode_value=adi.AdiEnums.DataSetWriteModes.Insert, lines=data_to_write)
        except Exception as ex:
            print(f"Error writing records: {ex}")
            break
        records_written += len(records)
        print(f"Written {records_written} of {number_records} records")

    await ds_src.Close()
    await ds_out.Close()
    await adi_client.Stop()

asyncio.run(main())
