"""Inline keyboard menu: control cameras with buttons instead of typing commands.

The menu lives in a single message ("panel") that is edited in place: toggles
answer with a short popup instead of new chat messages. Alert settings changed
from the menu are saved to `configs/config.json` and survive bot restarts.
"""

import contextlib
import inspect
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Final

from pyrogram.errors import MessageNotModified
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

import hikcamerabot.callbacks as cb
from hikcamerabot.clients.hikvision.enums import IrcutFilterType
from hikcamerabot.config.schemas.main_config import AlertSchema, DetectionSchema
from hikcamerabot.config.store import ConfigStore
from hikcamerabot.constants import TG_MAX_MSG_SIZE
from hikcamerabot.decorators import authorization_check
from hikcamerabot.enums import DetectionType
from hikcamerabot.exceptions import HikvisionAPIError, ServiceRuntimeError
from hikcamerabot.health import build_status_text
from hikcamerabot.utils.errors import describe_error
from hikcamerabot.utils.shared import send_text

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam
    from hikcamerabot.camerabot import CameraBot

log = logging.getLogger(__name__)

CALLBACK_PREFIX: Final[str] = 'hcb'
_SEP: Final[str] = '|'
_ARG_SEP: Final[str] = ':'

# Text of the persistent reply keyboard button that opens the panel.
MENU_BUTTON_TEXT: Final[str] = '📋 Меню'
MENU_REPLY_KEYBOARD: Final[ReplyKeyboardMarkup] = ReplyKeyboardMarkup(
    [[KeyboardButton(MENU_BUTTON_TEXT)]],
    is_persistent=True,
    resize_keyboard=True,
)

_ACTION_CAMERAS: Final[str] = 'cams'
_ACTION_CAMERA: Final[str] = 'cam'
_ACTION_STATUS: Final[str] = 'status'
_ACTION_CLOSE: Final[str] = 'close'
_ACTION_ALERT: Final[str] = 'alert'
_ACTION_IR: Final[str] = 'ir'
_ACTION_SETTINGS: Final[str] = 'settings'
_ACTION_DETECTION: Final[str] = 'det'
_ACTION_DETECTION_TOGGLE: Final[str] = 'dett'
_ACTION_OPTION: Final[str] = 'opt'
_ACTION_DELAY: Final[str] = 'delay'

# Action -> (callback, short confirmation shown in Telegram).
# Callbacks are the same functions used by text commands like `/getpic_cam_1`.
# They send photos/videos, so new chat messages are expected here.
_CAMERA_ACTIONS: Final[dict[str, tuple[Callable, str]]] = {
    'pic': (cb.cmd_getpic, '📷 Делаю снимок...'),
    'fullpic': (cb.cmd_getfullpic, '🖼 Делаю полный снимок...'),
    'video': (cb.cmd_getvideo, '🎥 Записываю видео...'),
    'videor': (cb.cmd_getvideor, '⏪ Записываю видео с перемоткой...'),
}

# Short code -> (detection type, label, visibility section name).
_DETECTIONS: Final[dict[str, tuple[DetectionType, str, str]]] = {
    'ld': (DetectionType.LINE, '〰️ Линия', 'line_detection'),
    'md': (DetectionType.MOTION, '🏃 Движение', 'motion_detection'),
    'intr': (DetectionType.INTRUSION, '🚷 Вторжение', 'intrusion_detection'),
}

# Short code -> (detection schema field, label).
_DETECTION_OPTIONS: Final[dict[str, tuple[str, str]]] = {
    'pic': ('sendpic', '📷 Фото'),
    'full': ('fullpic', '🖼 Полное фото'),
    'vid': ('send_videogif', '🎥 Видео'),
    'txt': ('send_text', '💬 Текст'),
}

# Short code -> (filter type, label).
_IR_MODES: Final[dict[str, tuple[IrcutFilterType, str]]] = {
    'night': (IrcutFilterType.NIGHT, '🌙 Ночь'),
    'day': (IrcutFilterType.DAY, '☀️ День'),
    'auto': (IrcutFilterType.AUTO, '🌗 Авто'),
}

ALERT_DELAY_STEP: Final[int] = 5
ALERT_DELAY_MAX: Final[int] = 600

_ON: Final[str] = '✅'
_OFF: Final[str] = '❌'

_config_store = ConfigStore()

# Chat ID -> message ID of the last opened panel, to keep only one in chat.
_panels: dict[int, int] = {}
# Camera ID -> last IR mode set from the menu (camera doesn't report it).
_ir_modes: dict[str, str] = {}


