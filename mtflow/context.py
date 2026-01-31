from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mtflow.services.monitor import Monitor
    from mtflow.services.recorder import Recorder
    from mtflow.services.scheduler import Scheduler
    from mtflow.services.ray_manager import RayManager
    from mtflow.transport.ws_server import WebSocketServer

import os
import threading


class MTFlowContext:
    """
    Manages mtflow services lifecycle.
    Services run in background threads while the main thread runs the trading engine.
    """

    def __init__(self):
        self._monitor: Monitor | None = None
        self._recorder: Recorder | None = None
        self._scheduler: Scheduler | None = None
        self._ray_manager: RayManager | None = None
        self._ws_server: WebSocketServer | None = None

        self._threads: list[threading.Thread] = []
        self._running = False
        self._lock = threading.Lock()
    
    def _start_ws_server(self):
        # TODO: use config.num_workers for web-concurrency
        server_port = os.getenv('MTFLOW_SERVER_PORT', 8000)
        self._ws_server = WebSocketServer()
    
    def _start_service(self):
        import sys
        import subprocess
        subprocess.Popen([sys.executable, "-m", "my_package.service"])
    
    # TODO: do registration here? register_engine() and register_component()

    # -------------------------------------------------------------------------
    # Service Registration
    # -------------------------------------------------------------------------

    def add_monitor(self, **kwargs) -> MTFlowContext:
        """Add a Monitor service."""
        # TODO: implement Monitor class
        # from mtflow.monitor import Monitor
        # self._monitor = Monitor(**kwargs)
        return self

    def add_recorder(self, **kwargs) -> MTFlowContext:
        """Add a Recorder service."""
        # TODO: implement Recorder class
        # from mtflow.recorder import Recorder
        # self._recorder = Recorder(**kwargs)
        return self

    def add_scheduler(self, **kwargs) -> MTFlowContext:
        """Add a Scheduler service."""
        # TODO: implement Scheduler class
        # from mtflow.scheduler import Scheduler
        # self._scheduler = Scheduler(**kwargs)
        return self

    def add_ray_manager(self, **kwargs) -> MTFlowContext:
        """Add a RayManager service."""
        # TODO: implement RayManager class
        # from mtflow.ray_manager import RayManager
        # self._ray_manager = RayManager(**kwargs)
        return self

    # -------------------------------------------------------------------------
    # Lifecycle Management
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """Start all configured services in background threads."""
        with self._lock:
            if self._running:
                return

            # TODO: Start WS server first (other services connect to it)
            # if self._ws_server is None:
            #     from mtflow.ws_server import WSServer
            #     self._ws_server = WSServer()
            # self._start_service(self._ws_server)

            # Start each configured service
            if self._monitor:
                self._start_service(self._monitor, name="mtflow:monitor")

            if self._recorder:
                self._start_service(self._recorder, name="mtflow:recorder")

            if self._scheduler:
                self._start_service(self._scheduler, name="mtflow:scheduler")

            if self._ray_manager:
                self._start_service(self._ray_manager, name="mtflow:ray-manager")

            self._running = True

    def _start_service(self, service, name: str | None = None) -> None:
        """Start a service in a background daemon thread."""
        # TODO: each service should implement a `run()` method that blocks
        # The service should also implement a `stop()` method for graceful shutdown
        thread = threading.Thread(
            target=service.run,
            name=name,
            daemon=True,  # Daemon threads auto-terminate when main thread exits
        )
        thread.start()
        self._threads.append(thread)

    def stop(self) -> None:
        """Stop all services gracefully."""
        with self._lock:
            if not self._running:
                return

            # TODO: Stop services in reverse order (ws_server last)
            # Each service should implement a `stop()` method

            if self._ray_manager:
                # TODO: self._ray_manager.stop()
                pass

            if self._scheduler:
                # TODO: self._scheduler.stop()
                pass

            if self._recorder:
                # TODO: self._recorder.stop()
                pass

            if self._monitor:
                # TODO: self._monitor.stop()
                pass

            # TODO: Stop WS server last
            # if self._ws_server:
            #     self._ws_server.stop()

            # Wait for threads to finish (with timeout)
            for thread in self._threads:
                thread.join(timeout=5.0)
                # TODO: log warning if thread didn't stop in time

            self._threads.clear()
            self._running = False

    def reset(self) -> None:
        """Reset the context (stop services and clear configuration)."""
        self.stop()
        self._monitor = None
        self._recorder = None
        self._scheduler = None
        self._ray_manager = None

    # -------------------------------------------------------------------------
    # Context Manager
    # -------------------------------------------------------------------------

    def __enter__(self) -> MTFlowContext:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
