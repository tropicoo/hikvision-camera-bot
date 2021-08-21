"""Utils module."""
import asyncio
import logging
import random
import string
from datetime import datetime
from uuid import uuid4

from aiogram.types import Message


class Singleton(type):
    """Singleton class."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """Check whether instance already exists.

        Return existing or create new instance and save to dict."""
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


async def shallow_sleep_async(sleep_time: float = 0.1) -> None:
    await asyncio.sleep(sleep_time)


def gen_uuid() -> str:
    return uuid4().hex


def gen_random_str(length=4) -> str:
    return ''.join(
        random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _
        in range(length))


def format_ts(ts: float, time_format: str = '%a %b %d %H:%M:%S %Y') -> str:
    return datetime.fromtimestamp(ts).strftime(time_format)


def make_bold(text: str) -> str:
    """Wrap input string in HTML bold tag."""
    return f'<b>{text}</b>'


def get_user_info(message: Message) -> str:
    """Return user information who interacts with bot."""
    chat = message.chat
    return f'Request from user_id: {chat.id}, username: {chat.username}, ' \
           f'full name: {chat.full_name}'


def build_command_presentation(commands: dict[str, list]) -> str:
    groups = []
    for desc, cmds in commands.items():
        groups.append('{0}\n{1}'.format(desc, '\n'.join(['/' + c for c in cmds])))
    return '\n\n'.join(groups)


def setup_logging() -> None:
    log_format = '%(asctime)s - [%(levelname)s] - [%(name)s:%(lineno)s] - %(message)s'
    logging.basicConfig(format=log_format)