def make_callback_data(action: str, cam_id: str = '', *args: str) -> str:
    return _SEP.join((CALLBACK_PREFIX, _ARG_SEP.join((action, *args)), cam_id))


def parse_callback_data(data: str) -> tuple[str, str] | None:
    """Return (action, cam_id) or None if data doesn't belong to this menu.

    Action may contain arguments, e.g. `opt:md:pic`.
    """
    parts = data.split(_SEP)
    if len(parts) != 3 or parts[0] != CALLBACK_PREFIX:  # noqa: PLR2004
        return None
    return parts[1], parts[2]


def _btn(text: str, action: str, cam_id: str = '', *args: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text, callback_data=make_callback_data(action, cam_id, *args)
    )


def _mark(state: bool) -> str:
    return _ON if state else _OFF


def _visible_detections(cam: 'HikvisionCam') -> list[str]:
    visibility = cam.conf.command_sections_visibility
    return [
        code
        for code, (_, _, section) in _DETECTIONS.items()
        if getattr(visibility, section)
    ]


def _is_settings_visible(cam: 'HikvisionCam') -> bool:
    return cam.conf.command_sections_visibility.alert_service or bool(
        _visible_detections(cam)
    )


def _detection_conf(cam: 'HikvisionCam', code: str) -> DetectionSchema:
    return cam.conf.alert.get_detection_schema_by_type(_DETECTIONS[code][0])


# Keyboards and texts.


def build_cameras_keyboard(bot: 'CameraBot') -> InlineKeyboardMarkup:
    rows = [
        [_btn(f'📹 {cam.description} ({cam.id})', _ACTION_CAMERA, cam.id)]
        for cam in bot.cam_registry.get_instances()
    ]
    rows.append([_btn('🤖 Статус', _ACTION_STATUS), _btn('✖️', _ACTION_CLOSE)])
    return InlineKeyboardMarkup(rows)


_CAMERAS_TEXT: Final[str] = '<b>📹 Камеры</b>\nВыберите камеру:'


def build_camera_keyboard(
    cam: 'HikvisionCam', show_back: bool = True
) -> InlineKeyboardMarkup:
    """Build camera control panel respecting `command_sections_visibility`."""
    visibility = cam.conf.command_sections_visibility
    cam_id = cam.id
    rows: list[list[InlineKeyboardButton]] = []
    if visibility.general:
        rows.append(
            [_btn('📷 Фото', 'pic', cam_id), _btn('🖼 Полное фото', 'fullpic', cam_id)]
        )
        rows.append(
            [
                _btn('🎥 Видео', 'video', cam_id),
                _btn('⏪ Видео+перемотка', 'videor', cam_id),
            ]
        )
    if visibility.alert_service:
        started = cam.services.alarm.started
        rows.append(
            [
                _btn(
                    f'{"🔔" if started else "🔕"} Оповещения {_mark(started)}',
                    _ACTION_ALERT,
                    cam_id,
                )
            ]
        )
    if visibility.infrared:
        current = _ir_modes.get(cam_id)
        rows.append(
            [
                _btn(
                    f'• {label} •' if code == current else label,
                    _ACTION_IR,
                    cam_id,
                    code,
                )
                for code, (_, label) in _IR_MODES.items()
            ]
        )
    last_row = [_btn('🔄', _ACTION_CAMERA, cam_id), _btn('🤖 Статус', _ACTION_STATUS)]
    if _is_settings_visible(cam):
        last_row.insert(0, _btn('⚙️ Настройки', _ACTION_SETTINGS, cam_id))
    rows.append(last_row)
    nav_row = [_btn('✖️ Закрыть', _ACTION_CLOSE)]
    if show_back:
        nav_row.insert(0, _btn('⬅️ Камеры', _ACTION_CAMERAS))
    rows.append(nav_row)
    return InlineKeyboardMarkup(rows)


def build_camera_text(cam: 'HikvisionCam') -> str:
    visibility = cam.conf.command_sections_visibility
    lines = [f'<b>📹 {cam.description}</b> ({cam.id})', '']
    if visibility.alert_service:
        started = cam.services.alarm.started
        lines.append(f'🔔 Оповещения: <b>{"вкл" if started else "выкл"}</b>')
    detections = _visible_detections(cam)
    if detections:
        states = ' · '.join(
            f'{_DETECTIONS[code][1]} {_mark(_detection_conf(cam, code).enabled)}'
            for code in detections
        )
        lines.append(f'🎯 Детекции: {states}')
    if visibility.alert_service:
        lines.append(f'⏱ Пауза между тревогами: {cam.conf.alert.delay} с')
    if visibility.infrared and cam.id in _ir_modes:
        lines.append(f'🌗 ИК-режим: {_IR_MODES[_ir_modes[cam.id]][1]}')
    return '\n'.join(lines)


