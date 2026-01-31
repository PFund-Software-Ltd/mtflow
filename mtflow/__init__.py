from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mtflow.transport.ws_client import WebSocketClient

import atexit
from importlib.metadata import version

from mtflow.config import get_config, configure, configure_logging
from mtflow.context import MTFlowContext


_context: MTFlowContext | None = None
_ws_client: WebSocketClient | None = None


def emit(event_type: str, data: dict):
    from mtflow.transport.ws_client import WebSocketClient
    global _ws_client
    if _ws_client is None:
        _ws_client = WebSocketClient()  # Lazy init
        _ws_client.connect()  # Persistent connection
    _ws_client.send(event_type, data)
    
    
def get_context() -> MTFlowContext:
    """Get or create the global context."""
    global _context
    if _context is None:
        _context = MTFlowContext()
        # Register cleanup on interpreter shutdown
        atexit.register(_context.stop)
    return _context


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
    # Lifecycle
    'start',
    'stop',
    'reset',
]


def __dir__():
    return sorted(__all__)
