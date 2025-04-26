from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pfund.enums import RunMode, Database
    from pfund.typing import Component, tTRADING_VENUE, ComponentName, EngineName
    from pfund.external_listeners import ExternalListeners
    from mtflow.typing import tZMQ_MESSENGER
    from mtflow.monitor import SystemMonitor
    from mtflow.recorder import DataRecorder
    from mtflow.profiler import Profiler


class TradeKernel:
    '''
    Low-level operational runtime of the pfund's trade engine .
    Handles engine's messaging, tasks scheduling, and process management.
    e.g. ZeroMQ messaging, background tasks, etc.
    '''
    _PROCESS_NO_PONG_TOLERANCE_IN_SECONDS = 30

    def __init__(
        self, 
        mode: RunMode,
        database: Database | None,
        external_listeners: ExternalListeners,
        zmq_urls: dict[EngineName | tTRADING_VENUE | ComponentName, str],
        zmq_ports: dict[tZMQ_MESSENGER | tTRADING_VENUE | ComponentName, int],
    ):
        import logging
        from mtflow.orchestrator import Orchestrator
        from mtflow.scheduler import Scheduler
        from mtflow.messaging.messenger import Messenger
        
        self._logger = logging.getLogger('mtflow')
        self._mode = mode
        self._database = database
        self._external_listeners = external_listeners
        self._messenger = Messenger(zmq_url=zmq_urls, zmq_ports=zmq_ports)
        self._scheduler = Scheduler(mode=mode)
        self._orchestrator = Orchestrator(mode=mode)
        self._monitor: SystemMonitor | None = None
        self._recorder: DataRecorder | None = None
        self._profiler: Profiler | None = None
        self._setup_external_listeners()
        self._is_running = False
        
    def _setup_external_listeners(self):
        if self._external_listeners.notebooks:
            from pfund_plot.templates.notebook import Notebook
            self._notebook = Notebook()
        elif self._external_listeners.dashboards:
            from pfund_plot.templates.dashboard import Dashboard
            self._dashboard = Dashboard()
        if self._external_listeners.monitor:
            from mtflow.monitor import SystemMonitor
            self._monitor = SystemMonitor()
        if self._external_listeners.recorder:
            from mtflow.recorder import DataRecorder
            self._recorder = DataRecorder()
        if self._external_listeners.profiler:
            from mtflow.profiler import Profiler
            self._profiler = Profiler()
            
    def add_ray_actor(self, component: Component, auto_wrap: bool=True):
        self._orchestrator.add_actor(component, auto_wrap=auto_wrap)
    
    def remove_ray_actor(self, component: Component):
        self._orchestrator.remove_actor(component)
    
    def add_connection_process(self, process):
        self._orchestrator.add_process(process)
        
    def remove_connection_process(self, process):
        self._orchestrator.remove_process(process)
    
    # FIXME    
    def run(self, active_trading_venues: list[tTRADING_VENUE], active_components: list[str]):
        self._messenger.start(active_trading_venues, active_components)
        # self._start_scheduler()
        # self._executor.start(in_parallel=self._use_ray)
        self._is_running = True
    
    # FIXME
    def end(self):
        """Stop and clear all state (hard stop)."""
        pass
        # for strat in list(self.strategy_manager.strategies):
        #     self.strategy_manager.stop(strat, in_parallel=self._use_ray, reason='end')
        #     self.remove_strategy(strat)
        # self._zmq.stop()
        # self._is_running = False
        # self.scheduler.shutdown()