def build_settings_keyboard(cam: 'HikvisionCam') -> InlineKeyboardMarkup:
    cam_id = cam.id
    rows = [
        [
            _btn(
                f'{_DETECTIONS[code][1]} {_mark(_detection_conf(cam, code).enabled)}',
                _ACTION_DETECTION_TOGGLE,
                cam_id,
                code,
            ),
            _btn('⚙️', _ACTION_DETECTION, cam_id, code),
        ]
        for code in _visible_detections(cam)
    ]
    if cam.conf.command_sections_visibility.alert_service:
        rows.append(
            [
                _btn(f'-{ALERT_DELAY_STEP} с', _ACTION_DELAY, cam_id, '-'),
                _btn(f'⏱ {cam.conf.alert.delay} с', _ACTION_SETTINGS, cam_id),
                _btn(f'+{ALERT_DELAY_STEP} с', _ACTION_DELAY, cam_id, '+'),
            ]
        )
    rows.append([_btn('⬅️ Назад', _ACTION_CAMERA, cam_id)])
    return InlineKeyboardMarkup(rows)


def build_settings_text(cam: 'HikvisionCam') -> str:
    return (
        f'<b>⚙️ Настройки тревог</b> — {cam.description} ({cam.id})\n\n'
        'Нажмите на детекцию, чтобы включить или выключить её на камере, '
        '⚙️ — что присылать при тревоге.\n'
        '⏱ — пауза между тревогами.\n\n'
        '<i>Изменения сохраняются в config.json.</i>'
    )


def build_detection_keyboard(cam: 'HikvisionCam', code: str) -> InlineKeyboardMarkup:
    conf = _detection_conf(cam, code)
    buttons = [
        _btn(
            f'{label} {_mark(getattr(conf, field))}',
            _ACTION_OPTION,
            cam.id,
            code,
            opt_code,
        )
        for opt_code, (field, label) in _DETECTION_OPTIONS.items()
    ]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.insert(
        0,
        [
            _btn(
                f'Детекция {_mark(conf.enabled)}',
                _ACTION_DETECTION_TOGGLE,
                cam.id,
                code,
                'det',
            )
        ],
    )
    rows.append([_btn('⬅️ Назад', _ACTION_SETTINGS, cam.id)])
    return InlineKeyboardMarkup(rows)


def build_detection_text(cam: 'HikvisionCam', code: str) -> str:
    return (
        f'<b>{_DETECTIONS[code][1]}</b> — {cam.description} ({cam.id})\n\n'
        'Что присылать при тревоге:'
    )


def _status_keyboard(back_cam_id: str) -> InlineKeyboardMarkup:
    back = (
        _btn('⬅️ Назад', _ACTION_CAMERA, back_cam_id)
        if back_cam_id
        else _btn('⬅️ Назад', _ACTION_CAMERAS)
    )
    return InlineKeyboardMarkup(
        [[back, _btn('🔄', _ACTION_STATUS, back_cam_id), _btn('✖️', _ACTION_CLOSE)]]
    )


# Commands.


async def cmd_start(bot: 'CameraBot', message: Message) -> None:  # noqa: ARG001
    """Send help message (`/start`, `/help`) and show the persistent menu button."""
    await message.reply_text(cb.HELP_TEXT, reply_markup=MENU_REPLY_KEYBOARD, quote=True)


@authorization_check
async def cmd_menu(bot: 'CameraBot', message: Message) -> None:
    """Show inline camera control panel, replacing the previous one."""
    chat_id = message.chat.id
    # Keep the chat clean: remove the command itself and the old panel.
    with contextlib.suppress(Exception):
        await message.delete()
    old_panel_id = _panels.pop(chat_id, None)
    if old_panel_id:
        with contextlib.suppress(Exception):
            await bot.delete_messages(chat_id, old_panel_id)

    cams = list(bot.cam_registry.get_instances())
    if len(cams) == 1:
        text, markup = (
            build_camera_text(cams[0]),
            build_camera_keyboard(cams[0], show_back=False),
        )
    else:
        text, markup = _CAMERAS_TEXT, build_cameras_keyboard(bot)
    panel = await bot.send_message(chat_id, text, reply_markup=markup)
    _panels[chat_id] = panel.id


