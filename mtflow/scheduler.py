from pfund.enums import RunMode


class Scheduler:
    def __init__(self, mode: RunMode):
        if mode == RunMode.WASM:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            self._scheduler = AsyncIOScheduler()
        else:
            from apscheduler.schedulers.background import BackgroundScheduler
            self._scheduler = BackgroundScheduler()
        self._scheduler.start()

    def _start_scheduler(self):
        '''start scheduler for background tasks'''
        self._scheduler.add_job(
            self._ping_processes, 'interval', 
            seconds=self._PROCESS_NO_PONG_TOLERANCE_IN_SECONDS // 3
        )
        self._scheduler.add_job(
            self._check_processes, 'interval', 
            seconds=self._PROCESS_NO_PONG_TOLERANCE_IN_SECONDS
        )
        for broker in self.brokers.values():
            broker.schedule_jobs(self.scheduler)
        self._scheduler.start()