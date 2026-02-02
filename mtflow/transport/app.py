from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from litestar.datastructures import State

import os
import time
import asyncio
import logging.config

import logfire
from litestar import Litestar, websocket, WebSocket
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.logging import LoggingConfig
from litestar.exceptions import WebSocketDisconnect
# from redis.asyncio.client import Redis
# from litestar.channels.backends.redis import RedisChannelsPubSubBackend

from mtflow.config import setup_logging, get_logging_config
from mtflow.transport.ws_server import WebSocketServer


VERSION = "v1"


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


async def on_startup(app: Litestar) -> None:
    channels_plugin = app.plugins.get(ChannelsPlugin)
    ws_server = WebSocketServer(channels_plugin)
    app.state.ws_server = ws_server
    await ws_server.start()


async def on_shutdown(app: Litestar) -> None:
    ws_server = app.state.ws_server
    await ws_server.stop()
    app.state.ws_server = None


# NOTE: socket is per connection, i.e. different sockets for different users
@websocket(f"/{VERSION}")
async def handler(socket: WebSocket) -> None:
    logger = socket.app.logger  # logger "litestar"
    state: State = socket.app.state
    ws_server: WebSocketServer = state.ws_server
    try:
        await ws_server.on_connected(socket)
        while True:
            try:
                await ws_server.recv(socket)
            except WebSocketDisconnect:
                logger.debug('websocket disconnected, breaking while loop:')
                break  # client gone or server stopping
            except Exception:
                logger.exception("handler exception:")
    except Exception:
        logger.exception('Unexpected handler exception:')
    finally:
        await ws_server.on_disconnected(socket)


app = Litestar(
    route_handlers=[handler],
    on_startup=[on_startup],
    on_shutdown=[on_shutdown],
    logging_config=litestar_logging_config,
    plugins=[
        ChannelsPlugin(
            # channels=...,
            backend=MemoryChannelsBackend(history=20),
            # TODO: support redis backend
            # backend=RedisChannelsPubSubBackend(
            #     redis=Redis(
            #         host=os.getenv('REDIS_HOST', 'localhost'),
            #         port=int(os.getenv('REDIS_PORT', 6379)),
            #         db=0
            #     )
            # ),
            subscriber_max_backlog=1000,
            # dropping the oldest message in the backlog when a new one is added while the backlog is full
            subscriber_backlog_strategy="dropleft",
            # NOTE: too many combinations of channels, allow arbitrary channels at litestar level
            # validate them at ws_server level
            arbitrary_channels_allowed=True,
        )
    ],
)
