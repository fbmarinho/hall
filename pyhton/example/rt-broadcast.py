from __future__ import annotations
import asyncio
from datetime import datetime
from adi.AdiClientToRemote import AdiClientToRemote
from adi.AdiDefinitions import ConnectionState
from adi.AdiEnums import DataSetWriteModes, RecordOpenModes

async def async_main():
    adi_client:AdiClientToRemote = AdiClientToRemote(asyncio.get_event_loop(), host="127.0.0.1", enabled=True, realtime=True)
    while adi_client.connection_state != ConnectionState.CONNECTED: await asyncio.sleep(0.1)

    open_mode = RecordOpenModes.PostRealTimeData | RecordOpenModes.ReadWrite | RecordOpenModes.Create | RecordOpenModes.NoTruncate

    vars_logging = ["Time & Date", "Depth", "T/D Activity", {"name": "ROP Avg", "unit_option": "fps"}, "Revs On Bit", "Hydraul HP Bit", "Hydraul HP Area"]
    ds_logging = await adi_client.OpenDataSet(well=adi_client.well, run_alias=adi_client.run_alias, record="Logging", description="", open_mode_value=open_mode, variables_list=vars_logging)
    vars_bwtb = ["Time & Date", {"name": "DCTA", "unit_option": "f-p"}, {"name": "DCWA", "unit_option": "klb"}]
    ds_bwtb = await adi_client.OpenDataSet(well=adi_client.well, run_alias=adi_client.run_alias, record="BWTB Bit RT", description="Realtime", open_mode_value=open_mode, variables_list=vars_bwtb)
    vars_bvibe = ["Time & Date", "RPM RT"]
    ds_bvibe = await adi_client.OpenDataSet(well=adi_client.well, run_alias=adi_client.run_alias, record="BVibe RPM RT", description="Realtime", open_mode_value=open_mode, variables_list=vars_bvibe)


    write_bwtb_every = 5
    write_bvibe_every = 20
    write_logging_every = 30
    depth = 1000
    tda = 2
    rop = 5
    revs = 10000
    hydraul_hp_bit = 500
    hydraul_hp_area = 200

    wob = 5
    tob = 10
    rpm = 100
    for i in range(1, 1000):
        if i % write_bwtb_every == 0:
            print(f"Writing data to BWTB: [{tob}, {wob}]")
            await ds_bwtb.WriteLines(write_mode_value=DataSetWriteModes.PostRealTimeData, lines=[[datetime.now().astimezone(), tob, wob]])
            wob += 1
            tob += 2
    
        if i % write_bvibe_every == 0:
            print(f"Writing data to BVibe: [{rpm}]")
            await ds_bvibe.WriteLines(write_mode_value=DataSetWriteModes.PostRealTimeData, lines=[[datetime.now().astimezone(), rpm]])
            rpm += 10

        if i % write_logging_every == 0:
            print(f"Writing data to Logging...")
            await ds_logging.WriteLines(write_mode_value=DataSetWriteModes.PostRealTimeData, lines=[[datetime.now().astimezone(), depth, tda, rop, revs, hydraul_hp_bit, hydraul_hp_area]])
            depth += 0.5

        await asyncio.sleep(1)

    await ds_logging.Close()
    await ds_bwtb.Close()
    await ds_bvibe.Close()
    await adi_client.Stop()


if __name__ == "__main__":
    asyncio.run(async_main())
