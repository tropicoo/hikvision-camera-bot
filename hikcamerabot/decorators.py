"""Decorators module."""

import re
from functools import wraps
from typing import TYPE_CHECKING

from pyrogram.types import Message

from hikcamerabot.constants import CMD_CAM_ID_REGEX
from hikcamerabot.utils.utils import get_user_info

if TYPE_CHECKING:
    from hikcamerabot.camerabot import CameraBot


# def event_error_handler(func):
#     @wraps(func)
#     async def wrapper(*args, **kwargs):
#         handler, data = args
#         try:
#             return await func(*args, **kwargs)
#         except Exceptio n as err:
#             return {'error_full': traceback.format_exc(), 'error': str(err),
#                     **data}
#
#     return wrapper


# def result_error_handler(func):
#     @wraps(func)
#     async def wrapper(*args, **kwargs):
#         handler, data = args
#
#         if 'error' not in data:
#             return await func(*args, **kwargs)
#
#         message: Message
#         cam_id, message = handler._bot._updates.pop(data['event_id'])
#
#         err_text = data['error']
#
#         # TODO: Move to util module.
#         if len(err_text) > TG_MAX_MSG_SIZE:
#             for x in range(0, len(err_text), TG_MAX_MSG_SIZE):
#                 await message.answer(err_text[x:x + TG_MAX_MSG_SIZE])
#         else:
#             await message.answer(err_text)
#
#     return wrapper


def authorization_check(func):
    """User authorization check."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        bot: CameraBot = args[0]
        message: Message = args[1]
        bot._log.debug(get_user_info(message))  # noqa

        if message.chat.id in bot.chat_users:
            return await func(*args, **kwargs)

        bot._log.error('User authorization error: %s', message.chat.id)  # noqa
        await message.reply_text(
            'Not authorized', reply_to_message_id=message.message_id
        )

    return wrapper


def camera_selection(func):
    """Select camera ID to use."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        bot: CameraBot = args[0]
        message: Message = args[1]
        cam_id = re.findall(CMD_CAM_ID_REGEX, message.text)[0]
        cam = bot.cam_registry.get_instance(cam_id)
        try:
            return await func(*args, cam=cam, **kwargs)
        except Exception:
            bot._log.exception('Failed to process event for %s', cam_id)

    return wrapper
