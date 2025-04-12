import sys


def is_wasm() -> bool:
    return sys.platform == "emscripten"
