import asyncio
import adi.AdiClientToRemote
import adi.AdiDefinitions
import adi.AdiEnums

class AdiUtils:
    @staticmethod
    async def PopulateInsite(loop:asyncio.AbstractEventLoop, host:str, well:str, run_number:int, record:str, description:str, variables:list, data_points:list, clear_previous_data:bool):
        adi_client:adi.AdiClientToRemote.AdiClientToRemote = None
        ds:adi.AdiDefinitions.AdiDataSetReader = None
        try:
            adi_client = adi.AdiClientToRemote.AdiClientToRemote(loop=loop, host=host, realtime=False)
            for i in range(50):
                if adi_client.connection_state == adi.AdiEnums.ConnectionState.CONNECTED: break
                await asyncio.sleep(0.1)
            if adi_client.connection_state != adi.AdiEnums.ConnectionState.CONNECTED:
                return {"Success": False, "Error": "Connection to remote server failed"}

            open_mode = adi.AdiEnums.RecordOpenModesInsite.ReadWrite | adi.AdiEnums.RecordOpenModesInsite.Create \
                | (adi.AdiEnums.RecordOpenModesInsite.NoTruncate if not clear_previous_data else 0)
            ds = await adi_client.OpenDataSet(well=well, run_number=run_number, record=record, description=description, variables_list=variables, open_mode_value=open_mode)
            if ds == None:
                return {"Success": False, "Error": "It was not possible to open the dataset."}

            result = await ds.WriteLines(write_mode_value=adi.AdiEnums.DataSetWriteModes.Insert, lines=data_points)
            return result
        except Exception as ex:
            return {"Success": False, "Error": str(ex)}
        finally:
            if ds != None: await ds.Close()
            if adi_client != None: await adi_client.Stop()
