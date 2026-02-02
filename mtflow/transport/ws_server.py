from __future__ import annotations
from typing import TYPE_CHECKING, TypeAlias, TypedDict, Any
if TYPE_CHECKING:
    from litestar.channels import ChannelsPlugin, Subscriber
    from mtflow.enums.event import EventStruct, FullChannelName
    ClientId: TypeAlias = str
    WebSocketId: TypeAlias = str
    class DataDict(TypedDict):
        event: Event
        data: dict

import time
import asyncio
import logging

from msgspec import json, convert, DecodeError, EncodeError
from litestar import WebSocket

from mtflow.enums.event import Event


class WebSocketServer:
    def __init__(self, channels_plugin: ChannelsPlugin):
        self._logger = logging.getLogger('mtflow')
        # use litestar's channels plugin to manage subscriptions
        self._channels_plugin: ChannelsPlugin = channels_plugin
        self._websockets: list[WebSocket] = []
        self._client_ids: dict[WebSocketId, ClientId] = {}  # map id(ws) -> client_id
        self._subscribers: dict[ClientId, Subscriber] = {}
        self._subscriptions: dict[ClientId, list[FullChannelName]] = {}
        self._encoder = json.Encoder()
        self._decoder = json.Decoder()
        self._forward_tasks: dict[ClientId, asyncio.Task] = {}
        
    async def start(self):
        """Start background tasks"""
        pass
        
    async def stop(self):
        """Cleanup all tasks"""
        # Cancel all forward tasks
        for client_id, task in list(self._forward_tasks.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._forward_tasks.clear()
    
    async def on_connected(self, ws: WebSocket):
        '''on client connected'''
        await ws.accept()
        self._add_websocket(ws)
        await self._send(ws, {'event': Event.connected, 'data': {'ts': time.time()}})

    async def on_disconnected(self, ws: WebSocket):
        '''on client disconnected'''
        # Cleanup subscription on disconnect
        await self._unsubscribe(ws)
        self._remove_websocket(ws)
        if ws.connection_state != 'disconnect':
            await self._send(ws, {'event': Event.disconnected, 'data': {'ts': time.time()}})
            await ws.close()
    
    def _add_websocket(self, ws: WebSocket):
        if ws in self._websockets:
            raise ValueError(f'ws {ws} already in server')
        self._websockets.append(ws)
        client_id = f"client_{len(self._websockets)}"
        self._client_ids[id(ws)] = client_id
        self._logger.debug(f'added ws {client_id}')
    
    def _remove_websocket(self, ws: WebSocket):
        if ws not in self._websockets:
            raise ValueError(f'ws {ws} not in server')
        self._websockets.remove(ws)
        client_id = self._client_ids.pop(id(ws), None)
        self._logger.debug(f'removed ws {client_id}')
    
    def _get_client_id(self, ws: WebSocket) -> ClientId:
        client_id = self._client_ids.get(id(ws), None)
        if not client_id:
            self._logger.error(f'no client id found for ws {id(ws)}')
            return 'client_UNKNOWN'
        return client_id

    async def _subscribe(self, ws: WebSocket, channels: list[str]) -> Subscriber:
        client_id = self._get_client_id(ws)
        existing_channels = self._subscriptions.get(client_id, [])
        if existing_channels:
            await self._unsubscribe(ws, channels=existing_channels)
        all_channels = list(set(existing_channels + channels))
        subscriber: Subscriber = await self._channels_plugin.subscribe(all_channels)
        self._subscribers[client_id] = subscriber
        self._subscriptions[client_id] = all_channels
        # Spawn forward task
        self._forward_tasks[client_id] = asyncio.create_task(self._forward_data(ws, subscriber))
        return subscriber
    
    async def _unsubscribe(self, ws: WebSocket, channels: list[str] | None = None):
        client_id = self._get_client_id(ws)
        if client_id not in self._subscribers:
            return
        
        existing_channels = self._subscriptions.get(client_id, [])
        remove_channels = channels or existing_channels
        if not remove_channels:
            return
        remaining_channels = set(existing_channels) - set(remove_channels)

        # Cancel forward task first
        if task := self._forward_tasks.pop(client_id, None):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        subscriber: Subscriber = self._subscribers[client_id]
        # remove all existing channels first
        await self._channels_plugin.unsubscribe(subscriber, channels=existing_channels)
        self._subscribers.pop(client_id)
        self._subscriptions.pop(client_id)
        # re-subscribe to remaining channels
        if remaining_channels:
            await self._subscribe(ws, channels=list(remaining_channels))

    async def _send(self, ws: WebSocket, data: DataDict):
        client_id = self._get_client_id(ws)
        try:
            data_struct: EventStruct = convert(data, type=Event[data['event']].event_class)
            data_bytes = self._encoder.encode(data_struct)
            await ws.send_bytes(data_bytes)
            self._logger.debug(f'sent {data} to {client_id}')
        except EncodeError:
            self._logger.exception(f'error encoding {data} to {client_id}:')
        except Exception:
            self._logger.exception(f'error sending {data} to {client_id}:')
        
    async def recv(self, ws: WebSocket) -> EventStruct | None:
        client_id = self._get_client_id(ws)
        try:
            data_bytes: bytes = await ws.receive_bytes()
            
            data: DataDict | Any = self._decoder.decode(data_bytes)
            self._logger.debug(f'received {data} from {client_id}')

            # if user sends data that doesn't follow the DataDict schema, return None
            if not isinstance(data, dict):
                self._logger.debug(f'received non-dict data {data} from {client_id}, returning None')
                return None

            data_struct: EventStruct = convert(data, type=Event[data['event']].event_class)

            # Start handling data events
            match data_struct.event:
                case Event.ping:
                    await self._send(ws, {'event': Event.pong, 'data': {'ts': time.time()}})
                # TODO: check if channels are valid in subscribe/unsubscribe, if subscription fails, send data with "error" field (see event.py)
                case Event.subscribe:
                    channels = data_struct.data.channels
                    await self._subscribe(ws, channels)
                    # send message to client to indicate subscribe success 
                    await self._send(ws, {'event': Event.subscribe, 'data': {'channels': channels, 'ts': time.time()}})
                case Event.unsubscribe:
                    channels = data_struct.data.channels
                    await self._unsubscribe(ws, channels)
                    # send message to client to indicate unsubscribe success
                    await self._send(ws, {'event': Event.unsubscribe, 'data': {'channels': channels, 'ts': time.time()}})
                case Event.data | Event.engine | Event.fund:
                    # use litestar's channels plugin to publish data to all subscribers
                    self._channels_plugin.publish(data_bytes, channels=data_struct.data.channel)
                case _:
                    self._logger.error(f'Unknown event {data_struct} from {client_id}')
 
            return data_struct
        # NOTE: do NOT catch all errors here, let it propagate up to handler so the while true loop in app.py handler() can exit
        except DecodeError:
            self._logger.debug(f'error decoding {data_bytes} from {client_id}:')
        except KeyError:
            self._logger.debug(f'no "event" field or invalid event type found in {data}, returning None')

    async def _forward_data(self, ws: WebSocket, subscriber: Subscriber):
        """Forward channel data to this WebSocket"""
        client_id = self._get_client_id(ws)
        try:
            # NOTE: A while True loop is already inside iter_events()
            async for data_bytes in subscriber.iter_events():
                await ws.send_bytes(data_bytes)
                self._logger.debug(f'forwarded {data_bytes} to {client_id}')
        except asyncio.CancelledError:
            self._logger.debug(f'forward data cancelled for {client_id}')
        except Exception:
            self._logger.exception(f'forward data error for {client_id}:')
        finally:
            # Cleanup on task exit (whether cancelled or errored)
            self._forward_tasks.pop(client_id, None)
