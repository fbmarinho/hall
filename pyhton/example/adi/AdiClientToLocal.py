from __future__ import annotations
import asyncio
import random
import struct
import traceback
from typing import TYPE_CHECKING
import adi.AdiClient
import adi.AdiCommands
from adi.AdiEnums import ClientState, ConnectionState, IdentificationState, RecordOpenModes
from adi.AdiDefinitions import AdiDataSetReader, AdiProcessClientIdentification, AdiResponse

if TYPE_CHECKING:
    from adi.AdiServer import AdiServer


class BufferedResponseToSend:
    def __init__(self, data: bytearray):
        self.bytes_to_send = data
        self.total_bytes = len(self.bytes_to_send)
        self.bytes_sent = 0

    def GetNextBytesToSend(self):
        total_bytes = adi.AdiClient.AdiClient.CLIENT_BUFFER_SIZE if self.total_bytes - \
            self.bytes_sent > adi.AdiClient.AdiClient.CLIENT_BUFFER_SIZE else self.total_bytes - self.bytes_sent
        return self.bytes_to_send[self.bytes_sent:self.bytes_sent + total_bytes]

    def SendingSucceeded(self, bytes_sent):
        self.bytes_sent += bytes_sent
        return self.SendingComplete()

    def SendingComplete(self):
        return self.bytes_sent >= self.total_bytes


