from enum import StrEnum


class PFundSignal(StrEnum):
    ready = 'ready'
    start = 'start'
    stop = 'stop'