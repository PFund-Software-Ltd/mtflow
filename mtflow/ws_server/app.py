import os
import logging

from redis.asyncio.client import Redis
from litestar import Litestar, WebSocket, websocket
from litestar.exceptions import WebSocketDisconnect
# from litestar.handlers.websocket_handlers import websocket_listener, WebsocketListener
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.redis import RedisChannelsPubSubBackend
from litestar.datastructures import State
from litestar.logging import LoggingConfig
from litestar.logging.standard import QueueListenerHandler
from cpfund.logging import set_up_loggers

from ws_server.const.paths import CONFIG_PATH, LOG_PATH
from ws_server.ws_server import WebSocketServer


# TODO: should read from redis to know what engine(s) are running and what data channels are available
# rmb you can create channels on the fly
def create_channels():
    from cpfund.const.commons import SUPPORTED_ENVIRONMENTS, SUPPORTED_DATA_CHANNELS
    # SUPPORTED_CHANNELS = ['position', 'balance', 'trade', 'order']
    # [f'{env}:{channel}' for env in SUPPORTED_ENVIRONMENTS for channel in SUPPORTED_CHANNELS]
    channels = ['PAPER:channel_1']
    return channels


def get_ws_server(app: Litestar) -> None:
    if not getattr(app.state, "ws_server", None):
        channels = [plugin for plugin in app.plugins.init if type(plugin) is ChannelsPlugin][0]
        ws_server = WebSocketServer(app.logger, channels)
        ws_server.start()
        app.state.ws_server = ws_server


def add_handlers_to_logger(app: Litestar) -> None:
    set_up_loggers(log_path=LOG_PATH, config_path=CONFIG_PATH)
    logger = logging.getLogger('litestar')
    configured_handlers = logger.handlers[:]  # handlers configured in logging.yml
    assert logger is app.logger, f"Unexpected {app.logger=}, {logger=}"
    queue_listener = QueueListenerHandler(configured_handlers)
    queue_listener.setLevel(logging.DEBUG)
    queue_listener.listener.respect_handler_level = True
    logger.addHandler(queue_listener)
    # clear the existing handlers after adding them to the queue_listener
    for handler in configured_handlers:
        logger.removeHandler(handler)
    

async def stop_ws_server(app: Litestar) -> None:
    if getattr(app.state, "ws_server", None):
        ws_server = app.state.ws_server
        await ws_server.stop()


@websocket(path='/v1/private')
async def private_handler(state: State, socket: WebSocket, channels: ChannelsPlugin) -> None:
    error_msg = None
    try:
        # NOTE: socket is per connection, i.e. different sockets for different users
        await socket.accept()
        ws_server = state.ws_server
        logger = socket.app.logger
        
        ws_server.ping(socket)
        
        logger.info(f'{socket=} connected')
        
        while True:
            msg = await socket.receive_json()
            type_ = msg['type']
            logger.debug(f'{socket=} {msg=}')
            if type_ == 'subscribe':
                result = {'type': type_, 'subscribed': []}
                failed_channels = []
                channel_list: list[str] = msg['channels']
                for channel in channel_list:
                    if is_success := await ws_server.subscribe(socket, channel):
                        result['subscribed'].append(channel)
                    else:
                        failed_channels.append(channel)
                if failed_channels:
                    result['error'] = f'Could not subscribe to {failed_channels}'
                await socket.send_json(result)
            elif type_ == 'unsubscribe':
                result = {'type': type_, 'unsubscribed': []}
                failed_channels = []
                channel_list: list[str] = msg['channels']
                for channel in channel_list:
                    if is_success := await ws_server.unsubscribe(socket, channel):
                        result['unsubscribed'].append(channel)
                    else:
                        failed_channels.append(channel)
                if failed_channels:
                    result['error'] = f'Could not unsubscribe to {failed_channels}'
                await socket.send_json(result)
            elif type_ == 'ping':
                ws_server.ping(socket)
                await socket.send_json({'type': 'pong'})
    except WebSocketDisconnect as err:
        error_msg = 'ws disconnected'
        logger.info(f'{socket=} disconnected')
    except Exception as err:
        error_msg = str(err)
        logger.exception(f'{socket=} private_handler exception:')
    finally:
        # unsubscribe all channels
        channels = ws_server.get_socket_channels(socket)
        for channel in channels:
            await ws_server.unsubscribe(socket, channel)
        # close socket
        try:
            if socket.connection_state != 'disconnect':
                # NOTE: this will trigger the on_close function in ws client (user side)
                await socket.close(reason=error_msg)
        except:
            logger.exception(f'{socket=} {error_msg=} socket.close exception:')


app = Litestar(
    route_handlers=[private_handler],
    on_startup=[get_ws_server, add_handlers_to_logger],
    on_shutdown=[stop_ws_server],
    # use this to make the default logger 'litestar' have empty handlers, will add handlers to it using add_handlers_to_logger()
    logging_config=LoggingConfig(loggers={"litestar": {"level": "INFO", "handlers": [], "propagate": False}}),        
    plugins=[
        ChannelsPlugin(
            backend=RedisChannelsPubSubBackend(
                redis=Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    db=0
                )
            ),
            channels=create_channels(),
            subscriber_max_backlog=1000,
            # dropping the oldest message in the backlog when a new one is added while the backlog is full
            subscriber_backlog_strategy="dropleft",
        )
    ],
    # debug=True,
)


if __name__ == '__main__':
    import uvicorn

    is_debug = True
    uvicorn.run(
        app if not is_debug else "app:app", 
        host="0.0.0.0",
        port=8002,
        reload=is_debug,
        # log_config=None,
    )