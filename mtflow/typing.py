from typing import Literal


tZMQ_MESSENGER = Literal[
    "proxy",  # ZeroMQ xsub-xpub proxy for messaging from trading venues -> engine -> components
    "router",  # ZeroMQ router-pull for pulling messages from components (e.g. strategies/models) -> engine -> trading venues
    "publisher",  # ZeroMQ publisher for broadcasting internal states to external apps
]
