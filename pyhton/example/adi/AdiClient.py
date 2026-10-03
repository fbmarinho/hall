from __future__ import annotations
from asyncio import StreamReader, StreamWriter, AbstractEventLoop
import asyncio
import struct
import time

from adi.AdiEnums import ClientState, ConnectionState
from adi.EventEmitter import EventEmitter

class AdiClient(EventEmitter):
    CLIENT_BUFFER_SIZE = 1024 * 1024 * 20
    CLIENT_MAX_BYTES_RECEIVED = 1024 * 1024 * 100

    def __init__(self, loop: AbstractEventLoop = None, reader: StreamReader = None, writer: StreamWriter = None, realtime: bool = False):
        super().__init__()

        self.loop: AbstractEventLoop = loop

        # stream reader for client socket
        self.reader: StreamReader = reader
        # stream writer for client socket
        self.writer: StreamWriter = writer
        self.reader_rt: StreamReader = None       # stream reader for RT socket
        self.writer_rt: StreamWriter = None       # stream writer for RT socket

        self.connected: bool = False
        self.realtime: bool = realtime
        self.realtime_id: int = None
        self.connection_state: ConnectionState = ConnectionState.CLOSED
        self.current_step: ClientState = ClientState.IDLE

        self.data_received_event = asyncio.Event()
        self.disconnection_event = asyncio.Event()

        self.full_buffer = b''

        self.total_bytes_received = 0
        self.total_bytes_sent = 0
        self.total_bytes_sent_rt = 0
        self.total_bytes_received_rt = 0

        self.max_seconds_bandwidth = 360
        self.history_timestamp_last_sample = 0
        self.history_download_per_second = [0] * self.max_seconds_bandwidth
        self.history_upload_per_second = [0] * self.max_seconds_bandwidth

        self.running: bool = False
        self.is_closing: bool = False
        self.task: asyncio.Task = None

    def _GetFullMessageReceived(self, full_buffer, is_response_msg: bool):
        # If there is still a response being processed,
        # return false, to not overwrite the response
        len_buffer = len(full_buffer)
        if len_buffer >= 16:
            [data_length] = struct.unpack_from("<I", full_buffer, 12)
            len_response = data_length + 16
            if len_buffer >= len_response:
                message = None
                from adi.AdiDefinitions import AdiResponse, MessageHeader
                if is_response_msg:
                    message = AdiResponse.LoadFromBytes(
                        full_buffer[:len_response])
                else:
                    from adi.AdiCommands import AdiCommands
                    message = AdiCommands.IdentifyCommandFromHeader(
                        self, MessageHeader(data=full_buffer), full_buffer)

                full_buffer = full_buffer[len_response:]
                return [True, full_buffer, message]
        return [False, full_buffer, None]

    def _AddToBandwidthStatistics(self, number_bytes, is_download, realtime):
        self._UpdateTimeStatisticsArrays()
        
        if is_download:
            if realtime: self.total_bytes_received_rt += number_bytes
            else: self.total_bytes_received += number_bytes
            self.history_download_per_second[-1] += number_bytes
        else:
            if realtime:
                self.total_bytes_sent_rt += number_bytes
            else:
                self.total_bytes_sent += number_bytes
            self.history_upload_per_second[-1] += number_bytes

    def _UpdateTimeStatisticsArrays(self):
        current_time = int(time.time())
        if current_time == self.history_timestamp_last_sample:
            return

        diff_time = current_time - self.history_timestamp_last_sample

        if diff_time >= self.max_seconds_bandwidth:
            self.history_download_per_second = [0] * self.max_seconds_bandwidth
            self.history_upload_per_second = [0] * self.max_seconds_bandwidth
        else:
            self.history_download_per_second = self.history_download_per_second[diff_time:] + [0] * diff_time
            self.history_upload_per_second = self.history_upload_per_second[diff_time:] + [0] * diff_time

        self.history_timestamp_last_sample = current_time

    def GetHistoricBandwidthPerSecond(self, is_download:bool):
        self._UpdateTimeStatisticsArrays()
        if is_download: return self.history_download_per_second
        else: return self.history_upload_per_second

    def GetAverageBandwidth(self, number_seconds=10):
        if number_seconds == 0: return 0
        if number_seconds > self.max_seconds_bandwidth:
            raise Exception("Number of seconds is too big")
        arr1 = self.history_download_per_second[-number_seconds:]
        arr2 = self.history_upload_per_second[-number_seconds:]
        avg = (sum(arr1) / len(arr1)) + (sum(arr2) / len(arr2))
        return avg

    async def _Disconnect(self):
        if self.is_closing: return
        self.is_closing = True
        self.connected = False
        try:
            if self.connection_state == ConnectionState.CLOSED:
                return

            if self.connection_state != ConnectionState.CLOSING:
                await self.ChangeConnectionStatus(ConnectionState.CLOSING)

            if self.writer_rt != None:
                self.writer_rt.close()
                await self.writer_rt.wait_closed()

            if self.writer != None:
                self.writer.close()
                await self.writer.wait_closed()

        except asyncio.CancelledError as ex:
            raise
        except Exception as ex:
            pass
        except:
            pass
        finally:
            await self.ChangeConnectionStatus(ConnectionState.CLOSED)
            self.disconnection_event.set()
            self.is_closing = False

    async def ChangeConnectionStatus(self, new_status: ConnectionState):
        if self.connection_state != new_status:
            self.connection_state = new_status
            await super().emit('connection_changed')

    async def _ReceiveDataToBufferNonBlocking(self, s: asyncio.StreamReader, full_buffer:bytearray, realtime:bool):
        try:
            data = b''
            if not self.running or not self.connected: return data

            # this will try to read bytes or will timeout after 0.1 seconds
            future = s.read(AdiClient.CLIENT_BUFFER_SIZE)
            data = await asyncio.wait_for(future, timeout=0.01)
            # data = await s.read(AdiClient.CLIENT_BUFFER_SIZE)
            if len(data) == 0:
                # Socket has closed smoothly
                await self._Disconnect()
                full_buffer = b''
            else:
                # If the amount of bytes in buffer is too big,
                # we have a problem and we'll close the connection
                if len(data) + len(full_buffer) >= AdiClient.CLIENT_MAX_BYTES_RECEIVED:
                    await self._Disconnect()
                    full_buffer = b''
                else:
                    self._AddToBandwidthStatistics(len(data), True, realtime)
                    full_buffer += data
            return full_buffer
        except asyncio.TimeoutError:
            return data
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            # socket was closed from another thread
            await self._Disconnect()
            return b''

    async def _ReceiveDataToBuffer(self, s: asyncio.StreamReader, full_buffer:bytes, realtime:bool)->bytes:
        try:
            data = await s.read(AdiClient.CLIENT_BUFFER_SIZE)
            if len(data) == 0:
                # Socket has closed smoothly
                self.connected = False
                await self._Disconnect()
                return b''
            else:
                # If the amount of bytes in buffer is too big,
                # we have a problem and we'll close the connection
                if len(data) + len(full_buffer) >= AdiClient.CLIENT_MAX_BYTES_RECEIVED:
                    await self._Disconnect()
                    return b''
                else:
                    self._AddToBandwidthStatistics(len(data), True, realtime)
                    return full_buffer + data
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            # socket was closed from another thread
            await self._Disconnect()
            return b''

    async def _WaitForFirstEvent(self, event1:asyncio.Event, event2:asyncio.Event):
        # Create tasks for event1 and event2
        task1 = asyncio.create_task(event1.wait())
        task2 = asyncio.create_task(event2.wait())

        try:
            # Wait for the first event to complete
            done, pending = await asyncio.wait(
                [task1, task2],
                return_when=asyncio.FIRST_COMPLETED  # Resumes as soon as the first event is set
            )

            # Cancel the pending task after the first event is completed
            for task in pending:
                task.cancel()  # Cancel the task that is still pending

        except asyncio.CancelledError:
            # Handle the cancellation (propagate after cleaning up)
            for task in [task1, task2]:
                if not task.done():
                    task.cancel()  # Ensure both tasks are canceled if the outer task is canceled
            raise  # Re-raise the CancelledError to propagate it
