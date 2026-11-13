"""Decorators module."""

import contextlib
import logging
import re
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TYPE_CHECKING, Any

from hikcamerabot.constants import CMD_CAM_ID_REGEX
from hikcamerabot.utils.errors import describe_error
from hikcamerabot.utils.shared import bold, get_user_info

if TYPE_CHECKING:
    from pyrogram.types import Message

    from hikcamerabot.camerabot import CameraBot

log = logging.getLogger(__name__)


def authorization_check(
    func: Callable[..., Awaitable[Any]],
) -> Callable[..., Awaitable[Any]]:
    """User authorization check."""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        bot: CameraBot = args[0]
        message: Message = args[1]
        log.debug(get_user_info(message))

        if message.chat.id in bot.chat_users:
            return await func(*args, **kwargs)

        log.error('User authorization error: %s', message.chat.id)
        await message.reply_text('⛔ Нет доступа', quote=True)
        return None

    return wrapper


def camera_selection(
    func: Callable[..., Awaitable[Any]],
) -> Callable[..., Awaitable[Any]]:
    """Select camera ID to use and tell the user if the command failed."""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        bot: CameraBot = args[0]
        message: Message = args[1]
        cam_id: str = re.findall(CMD_CAM_ID_REGEX, message.text)[0]
        cam = bot.cam_registry.get_instance(cam_id)
        try:
            return await func(*args, cam=cam, **kwargs)
        except Exception as err:
            log.exception('Failed to process event for %s', cam_id)
            log.debug('Failed event context: %s', message)
            # Never leave the user without an answer.
            with contextlib.suppress(Exception):
                await message.reply_text(
                    f'🛑 {bold("Команда не выполнена")} — '
                    f'{cam.description} ({cam.id})\n\n{describe_error(err)}',
                    quote=True,
                )

    return wrapper
