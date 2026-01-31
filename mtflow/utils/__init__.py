from typing import Literal

import os
import sys


def is_wasm() -> bool:
    return sys.platform == "emscripten"


def detect_execution_context() -> Literal["ray", "multiprocessing", "main"]:
    """
    Detects how the current Python process is running.

    Returns:
        A string representing the execution context:
        - "ray"          → running inside a Ray actor
        - "multiprocessing" → spawned by Python multiprocessing
        - "main"         → the main/root process
    """
    from multiprocessing import current_process
    if os.environ.get("RAY_WORKER_MODE") == "1":
        return "ray"
    elif current_process().name != "MainProcess":
        return "multiprocessing"
    elif current_process().name == "MainProcess":
        return "main"
    else:
        raise ValueError("Unknown execution context")
