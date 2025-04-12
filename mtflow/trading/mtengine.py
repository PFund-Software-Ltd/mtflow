from apscheduler.schedulers.background import BackgroundScheduler

from mtflow.executor import RayExecutor
from mtflow.trading.zeromq import ZeroMQ


class MTEngine:
    '''
    A meta-trading engine for pfund's engines.
    acts as the operation layer of trading engines.
    e.g. ZeroMQ/Kafka messaging, background tasks, etc.
    '''
    def __init__(self, use_ray: bool=True):
        self._use_ray = use_ray
        self._executor = RayExecutor() if use_ray else None
        self._zmq = ZeroMQ('engine')
        self._scheduler = BackgroundScheduler()