import asyncio
from threading import Thread

import pfeed as pe


class DataBroker:
    def __init__(self):
        self._data_engine = pe.DataEngine(
            data_tool=self._data_tool,
            use_ray=not self.is_wasm(),
            use_deltalake=config.use_deltalake
        )
        self._data_engine_thread: Thread | None = None
        self._data_engine_loop: asyncio.AbstractEventLoop | None = None
        self._data_engine_task: asyncio.Task | None = None
        self._setup_data_engine()

    def _setup_data_engine(self):
        from pfeed.messaging.zeromq import ZeroMQ
        sender_name = "data_engine"
        self._data_engine._setup_messaging(
            # FIXME: should be zmq_urls.get('data_engine', ZeroMQ.DEFAULT_URL)?
            zmq_url=self._settings.zmq_urls.get(self.name, ZeroMQ.DEFAULT_URL),
            zmq_sender_port=self._settings.zmq_ports.get('data_engine', None),
            # NOTE: zmq_receiver_port is not expected to be set manually
            # zmq_receiver_port=...
        )
        data_engine_zmq = self._data_engine._msg_queue
        data_engine_port = data_engine_zmq.get_ports_in_use(data_engine_zmq.sender)[0]
        self._settings.zmq_ports.update({ sender_name: data_engine_port })
    
    def run(self, num_data_workers: int | None=None, **ray_kwargs):
        '''
        Args:
            ray_kwargs: keyword arguments for ray.init()
            num_data_workers: number of Ray workers to create in the data engine
                if not specified, all available system CPUs will be used.
                it is ignored in WASM mode when Ray is not in use.
        '''
        # NOTE: need to init ray in the main thread to avoid "SIGTERM handler is not set because current thread is not the main thread"
        import ray
        if not ray.is_initialized():
            ray.init(**ray_kwargs)
        self._run_data_engine(num_workers=num_data_workers)

    def _run_data_engine(self, num_workers: int | None=None):
        def _run():
            ray_kwargs = {}
            if num_workers is not None:
                ray_kwargs['num_cpus'] = num_workers
            self._data_engine_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._data_engine_loop)
            self._data_engine_task = self._data_engine_loop.create_task(
                self._data_engine.run_async(**ray_kwargs)
            )
            try:
                self._data_engine_loop.run_until_complete(self._data_engine_task)
            except Exception:
                self._logger.exception("Exception in data engine thread:")
            finally:
                self._data_engine_loop.close()
                self._data_engine_loop = None
                self._data_engine_task = None
        
        # add storage to feeds in data engine
        for feed in self._data_engine.feeds:
            dataflow = feed.streaming_dataflows[0]
            if dataflow.sink is None:
                feed.load(to_storage=config.storage)
        
        self._data_engine_thread = Thread(target=_run, daemon=True)
        self._data_engine_thread.start()
    
    
    def _end_data_engine(self):
        self._logger.debug(f'{self.name} ending data engine')
        if not self.is_wasm():
            if self._data_engine_task and self._data_engine_loop and not self._data_engine_task.done():
                self._data_engine_loop.call_soon_threadsafe(self._data_engine_task.cancel)
        
    def end(self):
        self._end_data_engine()
        if self._data_engine_thread:
            self._logger.debug(f"{self.name} waiting for data engine thread to finish")
            self._data_engine_thread.join(timeout=10)
            if self._data_engine_thread.is_alive():
                self._logger.debug(f"{self.name} data engine thread is still running after timeout")
            else:
                self._logger.debug(f"{self.name} data engine thread finished")
