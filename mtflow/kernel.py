from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pfund.enums import Database
    from pfund._typing import Component
    from pfund.external_listeners import ExternalListeners
    from mtflow.monitor import SystemMonitor
    from mtflow.recorder import DataRecorder
    from mtflow.profiler import Profiler

import logging

from pfund.enums import RunMode


logger = logging.getLogger('mtflow')


class TradeKernel:
    '''
    Low-level operational runtime of the pfund's trade engine .
    Handles engine's tasks scheduling, process management, background tasks etc.
    '''
    PROCESS_NO_PONG_TOLERANCE_IN_SECONDS = 30

    def __init__(
        self, 
        database: Database | None, 
        external_listeners: ExternalListeners,
    ):
        from mtflow.orchestrator import Orchestrator
        from mtflow.scheduler import Scheduler
        from mtflow.registry import Registry
        
        self._database: Database | None = database
        self._external_listeners = external_listeners
        self._registry = Registry()
        self._orchestrator = Orchestrator()
        self._scheduler = Scheduler()
        self._monitor: SystemMonitor | None = None
        self._recorder: DataRecorder | None = None
        self._profiler: Profiler | None = None
        self._setup_external_listeners()
    
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
    
    def add_ray_actor(self, component_name: str):
        self._orchestrator.add_actor(component_name)
    
    def remove_ray_actor(self, component: Component):
        self._orchestrator.remove_actor(component)
    
    def register_engine(self, metadata: dict):
        self._registry.register_engine(metadata)
    
    def register_component(self, metadata: dict):
        if metadata['run_mode'] == RunMode.REMOTE:
            self.add_ray_actor(metadata['name'])
        self._registry.register_component(metadata)
        
    # FIXME    
    def run(self):
        pass
        # self._start_scheduler()
        # self._executor.start(in_parallel=self._use_ray)
    
    # FIXME
    def end(self):
        pass
        # self._orchestrator.stop()
        # for strat in list(self.strategy_manager.strategies):
        #     self.strategy_manager.stop(strat, in_parallel=self._use_ray, reason='end')
        #     self.remove_strategy(strat)
        # self._zmq.stop()
        # self.scheduler.shutdown()