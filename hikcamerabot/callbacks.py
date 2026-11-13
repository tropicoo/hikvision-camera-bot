"""Camera callbacks module."""

import logging

from pyrogram.enums import ChatType
from pyrogram.types import Message

from hikcamerabot.camera import HikvisionCam
from hikcamerabot.camerabot import CameraBot
from hikcamerabot.clients.github.version_checker import (
    HikCameraBotVersionChecker,
)
from hikcamerabot.clients.hikvision.enums import IrcutFilterType
from hikcamerabot.decorators import authorization_check, camera_selection
from hikcamerabot.enums import (
    AlarmType,
    DetectionType,
    EventType,
    ServiceType,
    StreamType,
)
from hikcamerabot.event_engine.events.inbound import (
    AlertConfEvent,
    DetectionConfEvent,
    GetPicEvent,
    GetVideoEvent,
    IrcutConfEvent,
    StreamEvent,
)
from hikcamerabot.utils.shared import bold, send_text

log = logging.getLogger(__name__)


@authorization_check
@camera_selection
async def cmds(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Print camera commands."""
    presentation = bot.cam_registry.get_commands_presentation(cam.id)
    text = (
        f'<b>Команды камеры «{cam.description}»</b>\n\n{presentation}\n\n'
        '/menu, /list_cams, /groups, /status, /help'
    )
    await send_text(text=text, message=message, quote=True)


@authorization_check
@camera_selection
async def cmd_ir_on(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Switch the camera to night mode (IR light on)."""
    log.info('Night IR mode for %s requested', cam.description)
    event = IrcutConfEvent(
        cam=cam,
        event=EventType.CONFIGURE_IRCUT_FILTER,
        message=message,
        filter_type=IrcutFilterType.NIGHT,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_ir_off(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Switch the camera to day mode (IR light off)."""
    log.info('Day IR mode for %s requested', cam.description)
    event = IrcutConfEvent(
        cam=cam,
        event=EventType.CONFIGURE_IRCUT_FILTER,
        message=message,
        filter_type=IrcutFilterType.DAY,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_ir_auto(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Let the camera switch day/night mode automatically."""
    log.info('Auto IR mode for %s requested', cam.description)
    event = IrcutConfEvent(
        cam=cam,
        event=EventType.CONFIGURE_IRCUT_FILTER,
        message=message,
        filter_type=IrcutFilterType.AUTO,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_getpic(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Get and send resized snapshot from the camera."""
    log.info('Resized cam snapshot from %s requested', cam.description)
    event = GetPicEvent(
        cam=cam,
        event=EventType.TAKE_SNAPSHOT,
        message=message,
        resize=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_getfullpic(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Get and send full snapshot from the camera."""
    log.info('Full cam snapshot requested')
    event = GetPicEvent(
        cam=cam,
        event=EventType.TAKE_SNAPSHOT,
        message=message,
        resize=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_getvideo(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Record video."""
    log.info('Record video requested')
    event = GetVideoEvent(
        cam=cam,
        event=EventType.RECORD_VIDEOGIF,
        message=message,
        rewind=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_getvideor(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Record rewind video."""
    log.info('Get rewound video requested')
    event = GetVideoEvent(
        cam=cam,
        event=EventType.RECORD_VIDEOGIF,
        message=message,
        rewind=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


def plural_ru(count: int, one: str, few: str, many: str) -> str:
    """Return Russian plural form: 1 камера, 2 камеры, 5 камер."""
    if count % 10 == 1 and count % 100 != 11:  # noqa: PLR2004
        return one
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return few
    return many


def _camera_card(cam: HikvisionCam) -> str:
    return f'📹 <b>{cam.description}</b> ({cam.id})\nКоманды: /cmds_{cam.id}'


@authorization_check
async def cmd_stop(bot: CameraBot, message: Message) -> None:  # noqa: ARG001
    """Explain how to stop the bot: it can't be stopped from Telegram."""
    await send_text(text=STOP_TEXT, message=message, quote=True)


@authorization_check
async def cmd_app_version(bot: CameraBot, message: Message) -> None:  # noqa: ARG001
    """Show current bot version and whether an update is available."""
    checker = HikCameraBotVersionChecker()
    current = checker.get_current_version()
    lines = [f'🤖 Версия бота: <b>{current}</b>']
    try:
        version = await checker.get_version()
    except Exception as err:
        log.warning('Failed to check the latest bot version: %s', err)
        lines.append(
            '⚠️ Не удалось проверить обновления: нет интернета или GitHub '
            'недоступен. Попробуйте позже.'
        )
    else:
        if version.has_new_version():
            lines.append(
                f'🆕 Доступна версия <b>{version.latest}</b>.\n'
                'Чтобы обновить, выполните на устройстве с ботом: '
                '<code>./update.sh</code>'
            )
        else:
            lines.append('✅ Установлена последняя версия.')
    await send_text(text='\n'.join(lines), message=message, quote=True)


async def cmd_unknown(bot: CameraBot, message: Message) -> None:
    """Answer to a mistyped or unknown command instead of silence."""
    text = message.text or ''
    if message.chat.type != ChatType.PRIVATE:
        # In groups answer only to commands addressed to this bot.
        username = getattr(bot.me, 'username', None)
        if not username or f'@{username}'.lower() not in text.lower():
            return
    log.info('Unknown command "%s" from %s', text[:64], message.chat.id)
    await send_text(text=UNKNOWN_COMMAND_TEXT, message=message, quote=True)


@authorization_check
async def cmd_list_group_cams(bot: CameraBot, message: Message) -> None:
    meta = bot.cam_registry.get_group(message.command[0])
    count = len(meta['cams'])
    word = plural_ru(count, 'камера', 'камеры', 'камер')
    msg = [bold(f'В группе «{meta["name"]}» {count} {word}')]
    msg.extend(_camera_card(cam) for cam in meta['cams'])
    msg.append('/groups, /menu, /help')
    await send_text(text='\n\n'.join(msg), message=message, quote=True)


@authorization_check
async def cmd_list_groups(bot: CameraBot, message: Message) -> None:
    group_registry = bot.cam_registry.get_groups_registry()
    count = len(group_registry)
    word = plural_ru(count, 'группа', 'группы', 'групп')
    msg = [bold(f'Группы камер: {count} {word}\n')]

    for command, meta in group_registry.items():
        msg.append(f'/{command} — {meta["name"]}')

    msg.append('\n/list_cams, /menu, /help')
    await send_text(text='\n'.join(msg), message=message, quote=True)


@authorization_check
async def cmd_list_cams(bot: CameraBot, message: Message) -> None:
    """List user's cameras."""
    log.debug('Camera list has been requested from %s', message.chat.id)
    count = bot.cam_registry.count()
    word = plural_ru(count, 'камера', 'камеры', 'камер')
    msg = [bold(f'Подключено: {count} {word}')]
    msg.extend(_camera_card(cam) for cam in bot.cam_registry.get_instances())
    msg.append('/groups, /menu, /help')
    await send_text(text='\n\n'.join(msg), message=message, quote=True)


@authorization_check
@camera_selection
async def cmd_intrusion_detection_on(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Enable camera's Intrusion Detection."""
    event = DetectionConfEvent(
        cam=cam,
        event=EventType.CONFIGURE_DETECTION,
        type=DetectionType.INTRUSION,
        message=message,
        state=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_intrusion_detection_off(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Disable camera's Intrusion Detection."""
    event = DetectionConfEvent(
        cam=cam,
        event=EventType.CONFIGURE_DETECTION,
        type=DetectionType.INTRUSION,
        message=message,
        state=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_motion_detection_on(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Enable camera's Motion Detection."""
    event = DetectionConfEvent(
        cam=cam,
        event=EventType.CONFIGURE_DETECTION,
        type=DetectionType.MOTION,
        message=message,
        state=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_motion_detection_off(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Disable camera's Motion Detection."""
    event = DetectionConfEvent(
        cam=cam,
        event=EventType.CONFIGURE_DETECTION,
        type=DetectionType.MOTION,
        message=message,
        state=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_line_detection_on(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Enable camera's Line Crossing Detection."""
    event = DetectionConfEvent(
        cam=cam,
        event=EventType.CONFIGURE_DETECTION,
        type=DetectionType.LINE,
        message=message,
        state=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_line_detection_off(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Disable camera's Line Crossing Detection."""
    event = DetectionConfEvent(
        cam=cam,
        event=EventType.CONFIGURE_DETECTION,
        type=DetectionType.LINE,
        message=message,
        state=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_yt_on(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Start YouTube stream."""
    event = StreamEvent(
        cam=cam,
        event=EventType.STREAM,
        service_type=ServiceType.STREAM,
        stream_type=StreamType.YOUTUBE,
        message=message,
        state=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_yt_off(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Stop YouTube stream."""
    event = StreamEvent(
        cam=cam,
        event=EventType.STREAM,
        service_type=ServiceType.STREAM,
        stream_type=StreamType.YOUTUBE,
        message=message,
        state=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_tg_on(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Start Telegram stream."""
    event = StreamEvent(
        cam=cam,
        event=EventType.STREAM,
        service_type=ServiceType.STREAM,
        stream_type=StreamType.TELEGRAM,
        message=message,
        state=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_tg_off(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Stop Telegram stream."""
    event = StreamEvent(
        cam=cam,
        event=EventType.STREAM,
        service_type=ServiceType.STREAM,
        stream_type=StreamType.TELEGRAM,
        message=message,
        state=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_icecast_on(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Start Icecast stream."""
    event = StreamEvent(
        cam=cam,
        event=EventType.STREAM,
        service_type=ServiceType.STREAM,
        stream_type=StreamType.ICECAST,
        message=message,
        state=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_icecast_off(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Stop Icecast stream."""
    event = StreamEvent(
        cam=cam,
        event=EventType.STREAM,
        service_type=ServiceType.STREAM,
        stream_type=StreamType.ICECAST,
        message=message,
        state=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_alert_on(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Enable camera's Alert Mode."""
    log.info("Enabling camera's alert mode requested")
    event = AlertConfEvent(
        cam=cam,
        event=EventType.CONFIGURE_ALARM,
        service_type=ServiceType.ALARM,
        service_name=AlarmType.ALARM,
        message=message,
        state=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_alert_off(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Disable camera's Alert Mode."""
    log.info("Disabling camera's alert mode requested")
    event = AlertConfEvent(
        cam=cam,
        event=EventType.CONFIGURE_ALARM,
        service_type=ServiceType.ALARM,
        service_name=AlarmType.ALARM,
        message=message,
        state=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


HELP_TEXT = (
    '<b>🤖 Бот для камер Hikvision</b>\n'
    'Присылает фото и видео с камер, сообщает о тревогах (движение, '
    'пересечение линии, вторжение) и следит за состоянием устройства.\n\n'
    '<b>С чего начать</b>\n'
    'Нажмите кнопку «📋 Меню» под полем ввода или отправьте /menu — '
    'откроется панель с кнопками:\n'
    '• 📷 Фото / 🖼 Полное фото — снимок с камеры\n'
    '• 🎥 Видео — короткая запись с камеры\n'
    '• 🔔 Оповещения — включить или выключить сообщения о тревогах\n'
    '• 🌙 ☀️ 🌗 — режим ночь / день / авто\n'
    '• ⚙️ Настройки — какие детекции включены и что присылать при тревоге\n\n'
    '<b>Основные команды</b>\n'
    '/menu — панель управления с кнопками\n'
    '/status — состояние бота, диска и камер\n'
    '/list_cams — список камер и их команды\n'
    '/groups — группы камер\n'
    '/version — версия бота и наличие обновления\n'
    '/help — эта справка\n\n'
    '<b>Если что-то не работает</b>\n'
    '• «Камера не отвечает» — проверьте питание камеры и сеть, затем '
    'повторите команду.\n'
    '• «Камера отклонила логин или пароль» — исправьте user и password '
    'камеры в configs/config.json и перезапустите бота.\n'
    '• Не приходят тревоги — откройте /menu и проверьте, что оповещения и '
    'нужные детекции отмечены ✅.\n'
    '• Бот не отвечает — на устройстве с ботом выполните '
    '<code>docker compose restart hikvision-camera-bot</code>, логи: '
    '<code>docker compose logs --tail 100 hikvision-camera-bot</code>'
)

STOP_TEXT = (
    '🛑 Остановить бота из Telegram нельзя: он работает как служба и '
    'запускается сам после перезагрузки.\n\n'
    'Остановить на устройстве с ботом: <code>docker compose stop</code>\n'
    'Запустить снова: <code>docker compose up -d</code>\n\n'
    'Чтобы просто не получать тревоги, выключите оповещения в /menu.'
)

UNKNOWN_COMMAND_TEXT = (
    '🤔 Не знаю такую команду. Откройте /menu, чтобы управлять камерами '
    'кнопками, или /help — там список команд.'
)