class AdiClientToLocal(adi.AdiClient.AdiClient, AdiProcessClientIdentification):
    def __init__(self, server: AdiServer, loop: asyncio.AbstractEventLoop = None, reader: asyncio.StreamReader = None, writer: asyncio.StreamWriter = None):
        adi.AdiClient.AdiClient.__init__(self, loop=loop, reader=reader, writer=writer, realtime=False)
        AdiProcessClientIdentification.__init__(self)

        self.server:AdiServer = server
        self.client_rt = None

        self.current_step = ClientState.IDLE
        self.identification_state = IdentificationState.INITIALIZING

        self.realtime_id = random.randint(0x100000, 0xff00ff00)
        self.realtime_transferred = False

        self.buffered_response:BufferedResponseToSend = None
        self.current_request:adi.AdiCommands.AdiCommands.AdiCommand = None
        self.number_unknown_commands = 0
        self.command_processed_event = asyncio.Event()

        self.opened_datasets:list[AdiDataSetReader] = []
        self.next_dataset_id = 1

        self.notify_well_change = False
        self.notify_run_change = False

        if writer != None:
            self.connected = True
            self.connection_state = ConnectionState.CONNECTED

        if loop != None:
            self.running = True
            self.task = self.loop.create_task(self.__ClientProcess())
            self.task_recv_data = self.loop.create_task(self.__ReceivingData())

        if server != None:
            server.add_event_listener("WELL_CHANGED", self.__OnWellChange)
            server.add_event_listener("RUN_CHANGED", self.__OnRunChange)

    async def __OnWellChange(self, _):
        if self.realtime and self.notify_well_change and self.writer_rt != None:
            msg:AdiResponse = AdiResponse(param=0xa066, data=struct.pack("<II", 2, 3))
            bytes_to_send = msg.GetBytes()
            self.writer_rt.write(bytes_to_send)
            try:
                await self.writer_rt.drain()
            except asyncio.CancelledError:
                raise

            bytes_sent = len(bytes_to_send)
            self._AddToBandwidthStatistics(bytes_sent, False, True)

    async def __OnRunChange(self, _):
        if self.realtime and self.notify_run_change and self.writer_rt != None and self.writer_rt.is_closing() == False:
            msg:AdiResponse = AdiResponse(param=0xa066, data=struct.pack("<II", 2, 3))
            bytes_to_send = msg.GetBytes()
            self.writer_rt.write(bytes_to_send)
            try:
                await self.writer_rt.drain()
            except asyncio.CancelledError:
                raise

            bytes_sent = len(bytes_to_send)
            self._AddToBandwidthStatistics(bytes_sent, False, True)

    async def Disconnect(self):
        await super()._Disconnect()
        self.running = False

        if self.task != None:
            self.task.cancel()
            await self.task

        if self.task_recv_data != None:
            self.task_recv_data.cancel()
            await self.task_recv_data

        self.buffered_response = None
        self.current_request = None

    async def __ReceivingData(self):
        data_buffer = b''
        while self.connected:
            try:
                data_buffer = await self._ReceiveDataToBuffer(self.reader, data_buffer, False)
                
                # Disconnection from client
                if not self.connected:
                    break

                # Data received, but we will only activate
                # the event if we have a complete message
                has_new_msg = True
                while has_new_msg:
                    command:adi.AdiCommands.AdiCommands.AdiCommand
                    [has_new_msg, data_buffer, command] = self._GetFullMessageReceived(data_buffer, False)

                    # If we have a new message, we trigger the event
                    if has_new_msg:
                        self.current_request = command
                        self.data_received_event.set()

                        # Wait for the command to be processed before
                        # checking if there are new messages on the buffer
                        await self.command_processed_event.wait()
                        self.command_processed_event.clear()

            except asyncio.CancelledError:
                break
            except Exception as ex:
                # socket was closed from another thread
                print("Error receiving data: ", ex)
                break

    async def __ClientProcess(self):
        while self.connected:
            try:
                if self.current_step == ClientState.IDLE:
                    # Create a task that waits for event1 or event2
                    await self._WaitForFirstEvent(self.data_received_event, self.disconnection_event)
                    
                    if self.disconnection_event.is_set():
                        self.disconnection_event.clear()

                    elif self.data_received_event.is_set():
                        self.data_received_event.clear()
                        self.current_step = ClientState.IDENTIFYING_MSG

                elif self.current_step == ClientState.IDENTIFYING_MSG:
                    if self.current_request.IsValid():
                        self.current_step = ClientState.PROCESSING
                        self.number_unknown_commands = 0
                    else:
                        print(f"========= UNKNOWN COMMAND ({hex(self.current_request.code)}) ==========")
                        self.number_unknown_commands += 1

                        if self.number_unknown_commands >= 3:
                            await self.ChangeConnectionStatus(ConnectionState.CLOSING)
                        else:
                            # Sending error response to the client
                            self.current_step = ClientState.BUILDING_RESPONSE
                elif self.current_step == ClientState.PROCESSING:
                    processed = False
                    if self.identification_state != IdentificationState.COMPLETE:
                        processed = await self.__HandleIdentification()
                    else:
                        processed = await self.__HandleRequest()

                    if processed:
                        if self.current_request.response_expected:
                            self.current_step = ClientState.BUILDING_RESPONSE
                        else:
                            self.buffered_response = None
                            self.current_request = None
                            self.command_processed_event.set()
                            self.current_step = ClientState.IDLE

                elif self.current_step == ClientState.BUILDING_RESPONSE:
                    msg_built = await self.__BuildingResponse()
                    if msg_built:
                        self.current_step = ClientState.SENDING
                    
                elif self.current_step == ClientState.SENDING:
                    sending_complete = await self.__SendResponse()
                    if sending_complete:
                        self.buffered_response = None
                        self.current_request = None
                        self.command_processed_event.set()
                        self.current_step = ClientState.IDLE

            except asyncio.CancelledError:
                break
            except Exception as e:
                traceback.print_exc()
                print("Error in client local process: ", e)

        self.server.RemoveClient(self)

    async def __HandleIdentification(self):
        if self.identification_state == IdentificationState.INITIALIZING and self.current_request.name == "CMD_HANDSHAKE":
            self.identification_state = IdentificationState.SENDING_CREDENTIALS

        elif self.identification_state == IdentificationState.SENDING_CREDENTIALS and self.current_request.name == "CMD_IDENTIFY":
            req: adi.AdiCommands.AdiCommands.Identification = self.current_request
            if req.is_valid:
                self.id_client = req.id_client
                self.exec_name = req.exec_name
                self.host_name = req.host_name
                self.user_name = req.user_name
                self.identification_state = IdentificationState.COMPLETE
            # else:
            #     self.ChangeConnectionStatus(ConnectionState.CLOSING)

        else:
            # self.ChangeConnectionStatus(ConnectionState.CLOSING)
            # return False
            self.current_request.is_valid = False

        return True

    async def __HandleRequest(self) -> bool:
        # So far, no command to be executed requires too long
        # to be performed, so maybe change response to boolean
        # and return True only when finished
        await self.current_request.ExecuteCommand()
        return True

    async def __BuildingResponse(self) -> bool:
        adi_response = await self.current_request.GetResponseBytes()
        self.buffered_response = BufferedResponseToSend(adi_response.GetBytes())
        return True

    async def __SendResponse(self) -> bool:
        bytes_to_send = self.buffered_response.GetNextBytesToSend()
        self.writer.write(bytes_to_send)
        try:
            await self.writer.drain()
        except asyncio.CancelledError:
            raise
        
        bytes_sent = len(bytes_to_send)

        # Add to statistics
        self._AddToBandwidthStatistics(bytes_sent, False, False)

        return self.buffered_response.SendingSucceeded(bytes_sent)

    async def SendRealtimeData(self, adi_dataset:AdiDataSetReader, data_bytes:bytearray):
        if self.writer_rt != None and self.writer_rt.is_closing() == False:
            msg = AdiResponse(param=0xa064, data=data_bytes)
            bytes_to_send = msg.GetBytes()
            self.writer_rt.write(bytes_to_send)
            try:
                await self.writer_rt.drain()
            except asyncio.CancelledError:
                raise

            bytes_sent = len(bytes_to_send)
            self._AddToBandwidthStatistics(bytes_sent, False, True)

    def AddDataSetReader(self, adi_dataset:AdiDataSetReader):
        adi_dataset.id = self.next_dataset_id
        self.next_dataset_id += 1
        self.opened_datasets.append(adi_dataset)
    
    def CloseDataSet(self, adi_dataset_id):
        for adi_dataset in self.opened_datasets:
            if adi_dataset.id == adi_dataset_id:
                # Remove object from the list
                self.opened_datasets.remove(adi_dataset)
                self.server.DataSetClose(self, adi_dataset)
                return True
        return False

    def GetAdiDataSetReader(self, adi_dataset_id):
        for adi_dataset in self.opened_datasets:
            if adi_dataset.id == adi_dataset_id:
                return adi_dataset
        return None
