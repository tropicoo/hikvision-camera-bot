"""Utils module."""

import inspect
import time
from datetime import datetime
from multiprocessing.managers import SyncManager, NamespaceProxy

import psutil


class Singleton(type):
    """Singleton class."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """Check whether instance already exists.

        Return existing or create new instance and save to dict."""
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


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


def get_user_info(update):
    """Return user information who interacts with bot."""
    return 'Request from user_id: {0}, username: {1},' \
           'first_name: {2}, last_name: {3}'.format(
        update.message.chat.id,
        update.message.chat.username,
        update.message.chat.first_name,
        update.message.chat.last_name)


def print_access_error(update):
    """Send authorization error to telegram chat."""
    update.message.reply_text('Not authorized')


def build_commands_presentation(bot, cam_id):
    groups = []
    for desc, cmds in bot.cam_registry.get_commands(cam_id).items():
        groups.append(
            '{0}\n{1}'.format(desc, '\n'.join(['/' + c for c in cmds])))
    return '\n\n'.join(groups)


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
