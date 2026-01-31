from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from ray.actor import ActorClass
    from pfund._typing import Component, ComponentName
    from pfund.enums import RunMode

import time
import logging
from multiprocessing import Process, Value
try:
    import psutil
except ImportError:
    pass
try: 
    import ray
    from ray.actor import ActorHandle
    from ray._raylet import ObjectRef
except ImportError:
    ray = None
    ActorHandle = None

from pfund import cprint
from pfund.strategies.strategy_base import BaseStrategy
    
    
# TODO: zeromq loop for components
def _start_process(strategy: BaseStrategy, stop_flag: Value):
    try:
        from pfund.engines import TradeEngine
        assigned_cpus = TradeEngine.assign_cpus(strategy.name)
        current_process = psutil.Process()
        if hasattr(current_process, 'cpu_affinity') and assigned_cpus:
            current_process.cpu_affinity(assigned_cpus)
        else:
            strategy.logger.debug('cpu affinity is not supported')

        strategy.start_zmq()
        strategy.start()
        zmq = strategy.get_zmq()
        
        while not stop_flag.value:
            if msg := zmq.recv():
                channel, topic, info = msg
                if channel == 0:
                    if topic == 0:
                        strategy.pong()
                else:
                    bkr = info[0]
                    broker = strategy.get_broker(bkr)
                    # NOTE, if per-interpreter GIL in python 3.12 is ready, don't need to work on this
                    # TODO, receive e.g. orders/positions/balances/data updates from engine
                    if channel == 1:
                        broker.dm.handle_msgs(topic, info)
                    elif channel == 2:  # from api processes to data manager
                        broker.om.handle_msgs(topic, info)
                    elif channel == 3:
                        broker.pm.handle_msgs(topic, info)
        else:
            strategy.stop(reason='stop process')
            strategy.stop_zmq()
    except:
        strategy.logger.exception(f'{strategy.name} _start_process exception:')



