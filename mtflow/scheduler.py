from __future__ import annotations
from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from pfund._typing import Component

from pfund.enums import RunMode
from mtflow.utils.utils import is_wasm


# TODO: create a custom asyncio scheduler that can be also be used in the browser
class Scheduler:
    def __init__(self):
        if is_wasm():
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            self._scheduler = AsyncIOScheduler()
        else:
            from apscheduler.schedulers.background import BackgroundScheduler
            self._scheduler = BackgroundScheduler()
        # self._scheduler.start()

    def _start_scheduler(self):
        '''start scheduler for background tasks'''
        self._scheduler.add_job(
            self._ping_processes, 
            trigger='interval',
            seconds=self._PROCESS_NO_PONG_TOLERANCE_IN_SECONDS // 3
        )
        self._scheduler.add_job(
            self._check_processes, 
            trigger='interval',
            seconds=self._PROCESS_NO_PONG_TOLERANCE_IN_SECONDS
        )
        for broker in self.brokers.values():
            broker.schedule_jobs(self.scheduler)
        self._scheduler.start()
    
    def _schedule_task(self, func: Callable, **kwargs):
        self._scheduler.add_job(func, trigger='interval', **kwargs)
    
