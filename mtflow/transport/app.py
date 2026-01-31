import os
import asyncio
import logging.config

import logfire
from litestar import Litestar, websocket, WebSocket
from litestar.channels import ChannelsPlugin, Subscriber
from litestar.handlers.websocket_handlers import websocket_listener
from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.logging import LoggingConfig
from litestar.exceptions import WebSocketDisconnect
# from redis.asyncio.client import Redis
# from litestar.channels.backends.redis import RedisChannelsPubSubBackend

from mtflow.config import setup_logging, get_logging_config


VERSION = "v1"
# FIXME:
SUPPORTED_CHANNELS = ['channel_1', 'channel_2']


# NOTE: logging.config.dictConfig will be called by litestar, override it
# the flow is: pass in litestar_logging_config to litestar, which will call logging.config.dictConfig
# and then pass litestar_logging_config back to our custom setup_logging function
# TODO: set env
logging.config.dictConfig = (
    lambda config: setup_logging(config, include_uvicorn=False, env=None)
)

mtflow_logging_config = get_logging_config()
litestar_logging_config = LoggingConfig(
    loggers=mtflow_logging_config['loggers'],
    handlers=mtflow_logging_config['handlers'],
    formatters=mtflow_logging_config['formatters'],
    filters=mtflow_logging_config['filters'],
    log_exceptions="always",
    configure_root_logger=False,
)


@websocket(f"/{VERSION}")
async def handler(socket: WebSocket, channels: ChannelsPlugin) -> None:
    # NOTE: socket is per connection, i.e. different sockets for different users
    try:
        logger = logging.getLogger('litestar')
        logger.warning('testing!')
        print(logger.name, logger.level, logger.handlers)
        print(f'socket_id: {id(socket)} connected')

        await socket.accept()
        while True:
            msg = await socket.receive_json(mode='binary')
            print(f'socket_id: {id(socket)} {msg=} (msg type: {type(msg)})')
            await asyncio.sleep(1)
    except WebSocketDisconnect as err:
        print(f'socket_id: {id(socket)} disconnected')


    # async with channels.start_subscription(["some_channel"]) as subscriber:
    #     await channels.put_subscriber_history(subscriber, ["some_channel"], limit=10)


app = Litestar(
    route_handlers=[handler],
    # on_startup=[on_startup],
    # on_shutdown=[stop_ws_server],
    logging_config=litestar_logging_config,
    plugins=[
        ChannelsPlugin(
            channels=SUPPORTED_CHANNELS,  # FIXME
            backend=MemoryChannelsBackend(history=20),
            # TODO: support redis backend
            # backend=RedisChannelsPubSubBackend(
            #     redis=Redis(
            #         host=os.getenv('REDIS_HOST', 'localhost'),
            #         port=int(os.getenv('REDIS_PORT', 6379)),
            #         db=0
            #     )
            # ),
            # TODO
            subscriber_max_backlog=1000,
            # dropping the oldest message in the backlog when a new one is added while the backlog is full
            subscriber_backlog_strategy="dropleft",
            arbitrary_channels_allowed=False,
        )
    ],
)
