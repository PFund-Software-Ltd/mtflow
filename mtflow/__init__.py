from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Any, Awaitable
if TYPE_CHECKING:
    from mtflow.transport.ws_client import WebSocketClient

import atexit
from importlib.metadata import version

from mtflow.enums.event import Event
from mtflow.config import get_config, configure, configure_logging
from mtflow.context import MTFlowContext


_context: MTFlowContext | None = None
_ws_client: WebSocketClient | None = None


async def emit(event: Event, data: dict):
    ws_client = await get_ws_client()
    await ws_client.send({"event": event, "data": data})
    
    
def get_context() -> MTFlowContext:
    """Get or create the global context."""
    global _context
    if _context is None:
        _context = MTFlowContext()
        # Register cleanup on interpreter shutdown
        atexit.register(_context.stop)
    return _context


async def get_ws_client(url: str = "", callback: Callable[[dict], Any | Awaitable[Any]] | None = None) -> WebSocketClient:
    '''
    Args:
        url: websocket server url to connect to, 
            if not provided, will use a default url based on environment variables:
                MTFLOW_SERVER_HOST and MTFLOW_SERVER_PORT
        callback: callback function to call when a message is received
    '''
    global _ws_client
    if _ws_client is None:
        _ws_client = WebSocketClient(url=url, callback=callback)
        await _ws_client.connect()
    return _ws_client


def start(ws_server: bool = False):
    """Start services in background threads, optionally start WS server as subprocess."""
    ctx = get_context()
    if ws_server:
        ctx._start_ws_server()
    ctx.start()


def stop() -> None:
    """Stop all services gracefully."""
    _context.stop()


def reset() -> None:
    """Reset the global context (stop services and clear configuration)."""
    _context.reset()


def __getattr__(name: str):
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__version__ = version("mtflow")
__all__ = [
    # Version
    '__version__',
    # Config
    'get_config',
    'configure',
    'configure_logging',
    # Context
    'get_context',
    'get_ws_client',
    # Lifecycle
    'start',
    'stop',
    'reset',
    # Transport
    'emit',
]


def __dir__():
    return sorted(__all__)
