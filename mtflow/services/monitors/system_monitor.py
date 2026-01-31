import psutil

from pfund import cprint


class SystemMonitor:
    def __init__(self):
        pass
    
    

def print_disk_usage(path: str | None=None) -> None:
    """
    Prints the disk usage of the given path.
    """
    if not path:
        from pfeed.config import get_config
        config = get_config()
        path = config.data_path
    disk_usage = psutil.disk_usage(path)
    cprint(f"Disk usage at {path}: {disk_usage.percent}%", style="bold red")


def print_ram_usage() -> None:
    """
    Prints the system's RAM usage.
    """
    ram_usage = psutil.virtual_memory()
    cprint(f"RAM usage: {ram_usage.percent}%", style="bold red")


# TODO: monitor zeromq events
'''
from zmq.devices import monitored_queue
ins = ctx.socket(zmq.ROUTER)
outs = ctx.socket(zmq.DEALER)
mons = ctx.socket(zmq.PUB)
configure_sockets(ins,outs,mons)
monitored_queue(ins, outs, mons, in_prefix='in', out_prefix='out')
or 
from zhelpers import zpipe
pipe = zpipe(ctx)
monitored_queue(subscriber, publisher, pipe[0], b'pub', b'sub')
# should filter and monitor e.g. specific exchange's messages


and zmq.MessageTracker
'''