@authorization_check
async def cmd_status(bot: 'CameraBot', message: Message) -> None:
    """Show bot, host (CPU temp, RAM, disk) and camera services status."""
    await send_text(
        text=build_status_text(bot, bot.started_at), message=message, quote=True
    )


# Button presses.


async def _edit(message: Message, text: str, markup: InlineKeyboardMarkup) -> None:
    with contextlib.suppress(MessageNotModified):
        await message.edit_text(text[:TG_MAX_MSG_SIZE], reply_markup=markup)


async def on_menu_callback(bot: 'CameraBot', query: CallbackQuery) -> None:
    """Handle inline menu button presses."""
    parsed = parse_callback_data(query.data or '')
    message = query.message
    if parsed is None or message is None:
        await query.answer()
        return

    # Same rules as for text commands: both user and chat must be allowed.
    if (
        query.from_user is None
        or query.from_user.id not in bot.chat_users
        or message.chat.id not in bot.chat_users
    ):
        log.error('Menu authorization error: user %s', query.from_user)
        await query.answer('⛔ Нет доступа', show_alert=True)
        return

    action, cam_id = parsed
    try:
        await _process_action(bot, query, message, action, cam_id)
    except Exception as err:
        log.exception('Failed to process menu action "%s" for "%s"', action, cam_id)
        # The query may be already answered.
        with contextlib.suppress(Exception):
            await query.answer(describe_error(err), show_alert=True)


async def _process_action(  # noqa: PLR0911
    bot: 'CameraBot',
    query: CallbackQuery,
    message: Message,
    action: str,
    cam_id: str,
) -> None:
    action, *args = action.split(_ARG_SEP)

    if action == _ACTION_CAMERAS:
        await _edit(message, _CAMERAS_TEXT, build_cameras_keyboard(bot))
        await query.answer()
        return

    if action == _ACTION_STATUS:
        await query.answer('🤖 Собираю статус...')
        await _edit(
            message, build_status_text(bot, bot.started_at), _status_keyboard(cam_id)
        )
        return

    if action == _ACTION_CLOSE:
        _panels.pop(message.chat.id, None)
        await query.answer()
        await message.delete()
        return

    try:
        cam = bot.cam_registry.get_instance(cam_id)
    except KeyError:
        await query.answer('Камера не найдена, откройте /menu заново', show_alert=True)
        return

    if action == _ACTION_CAMERA:
        await _show_camera(bot, message, cam)
        await query.answer()
        return

    if action == _ACTION_SETTINGS:
        await _show_settings(message, cam)
        await query.answer()
        return

    if action == _ACTION_DETECTION and args and args[0] in _DETECTIONS:
        await _show_detection(message, cam, args[0])
        await query.answer()
        return

    handler = _TOGGLE_HANDLERS.get(action)
    if handler:
        answer_text = await handler(message, cam, *args)
        await query.answer(answer_text)
        return

    if action not in _CAMERA_ACTIONS:
        await query.answer(
            'Неизвестное действие, откройте /menu заново', show_alert=True
        )
        return

    callback, answer_text = _CAMERA_ACTIONS[action]
    await query.answer(answer_text)
    await _run_camera_action(bot, message, cam, action, callback)


async def _run_camera_action(
    bot: 'CameraBot',
    message: Message,
    cam: 'HikvisionCam',
    action: str,
    callback: Callable,
) -> None:
    try:
        # Skip decorators: authorization is checked above and camera is known.
        await inspect.unwrap(callback)(bot, message, cam=cam)
    except Exception as err:
        log.exception('[%s] Menu action "%s" failed', cam.id, action)
        # The query is already answered, so tell about the failure in chat.
        await bot.send_message(
            message.chat.id,
            f'🛑 <b>Не получилось</b> — {cam.description} ({cam.id})\n\n'
            f'{describe_error(err)}',
        )


async def _show_camera(bot: 'CameraBot', message: Message, cam: 'HikvisionCam') -> None:
    show_back = len(list(bot.cam_registry.get_instances())) > 1
    await _edit(
        message, build_camera_text(cam), build_camera_keyboard(cam, show_back=show_back)
    )


async def _show_settings(message: Message, cam: 'HikvisionCam') -> None:
    await _edit(message, build_settings_text(cam), build_settings_keyboard(cam))


async def _show_detection(message: Message, cam: 'HikvisionCam', code: str) -> None:
    await _edit(
        message, build_detection_text(cam, code), build_detection_keyboard(cam, code)
    )


