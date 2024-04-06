"""Utils module."""

import asyncio
import logging
import random
import string
from datetime import datetime
from typing import TYPE_CHECKING, Any, Generator
from uuid import uuid4

from pyrogram.enums import ParseMode
from pyrogram.types import Message

from hikcamerabot.config.config import get_main_config
from hikcamerabot.constants import TG_MAX_MSG_SIZE
from hikcamerabot.enums import CmdSectionType

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam


class Singleton(type):
    """Singleton class."""

    _instances = {}

    def __call__(cls, *args, **kwargs) -> Any:
        """Check whether instance already exists.

        Return existing or create new instance and save it to dict."""
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


async def shallow_sleep_async(sleep_time: float = 0.1) -> None:
    await asyncio.sleep(sleep_time)


def gen_uuid() -> str:
    return uuid4().hex


def gen_random_str(length=4) -> str:
    return ''.join(
        random.SystemRandom().choice(string.ascii_lowercase + string.digits)
        for _ in range(length)
    )


def format_ts(ts: float, time_format: str = '%a %b %d %H:%M:%S %Y') -> str:
    return datetime.fromtimestamp(ts).strftime(time_format)


def bold(text: str) -> str:
    """Wrap input string in HTML bold tag."""
    return f'<b>{text}</b>'


def get_user_info(message: Message) -> str:
    """Return user information who interacts with bot."""
    chat = message.chat
    last_name = f' {chat.last_name}' if chat.last_name else ''
    return (
        f'Request from user_id: "{chat.id}", username: "{chat.username}", '
        f'full_name: "{chat.first_name}{last_name}"'
    )


def build_command_presentation(
    commands: dict[str, list[str]], cam: 'HikvisionCam'
) -> str:
    groups = []
    visibility_opts: dict[str, bool] = cam.conf.command_sections_visibility
    for section_desc, cmds in commands.items():
        if visibility_opts[CmdSectionType(section_desc).name]:
            rendered_cmds = '\n'.join([f'/{cmd}' for cmd in cmds])
            groups.append(f'{section_desc}\n{rendered_cmds}')
    return '\n\n'.join(groups)


def setup_logging() -> None:
    logging.getLogger().setLevel(get_main_config().log_level)
    logging.getLogger('pyrogram').setLevel(logging.WARNING)
    log_format = '%(asctime)s - [%(levelname)s] - [%(name)s:%(lineno)s] - %(message)s'
    logging.basicConfig(format=log_format)


def split_telegram_message(text: str) -> Generator[str, None, None]:
    text_len = len(text)
    if text_len > TG_MAX_MSG_SIZE:
        for x in range(0, text_len, TG_MAX_MSG_SIZE):
            yield text[x : x + TG_MAX_MSG_SIZE]
    else:
        yield text


async def send_text(
    text: str,
    message: Message,
    quote: bool = False,
    parse_mode: ParseMode = ParseMode.HTML,
) -> None:
    first_chunk_sent = False
    for chunk in split_telegram_message(text):
        if first_chunk_sent:
            await message.reply_text(chunk, parse_mode=parse_mode)
        else:
            await message.reply_text(chunk, quote=quote, parse_mode=parse_mode)
            first_chunk_sent = True
