from __future__ import annotations
from typing import Callable, Awaitable, Any, TYPE_CHECKING
if TYPE_CHECKING:
    from msgspec import Struct

import os
import asyncio
import time
import logging

from websockets.asyncio.client import ClientConnection as WebSocket
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    ConnectionClosedOK,
)
from websockets.protocol import State

from mtflow.enums.event import Event


class WebSocketClient:
    CHECK_FREQ = 10  # check connection frequency (in seconds)
    PING_FREQ = 20  # application-level ping to server frequency (in seconds)
    NO_PONG_TOLERANCE = 60  # no pong period tolerance (in seconds)
    MSG_QUEUE_MAXSIZE = 1000  # max size of the message queue

    def __init__(self, name: str='ws_client', url: str='', callback: Callable[[dict], Any | Awaitable[Any]] | None = None):
        from msgspec import json
        
        self.name = name
        self.logger = logging.getLogger('mtflow')
        self.ws: WebSocket | None = None
        self.url: str = url or self._get_default_url()
        self._callback: Callable[[dict], Any | Awaitable[Any]] | None = callback
        self._encoder = json.Encoder()
        self._decoder = json.Decoder()
        self._recv_task: asyncio.Task | None = None
        self._monitor_task: asyncio.Task | None = None
        self._msg_queue: asyncio.Queue | None = None
        self._last_ping_ts = time.time()
        self._last_pong_ts = time.time()
    
    async def __aenter__(self) -> WebSocketClient:
        """
        Async context manager entry. Enables `async with` syntax.

        Usage:
            async with WebSocketClient() as client:
                await client.send(data)
            # auto-disconnects when exiting the block
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Async context manager exit. Auto-disconnects when leaving `async with` block.
        """
        await self.disconnect()

    def __aiter__(self) -> WebSocketClient:
        """
        Async iterator entry. Enables `async for` syntax.

        Usage:
            await client.connect(url)
            async for msg in client:
                process(msg)
        """
        return self

    async def __anext__(self) -> dict:
        """
        Async iterator next. Called on each iteration of `async for`.

        Returns the next message from the server.
        Raises StopAsyncIteration when connection closes (ends the loop).
        """
        msg_queue = self._get_msg_queue()
        data = await msg_queue.get()
        if data is None:  # sentinel from disconnect()
            raise StopAsyncIteration
        return data
    
    def _get_msg_queue(self) -> asyncio.Queue:
        if self._msg_queue is None:
            self._msg_queue = asyncio.Queue(maxsize=self.MSG_QUEUE_MAXSIZE)
        return self._msg_queue
    
    def _get_default_url(self) -> str:
        from mtflow.transport.app import VERSION as ws_server_version
        
        host = os.getenv("MTFLOW_SERVER_HOST", "localhost")
        port = os.getenv("MTFLOW_SERVER_PORT", "8000")
        scheme = 'ws://' if host in ['localhost', '127.0.0.1'] else 'wss://'
        url = f'{scheme}{host}:{port}'
        if not url.endswith(f'/{ws_server_version}'):
            url = f'{url}/{ws_server_version}'
        return url
        
    @property
    def is_connected(self) -> bool:
        return self.ws is not None and self.ws.state == State.OPEN
    
    async def ping(self):
        await self.send({'event': Event.ping})
    
    async def subscribe(self, channels: list[str]):
        await self.send({'event': Event.subscribe, 'data': {'channels': channels}})
    
    async def unsubscribe(self, channels: list[str]):
        await self.send({'event': Event.unsubscribe, 'data': {'channels': channels}})
    
    async def connect(self):
        from websockets.asyncio.client import connect
        if self.is_connected:
            self.logger.warning(f'{self.name} is already connected')
            return
        try:
            self.logger.debug(f'{self.name} is connecting to {self.url}')
            self.ws: WebSocket = await connect(self.url)
            # reset timestamps
            self._last_ping_ts = time.time()
            self._last_pong_ts = time.time()
            # create tasks
            if not self._recv_task or self._recv_task.done():
                self._recv_task = asyncio.create_task(self._recv_loop())
            if not self._monitor_task or self._monitor_task.done():
                self._monitor_task = asyncio.create_task(self._monitor_loop())
            self.logger.debug(f'{self.name} is connected')
        except Exception:
            self.logger.exception(f'{self.name} failed to connect to {self.url}:')
    
    async def disconnect(self, reason: str='', cancel_tasks: bool=True):
        if cancel_tasks and self._monitor_task:
            self._monitor_task.cancel()
            try: 
                await self._monitor_task
            except asyncio.CancelledError: 
                pass
            self._monitor_task = None
            
        if cancel_tasks and self._recv_task:
            self._recv_task.cancel()
            try: 
                await self._recv_task
            except asyncio.CancelledError: 
                pass
            self._recv_task = None
        
        if cancel_tasks and self._msg_queue:
            await self._msg_queue.put(None)  # signal to iterator to stop
        
        if self.ws:
            self.logger.warning(f'{self.name} is disconnecting (state={self.ws.state.name}), {reason=}')
            await self.ws.close(code=1000, reason=reason)
            await self.ws.wait_closed()
            self.ws: WebSocket | None = None
            self.logger.warning(f'{self.name} is disconnected')
            
    async def send(self, data: dict):
        if not self.is_connected:
            raise ConnectionClosedError(rcvd=None, sent=None)
        EventClass: type[Struct] = Event[data['event']].event_class
        event: Struct = EventClass(**data)
        await self.ws.send(self._encoder.encode(event))
        self.logger.debug(f'{self.name} sent {event}')
    
    async def _recv(self) -> dict:
        if not self.is_connected:
            raise ConnectionClosedError(rcvd=None, sent=None)
        data: bytes = await self.ws.recv()
        data: dict = self._decoder.decode(data)
        if data['event'] == Event.pong:
            # server_time = data['data']['ts']
            self._last_pong_ts = time.time()
        self.logger.debug(f'{self.name} received {data}')
        return data
    
    # NOTE: NO SLEEP HERE - Max Performance
    async def _recv_loop(self):
        '''Receive loop for receiving messages from the server and calling user's callback'''
        while True:
            try:
                data: dict = await self._recv()

                if self._callback:
                    # call user's callback
                    result = self._callback(data)
                    if asyncio.iscoroutine(result):
                        await result

                if self._msg_queue:
                    if self._msg_queue.full():
                        self.logger.warning(f"Message queue is full, dropping oldest message - consider increasing maxsize (current: {self.MSG_QUEUE_MAXSIZE}) or improving consuming speed")
                        self._msg_queue.get_nowait()  # Remove oldest
                    await self._msg_queue.put(data)
            except ConnectionClosedOK:
                self.logger.debug(f"{self.name} closed normally")
                break
            except ConnectionClosedError as e:
                self.logger.error(f"{self.name} closed with error: {e}")
                break
            except ConnectionClosed as e:
                self.logger.error(f"{self.name} connection lost: {e}")
                break
            except Exception:
                self.logger.exception(f'{self.name} error receiving data:')
    
    async def _monitor_loop(self):
        assert self.CHECK_FREQ < self.PING_FREQ, f'this loop runs every {self.CHECK_FREQ} seconds, but pings server every {self.PING_FREQ} seconds'
        while True:
            now = time.time()
            disconnect_reason = ''
            if not self.is_connected:
                disconnect_reason = 'connection lost, reconnecting'
            elif now - self._last_pong_ts > self.NO_PONG_TOLERANCE:
                disconnect_reason = f'no pong for more than {self.NO_PONG_TOLERANCE} seconds, reconnecting'

            if disconnect_reason:
                await self.disconnect(reason=disconnect_reason, cancel_tasks=False)
                await self.connect()
            else:
                # ping server regularly
                if now - self._last_ping_ts > self.PING_FREQ:
                    try:
                        await self.ping()
                    except Exception:
                        self.logger.exception(f'{self.name} error pinging server:')
                    self._last_ping_ts = now

            await asyncio.sleep(self.CHECK_FREQ)


# TEMP
if __name__ == "__main__":
    async def main():
        client = WebSocketClient()
        await client.connect()
        # Keep alive for testing
        while True:
            await asyncio.sleep(1)
    
    asyncio.run(main())
    # data = json.encode({"type": "test", "message": "Hello, world!"})
    # await ws.send(data)
    # msg = await ws.recv()
    # print(f"received: {msg}")
