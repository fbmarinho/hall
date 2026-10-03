import datetime
import adi.AdiClientToRemote
import adi.AdiDefinitions
import adi.AdiEnums
import asyncio

well = "34_7-D-1AH"
run = "0500"
motor_revs_per_litre = 0.034
accepted_activities = ["Drilling", "OffBottom Drilling"]

async def main():
    adi_client:adi.AdiClientToRemote.AdiClientToRemote = adi.AdiClientToRemote.AdiClientToRemote(asyncio.get_event_loop(), host="192.168.50.63", enabled=True, realtime=False)
    while adi_client.connection_state != adi.AdiDefinitions.ConnectionState.CONNECTED: await asyncio.sleep(0.1)

    local_host, local_port = adi_client.writer.get_extra_info("sockname")
    print(f"Client '{local_host}' connected from port {local_port}")

    ds = None
    ds_slow = None
    try:
        # Get the list of datasets
        ds = await adi_client.OpenDataSet(well=well, run_alias=run, record="Time SDL Fast", description="", variables_list=["Time & Date", "RPM Surface Avg", {"name": "Flow In Pum Avg", "unit_option": "lpm"}, "T/D Activity"])
        number_lines = await ds.GetNumberOfRecords()
        if ds == None:
            print("Not possible to open Time SDL Fast dataset")
            return

        lines = []

        last_rpm = None        
        last_flow = None
        last_time = None
        total_krevs = 0.0
        rejected_activities = []

        lines_read = 0
        last_percentage_reported = 0
        while True:
            data = await ds.ReadNext(0x840)
            if len(data) == 0: break
            
            for line in data:
                if line[3] not in accepted_activities:
                    if line[3] not in rejected_activities:
                        # print(f"Rejected activity: {line[3]}")
                        rejected_activities.append(line[3])
                    continue

                prev_rpm = 0 if last_rpm is None else last_rpm
                prev_flow = 0 if last_flow is None else last_flow
                delta_secs = 0 if last_time is None else (line[0] - last_time).total_seconds()
                if delta_secs > 10: delta_secs = 1

                last_time, last_rpm, last_flow = line[0], line[1], line[2]
                total_krevs += (prev_rpm + prev_flow * motor_revs_per_litre) * delta_secs / 60.0 / 1000.0
                lines.append([line[0], total_krevs])

            lines_read += len(data)
            percentage = int(lines_read * 100 / number_lines)
            if percentage > last_percentage_reported:
                print(f"Reading dataset: {percentage}%")
                last_percentage_reported = percentage

        await ds.Close()
        print("Activities rejected:", ", ".join(rejected_activities))

        last_index_checked = 0
        def GetTotalKrevsByTime(time):
            nonlocal last_index_checked
            while last_index_checked < len(lines) and lines[last_index_checked][0] <= time:
                last_index_checked += 1
            if lines[last_index_checked - 1][0] <= time:
                return lines[last_index_checked - 1][1]
            return 0.0

        write_mode = adi.AdiEnums.RecordOpenModes.ReadWrite
        ds_slow:adi.AdiDefinitions.AdiDataSetReader = await adi_client.OpenDataSet(well=well, run_alias=run, record="Time SDL Slow", description="", variables_list=["Time & Date", "Revs On Bit"], open_mode_value=write_mode)
        if ds_slow == None:
            print("Not possible to open Time SDL Slow dataset")
            return

        lines_written = 0
        last_percentage_reported = 0
        while True:
            data = await ds_slow.ReadNext(0x840)
            if len(data) == 0: break
            
            for line in data:
                krevs = GetTotalKrevsByTime(line[0])
                if krevs < 0: krevs = 0
                if line[1] != krevs:
                    line[1] = krevs
            response = await ds_slow.WriteLines(adi.AdiEnums.DataSetWriteModes.Update, data)
            if not response["Success"]:
                print(f"Error writing to dataset: {response['ErrorMessage']}")
                break
            await ds_slow.ReadNext(0x01)
            
            lines_written += len(data)
            percentage = round(lines_written * 100 / number_lines)
            if percentage > last_percentage_reported:
                print(f"Writing dataset: {percentage}%")
                last_percentage_reported = percentage

        await ds_slow.Close()
        print(f"Final Total Krevs: {total_krevs:.3f} kRevs.\nProcess completed successfully.")
    except Exception as e:
        print(f"Error opening dataset: {e}")
    finally:
        if ds is not None and ds.is_open:
            await ds.Close()
        if ds_slow is not None and ds_slow.is_open:
            await ds_slow.Close()
        if adi_client is not None:
            await adi_client.Stop()


asyncio.run(main())
