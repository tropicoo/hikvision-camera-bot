"""Decorators module."""

import re
import traceback
import uuid
from functools import wraps

from hikcamerabot.constants import CMD_CAM_ID_REGEX
from hikcamerabot.exceptions import UserAuthError
from hikcamerabot.utils import shallow_sleep, get_user_info, print_access_error


def retry(delay=5, retries=3):
    """Retry decorator."""
    retries = retries if retries > 0 else 1

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            _err = None
            for ret in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as err:
                    shallow_sleep(delay)
                    _err = err
            else:
                raise _err

        return wrapper

    return decorator


def event_error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        handler, data = args
        try:
            return func(*args, **kwargs)
        except Exception:
            return {'error': traceback.format_exc(), **data}

    return wrapper


def result_error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        handler, data = args
        if 'error' in data:
            cam_id, update = handler._bot._updates.pop(data['event_id'])
            update.message.reply_text(
                f'{data["error"]}\nTry later or /list other cameras')
            return
        return func(*args, **kwargs)

    return wrapper


def authorization_check(func):
    """User authorization check."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        update, ctx = args
        try:
            if update.message.chat.id not in ctx.bot.user_ids:
                raise UserAuthError
            return func(*args, **kwargs)
        except UserAuthError:
            ctx.bot._log.error('User authorization error')
            ctx.bot._log.error(get_user_info(update))
            print_access_error(update)

    return wrapper


def camera_selection(func):
    """Select camera ID to use."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        update, ctx = args
        cam_id = re.split(CMD_CAM_ID_REGEX, update.message.text)[-1]
        cam_meta = ctx.bot.cam_registry.get_conf(cam_id)

        # Generate unique event id and remember update object
        event_id = uuid.uuid4().hex
        ctx.bot._updates[event_id] = (cam_id, update)
        try:
            return func(*args, cam_id=cam_id, cam_meta=cam_meta,
                        event_id=event_id, **kwargs)
        except Exception:
            # Remove update object from dict in case of any failure
            ctx.bot._log.exception('Failed to process event')
            ctx.bot._updates.pop(event_id, None)

    return wrapper