async def _save_alert(cam: 'HikvisionCam', alert: AlertSchema) -> str:
    """Apply new alert settings and save them to config. Return a note on failure."""
    cam.update_alert_conf(alert)
    try:
        await _config_store.save_camera_alert(cam.id, alert)
    except Exception:
        log.exception('[%s] Failed to save alert settings to config', cam.id)
        return ' (⚠️ не сохранено в config.json)'
    return ''


def _service_error_text(err: ServiceRuntimeError) -> str:
    """Explain camera API errors; show service's own message otherwise."""
    if isinstance(err.__cause__, HikvisionAPIError):
        return describe_error(err)
    return f'❌ {err}'


def _updated_alert(cam: 'HikvisionCam', **update: object) -> AlertSchema:
    """Return validated copy of camera alert settings with updated fields."""
    data = cam.conf.alert.model_dump()
    data.update(update)
    return AlertSchema.model_validate(data)


async def _toggle_alert(message: Message, cam: 'HikvisionCam') -> str:
    alarm = cam.services.alarm
    state = not alarm.started
    try:
        if state:
            await alarm.start()
        else:
            await alarm.stop()
    except ServiceRuntimeError as err:
        return _service_error_text(err)
    if state and not alarm.started:
        return '⚠️ Камера за NVR — оповещения не запускаются'

    note = await _save_alert(cam, _updated_alert(cam, enabled=state))
    await _show_camera(cam.bot, message, cam)
    if state and not any(_detection_conf(cam, code).enabled for code in _DETECTIONS):
        return f'🔔 Оповещения включены, но все детекции выключены{note}'
    return f'{"🔔 Оповещения включены" if state else "🔕 Оповещения выключены"}{note}'


async def _set_ir_mode(message: Message, cam: 'HikvisionCam', code: str = '') -> str:
    if code not in _IR_MODES:
        return 'Неизвестный режим'
    filter_type, label = _IR_MODES[code]
    await cam.set_ircut_filter(filter_type)
    _ir_modes[cam.id] = code
    await _show_camera(cam.bot, message, cam)
    return f'{label}: режим включён'


async def _toggle_detection(
    message: Message, cam: 'HikvisionCam', code: str = '', source: str = ''
) -> str:
    if code not in _DETECTIONS:
        return 'Неизвестная детекция'
    detection_type, label, _ = _DETECTIONS[code]
    state = not _detection_conf(cam, code).enabled
    try:
        # Switch detection on the camera itself, like `/md_on_cam_1` does.
        await cam.services.alarm.trigger_switch(trigger=detection_type, state=state)
    except ServiceRuntimeError as err:
        return _service_error_text(err)

    detection = _detection_conf(cam, code).model_copy(update={'enabled': state})
    note = await _save_alert(
        cam, _updated_alert(cam, **{detection_type.value: detection.model_dump()})
    )
    if source == 'det':
        await _show_detection(message, cam, code)
    else:
        await _show_settings(message, cam)
    return f'{label}: {"включено" if state else "выключено"}{note}'


async def _toggle_option(
    message: Message, cam: 'HikvisionCam', code: str = '', opt_code: str = ''
) -> str:
    if code not in _DETECTIONS or opt_code not in _DETECTION_OPTIONS:
        return 'Неизвестная настройка'
    detection_type = _DETECTIONS[code][0]
    field, label = _DETECTION_OPTIONS[opt_code]
    detection = _detection_conf(cam, code)
    state = not getattr(detection, field)
    detection = detection.model_copy(update={field: state})
    note = await _save_alert(
        cam, _updated_alert(cam, **{detection_type.value: detection.model_dump()})
    )
    await _show_detection(message, cam, code)
    return f'{label}: {"вкл" if state else "выкл"}{note}'


async def _change_delay(message: Message, cam: 'HikvisionCam', sign: str = '+') -> str:
    step = ALERT_DELAY_STEP if sign == '+' else -ALERT_DELAY_STEP
    delay = min(max(cam.conf.alert.delay + step, 0), ALERT_DELAY_MAX)
    if delay == cam.conf.alert.delay:
        return f'⏱ {delay} с — предел'
    note = await _save_alert(cam, _updated_alert(cam, delay=delay))
    await _show_settings(message, cam)
    return f'⏱ Пауза между тревогами: {delay} с{note}'


_TOGGLE_HANDLERS: Final[dict[str, Callable]] = {
    _ACTION_ALERT: _toggle_alert,
    _ACTION_IR: _set_ir_mode,
    _ACTION_DETECTION_TOGGLE: _toggle_detection,
    _ACTION_OPTION: _toggle_option,
    _ACTION_DELAY: _change_delay,
}
