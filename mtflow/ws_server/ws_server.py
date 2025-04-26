import time
import datetime
import asyncio
from asyncio import CancelledError
from collections import defaultdict
from contextlib import suppress

from websockets.exceptions import ConnectionClosed
from litestar.exceptions import WebSocketDisconnect
from litestar.channels import ChannelsPlugin, Subscriber
from litestar import WebSocket


class WebSocketServer:
    _NO_PING_TOLERANCE = 180  # in seconds
    
    def __init__(self, logger, channels_plugin: ChannelsPlugin):
        self._logger = logger
        self._channels_plugin = channels_plugin
        self._channel_sockets = defaultdict(set)  # {channel: {socket1, socket2, ...}}
        self._socket_channel_subscribers = defaultdict(dict)  # {socket: {channel: subscriber}}
        self._publish_task = None
        self._monitor_task = None
        self._last_ping_ts = {}
    
    def get_socket_channels(self, socket: WebSocket) -> list[str]:
        return list(self._socket_channel_subscribers[socket].keys())
    
    def start(self):
        if not self._publish_task:
            self._publish_task = asyncio.create_task(self._publish())
        if not self._monitor_task:
            self._monitor_task = asyncio.create_task(self._monitor())
        self._logger.debug('started ws server')
    
    async def stop(self):
        for task in [self._publish_task, self._monitor_task]:
            if not task.done():
                task.cancel()
            with suppress(CancelledError):
                await task
        self._publish_task = None
        self._monitor_task = None
        self._logger.debug('stopped ws server')
    
    # TODO: set up zeromq of trade engine
    async def _publish(self):
        try:
            n = 1
            while True:
                n += 1
                now = datetime.datetime.now()
                channel_num = n % 2 + 1
                msg = {'message': now.strftime('%Y-%m-%d %H:%M:%S')}
                self._channels_plugin.publish(msg, f'channel_{channel_num}')
                # print(f'published {now.strftime("%Y-%m-%d %H:%M:%S")} to channel_{channel_num}')
                await asyncio.sleep(1)
        except CancelledError:
            self._logger.debug('stopped publishing')
        except:
            self._logger.exception('publish exception:')
    
    async def _monitor(self):
        try:
            while True:
                for socket in self._last_ping_ts:
                    if time.time() - self._last_ping_ts[socket] > self._NO_PING_TOLERANCE:
                        if socket.connection_state != 'disconnect':
                            await socket.close(reason=f'No ping for {self._NO_PING_TOLERANCE} seconds')
                            self._logger.debug(f'closed {socket} due to no ping for {self._NO_PING_TOLERANCE} seconds')
                await asyncio.sleep(1)
        except CancelledError:
            self._logger.debug('stopped monitoring')
        except:
            self._logger.exception('monitor exception:')
    
    async def subscribe(self, socket: WebSocket, channel: str) -> bool:
        is_success = False
        if socket not in self._channel_sockets[channel]:
            subscriber = await self._channels_plugin.subscribe(channel)
            self._channel_sockets[channel].add(socket)
            self._socket_channel_subscribers[socket][channel] = subscriber
            asyncio.create_task(self._worker(socket, subscriber))
            is_success = True
            self._logger.debug(f'{socket=} subscribed to {channel}')
        return is_success
    
    async def unsubscribe(self, socket: WebSocket, channel: str) -> bool:
        is_success = False
        if socket in self._channel_sockets[channel]:
            subscriber = self._socket_channel_subscribers[socket][channel] 
            self._channel_sockets[channel].remove(socket)
            # NOTE: this will send a None to the subscriber's queue,
            # which will break the iter_events() loop and kill the _worker() task
            await self._channels_plugin.unsubscribe(subscriber, channel)
            is_success = True
            self._logger.debug(f'{socket=} unsubscribed to {channel}')
        return is_success
    
    async def _worker(self, socket: WebSocket, subscriber: Subscriber):
        # NOTE: A while True loop is already inside iter_events()
        async for msg in subscriber.iter_events():
            try:
                await socket.send_text(msg)
                self._logger.debug(f'{socket=} {msg=}')
            except WebSocketDisconnect:
                self._logger.debug('WebSocketDisconnect, breaking worker loop')
                break
            except ConnectionClosed:
                self._logger.debug('ConnectionClosed, breaking worker loop')
                break
            except:
                self._logger.exception('work exception:')
                break
            
    def ping(self, socket: WebSocket):
        self._last_ping_ts[socket] = time.time()
        self._logger.debug(f'{socket=} pinged at {self._last_ping_ts[socket]}')