# TODO: should do ping-pong with the trade engine
class RayManager:
    '''
    Orchestrate Ray actors, and processes
    '''
    PROCESS_NO_PONG_TOLERANCE_IN_SECONDS = 30

    def __init__(self):
        self._logger = logging.getLogger('mtflow')
        self._actors: dict[ComponentName, ActorHandle] = {}

        # FIXME: from strategy manager
        # self._is_running = defaultdict(bool)
        # self._is_restarting = defaultdict(bool)
        # self._pids = defaultdict(lambda: None)
        # self._strategy_stop_flags = defaultdict(lambda: Value('b', False))
        # self._strategy_procs = {}
        # self._last_pong_ts = defaultdict(lambda: time.time())
    
    def _init_ray(self, **kwargs):
        if not ray.is_initialized():
            ray.init(**kwargs)

    def _shutdown_ray(self):
        if ray.is_initialized():
            ray.shutdown()
    
    @staticmethod
    def is_actor(value: Any) -> bool:
        return isinstance(value, ActorHandle)

    def add_actor(self, component_name: str):
        self._init_ray()
        actor: ActorHandle = ray.get_actor(component_name)
        self._actors[component_name] = actor

    def remove_actor(self, component: Component):
        del self._actors[component.name]
    
    def _check_processes(self):
        for broker in self.brokers.values():
            connection_manager = broker.cm
            trading_venues = connection_manager.get_trading_venues()
            if reconnect_trading_venues := [trading_venue for trading_venue in trading_venues if not connection_manager.is_process_healthy(trading_venue)]:
                connection_manager.reconnect(reconnect_trading_venues, reason='process not responding')
        if restart_strats := [strat for strat, strategy in self.strategies.items() if self._use_ray and not self.strategy_manager.is_process_healthy(strat)]:
            self.executor.restart(restart_strats, reason='process not responding')

    def _adjust_input_strats(self, strats: str|list[str]|None) -> list:
        if type(strats) is str:
            strats = [strats]
        return strats or list(self.strategies)
    
    def is_process_healthy(self, strat: str):
        if time.time() - self._last_pong_ts[strat] > self.PROCESS_NO_PONG_TOLERANCE_IN_SECONDS:
            self._logger.error(f'process {strat=} is not responding')
            return False
        else:
            return True
    
    def _set_pid(self, strat: str, pid: int):
        prev_pid = self._pids[strat]
        self._pids[strat] = pid
        self._logger.debug(f'set strategy {strat} process pid from {prev_pid} to {pid}')
    
    def _on_pong(self, strat: str):
        self._last_pong_ts[strat] = time.time()
        self._logger.debug(f'{strat} ponged')

    def is_running(self, strat: str):
        return self._is_running[strat]
    
    def on_start(self, strat: str):
        if not self._is_running[strat]:
            self._is_running[strat] = True 
            self._logger.debug(f'{strat} is started')

    def on_stop(self, strat: str, reason=''):
        if self._is_running[strat]:
            self._is_running[strat] = False
            self._logger.debug(f'{strat} is stopped ({reason=})')

    def _terminate_process(self, strat: str):
        pid = self._pids[strat]
        if pid is not None and psutil.pid_exists(pid):
            psutil.Process(pid).kill()
            self._logger.warning(f'force to terminate {strat} process ({pid=})')
            self._set_pid(strat, None)

    def start(self, strats: str|list[str]|None=None, in_parallel: bool=False):
        strats = self._adjust_input_strats(strats)
        for strat in strats:
            self._logger.debug(f'{strat} is starting')
            strategy = self.strategies[strat]
            if in_parallel:
                stop_flag = self._strategy_stop_flags[strat]
                stop_flag.value = False
                self._strategy_procs[strat] = Process(target=_start_process, args=(strategy, stop_flag), name=f'{strat}_process', daemon=True)
                self._strategy_procs[strat].start()
            else:
                strategy.start()
                self.on_start(strat)

    def stop(self, strats: str|list[str]|None=None, in_parallel: bool=False, reason=''):
        self._shutdown_ray()
        strats = self._adjust_input_strats(strats)
        for strat in strats:
            self._logger.debug(f'{strat} is stopping')
            strategy = self.strategies[strat]
            if in_parallel:
                stop_flag = self._strategy_stop_flags[strat]
                stop_flag.value = True
                # need to wait for the process to finish 
                # in case no pid has been returned (i.e. cannot terminate the process by pid)
                while self._strategy_procs[strat].is_alive():
                    self._logger.debug(f'waiting for strat process {strat} to finish')
                    self._terminate_process(strat)
                    time.sleep(1)
                else:
                    self._logger.debug(f'strat process {strat} is finished')
                    del self._strategy_procs[strat]
                    self.on_stop(strat, reason=f'forced stop ({reason})')
            else:
                strategy.stop(reason=reason)
                self.on_stop(strat, reason=reason)

    def restart(self, strats: str|list[str]|None=None, reason: str=''):
        strats = self._adjust_input_strats(strats)
        for strat in strats:
            if not self._is_restarting[strat]:
                self._logger.debug(f'{strat} is restarting ({reason=})')
                self._is_restarting[strat] = True
                self.stop(strat)
                self.start(strat)
                self._is_restarting[strat] = False
            else:
                self._logger.warning(f'{strat} is already restarting, do not restart again ({reason=})')
    
    def handle_msgs(self, topic, info):
        strat = info[0]
        # NOTE: this strategy object is just a shell without any memory
        # if the strategy is running in another process (is_parallel=True)
        strategy = self.get_strategy(strat)
        if topic == 0:  # pong
            self._on_pong(*info)
        elif topic == 1:
            self._set_pid(*info)
        elif topic == 2:
            self.on_start(*info)
        elif topic == 3:
            self.on_stop(*info)
        elif topic == 4:
            strategy.place_orders(...)
        elif topic == 5:
            strategy.cancel_orders(...)
        elif topic == 6:
            strategy.amend_orders(...)