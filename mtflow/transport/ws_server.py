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
    pass