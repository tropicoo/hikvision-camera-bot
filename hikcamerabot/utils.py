"""Utils module."""

import inspect
import time
from datetime import datetime
from multiprocessing.managers import SyncManager, NamespaceProxy

import psutil


def shallow_sleep(sleep_time=0.1):
    time.sleep(sleep_time)


def format_ts(ts, time_format='%a %b %d %H:%M:%S %Y'):
    return datetime.fromtimestamp(ts).strftime(time_format)


def kill_proc_tree(pid, including_parent=True):
    """Kill process tree.
    Kill ffmpeg process. Regular subprocess kill somehow leaves zombie.
    Really not critical but psutil works like a charm.
    """
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    for child in children:
        child.kill()
    if including_parent:
        parent.kill()
        parent.wait(5)


def make_bold(text):
    """Wrap input string in HTML bold tag."""
    return f'<b>{text}</b>'


def init_shared_manager(items):
    """Initialize and start shared manager."""
    for cls in items:
        proxy = create_proxy(cls)
        SyncManager.register(cls.__name__, cls, proxy)
    manager = SyncManager()
    manager.start()
    return manager


class BaseProxy(NamespaceProxy):
    _exposed_ = ['__getattribute__', '__setattr__', '__delattr__']


class HikCameraProxy(BaseProxy):
    pass


def create_proxy(cls):
    for attr in dir(cls):
        if inspect.ismethod(getattr(cls, attr)) and not attr.startswith('__'):
            HikCameraProxy._exposed_.append(attr)
            setattr(HikCameraProxy, attr,
                    lambda s: object.__getattribute__(s, '_callmethod')(attr))
    return HikCameraProxy
