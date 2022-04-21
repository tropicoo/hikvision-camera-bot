"""Camera callbacks module."""
import logging

from pyrogram.types import Message

from hikcamerabot.camera import HikvisionCam
from hikcamerabot.camerabot import CameraBot
from hikcamerabot.clients.hikvision.constants import IrcutFilterType
from hikcamerabot.constants import Alarm, Detection, Event, ServiceType, Stream
from hikcamerabot.decorators import authorization_check, camera_selection
from hikcamerabot.event_engine.events.inbound import (
    AlertConfEvent,
    DetectionConfEvent,
    GetPicEvent,
    GetVideoEvent,
    IrcutConfEvent,
    StreamEvent,
)

from hikcamerabot.utils.utils import make_bold

log = logging.getLogger(__name__)


@authorization_check
@camera_selection
async def cmds(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Print camera commands."""
    presentation = bot.cam_registry.get_commands_presentation(cam.id)
    await message.reply_text(
        f'<b>Available commands</b>\n\n{presentation}\n\n/list_cams',
        reply_to_message_id=message.message_id,
        parse_mode='HTML',
    )


@authorization_check
@camera_selection
async def cmd_ir_on(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Get and send resized snapshot from the camera."""
    log.info('Resized cam snapshot from %s requested', cam.description)
    # event = {'cam': cam, 'event': Event.CONFIGURE_IRCUT_FILTER,
    #          'message': message,
    #          'params': {'filter_type': IrcutFilterType.NIGHT}}
    event = IrcutConfEvent(
        cam=cam,
        event=Event.CONFIGURE_IRCUT_FILTER,
        message=message,
        filter_type=IrcutFilterType.NIGHT,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_ir_off(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Get and send resized snapshot from the camera."""
    log.info('Resized cam snapshot from %s requested', cam.description)
    # event = {'cam': cam, 'event': Event.CONFIGURE_IRCUT_FILTER,
    #          'message': message,
    #          'params': {'filter_type': IrcutFilterType.DAY}}
    event = IrcutConfEvent(
        cam=cam,
        event=Event.CONFIGURE_IRCUT_FILTER,
        message=message,
        filter_type=IrcutFilterType.DAY,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_ir_auto(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Get and send resized snapshot from the camera."""
    log.info('Resized cam snapshot from %s requested', cam.description)
    # event = {'cam': cam, 'event': Event.CONFIGURE_IRCUT_FILTER,
    #          'message': message,
    #          'params': {'filter_type': IrcutFilterType.AUTO}}
    event = IrcutConfEvent(
        cam=cam,
        event=Event.CONFIGURE_IRCUT_FILTER,
        message=message,
        filter_type=IrcutFilterType.AUTO,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_getpic(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Get and send resized snapshot from the camera."""
    log.info('Resized cam snapshot from %s requested', cam.description)
    # event = {'cam': cam, 'event': Event.TAKE_SNAPSHOT, 'message': message,
    #          'params': {'resize': True}}
    event = GetPicEvent(
        cam=cam,
        event=Event.TAKE_SNAPSHOT,
        message=message,
        resize=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_getfullpic(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Get and send full snapshot from the camera."""
    log.info('Full cam snapshot requested')
    # event = {'cam': cam, 'event': Event.TAKE_SNAPSHOT, 'message': message,
    #          'params': {'resize': False}}
    event = GetPicEvent(
        cam=cam,
        event=Event.TAKE_SNAPSHOT,
        message=message,
        resize=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_getvideo(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Record video gif."""
    log.info('Get video gif requested')
    # event = {'cam': cam, 'event': Event.RECORD_VIDEOGIF, 'message': message,
    #          'params': {'rewind': False}}
    event = GetVideoEvent(
        cam=cam,
        event=Event.RECORD_VIDEOGIF,
        message=message,
        rewind=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_getvideor(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Record rewind video gif."""
    log.info('Get rewound video gif requested')
    # event = {'cam': cam, 'event': Event.RECORD_VIDEOGIF, 'message': message,
    #          'params': {'rewind': True}}
    event = GetVideoEvent(
        cam=cam,
        event=Event.RECORD_VIDEOGIF,
        message=message,
        rewind=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
async def cmd_stop(bot: CameraBot, message: Message) -> None:
    """Terminate the bot."""
    # log.info(f'Stopping {(await bot.first_name)} bot')
    # TODO: Is this even needed?
    pass


@authorization_check
async def cmd_list_cams(bot: CameraBot, message: Message) -> None:
    """List user's cameras."""
    log.info('Camera list has been requested')
    cam_count = bot.cam_registry.get_count()
    msg = [
        make_bold(
            'You have {0} camera{1}'.format(cam_count, '' if cam_count == 1 else 's')
        )
    ]

    for cam_id, meta in bot.cam_registry.get_all().items():
        msg.append(
            f'<b>Camera:</b> {cam_id}\n'
            f'<b>Description:</b> {meta["cam"].description}\n'
            f'<b>Commands</b>: /cmds_{cam_id}'
        )

    await message.reply_text(
        '\n\n'.join(msg), reply_to_message_id=message.message_id, parse_mode='HTML'
    )
    log.info('Camera list has been sent')


@authorization_check
@camera_selection
async def cmd_intrusion_detection_on(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Enable camera's Intrusion Detection."""
    # event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_DETECTION,
    #          'type': Detection.INTRUSION, 'params': {'switch': True}}
    event = DetectionConfEvent(
        cam=cam,
        event=Event.CONFIGURE_DETECTION,
        type=Detection.INTRUSION,
        message=message,
        switch=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_intrusion_detection_off(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Disable camera's Intrusion Detection."""
    # event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_DETECTION,
    #          'type': Detection.INTRUSION, 'params': {'switch': False}}
    event = DetectionConfEvent(
        cam=cam,
        event=Event.CONFIGURE_DETECTION,
        type=Detection.INTRUSION,
        message=message,
        switch=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_motion_detection_on(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Enable camera's Motion Detection."""
    # event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_DETECTION,
    #          'type': Detection.MOTION, 'params': {'switch': True}}
    event = DetectionConfEvent(
        cam=cam,
        event=Event.CONFIGURE_DETECTION,
        type=Detection.MOTION,
        message=message,
        switch=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_motion_detection_off(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Disable camera's Motion Detection."""
    # event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_DETECTION,
    #          'type': Detection.MOTION, 'params': {'switch': False}}
    event = DetectionConfEvent(
        cam=cam,
        event=Event.CONFIGURE_DETECTION,
        type=Detection.MOTION,
        message=message,
        switch=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_line_detection_on(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Enable camera's Line Crossing Detection."""
    # event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_DETECTION,
    #          'name': Detection.LINE, 'params': {'switch': True}}
    event = DetectionConfEvent(
        cam=cam,
        event=Event.CONFIGURE_DETECTION,
        type=Detection.LINE,
        message=message,
        switch=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_line_detection_off(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Disable camera's Line Crossing Detection."""
    # event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_DETECTION,
    #          'type': Detection.LINE, 'params': {'switch': False}}
    event = DetectionConfEvent(
        cam=cam,
        event=Event.CONFIGURE_DETECTION,
        type=Detection.LINE,
        message=message,
        switch=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_yt_on(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Start YouTube stream."""
    # event = {'cam': cam, 'message': message, 'event': Event.STREAM,
    #          'service_type': ServiceType.STREAM,
    #          'stream_type': Stream.YOUTUBE, 'params': {'switch': True}}
    event = StreamEvent(
        cam=cam,
        event=Event.STREAM,
        service_type=ServiceType.STREAM,
        stream_type=Stream.YOUTUBE,
        message=message,
        switch=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_yt_off(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Stop YouTube stream."""
    # event = {'cam': cam, 'message': message, 'event': Event.STREAM,
    #          'service_type': ServiceType.STREAM,
    #          'stream_type': Stream.YOUTUBE, 'params': {'switch': False}}
    event = StreamEvent(
        cam=cam,
        event=Event.STREAM,
        service_type=ServiceType.STREAM,
        stream_type=Stream.YOUTUBE,
        message=message,
        switch=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_tg_on(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Start Telegram stream."""
    # event = {'cam': cam, 'message': message, 'event': Event.STREAM,
    #          'service_type': ServiceType.STREAM,
    #          'stream_type': Stream.TELEGRAM, 'params': {'switch': True}}
    event = StreamEvent(
        cam=cam,
        event=Event.STREAM,
        service_type=ServiceType.STREAM,
        stream_type=Stream.TELEGRAM,
        message=message,
        switch=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_tg_off(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Stop Telegram stream."""
    # event = {'cam': cam, 'message': message, 'event': Event.STREAM,
    #          'service_type': ServiceType.STREAM,
    #          'stream_type': Stream.TELEGRAM, 'params': {'switch': False}}
    event = StreamEvent(
        cam=cam,
        event=Event.STREAM,
        service_type=ServiceType.STREAM,
        stream_type=Stream.TELEGRAM,
        message=message,
        switch=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_icecast_on(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Start Icecast stream."""
    # event = {'cam': cam, 'message': message, 'event': Event.STREAM,
    #          'service_type': ServiceType.STREAM,
    #          'stream_type': Stream.ICECAST, 'params': {'switch': True}}
    event = StreamEvent(
        cam=cam,
        event=Event.STREAM,
        service_type=ServiceType.STREAM,
        stream_type=Stream.ICECAST,
        message=message,
        switch=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_icecast_off(
    bot: CameraBot, message: Message, cam: HikvisionCam
) -> None:
    """Stop Icecast stream."""
    # event = {'cam': cam, 'message': message, 'event': Event.STREAM,
    #          'service_type': ServiceType.STREAM,
    #          'stream_type': Stream.ICECAST, 'params': {'switch': False}}
    event = StreamEvent(
        cam=cam,
        event=Event.STREAM,
        service_type=ServiceType.STREAM,
        stream_type=Stream.ICECAST,
        message=message,
        switch=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_alert_on(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Enable camera's Alert Mode."""
    log.info('Enabling camera\'s alert mode requested')
    # event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_ALARM,
    #          'service_type': ServiceType.ALARM,
    #          'name': Alarm.ALARM, 'params': {'switch': True}}
    event = AlertConfEvent(
        cam=cam,
        event=Event.CONFIGURE_ALARM,
        service_type=ServiceType.ALARM,
        service_name=Alarm.ALARM,
        message=message,
        switch=True,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_alert_off(bot: CameraBot, message: Message, cam: HikvisionCam) -> None:
    """Disable camera's Alert Mode."""
    log.info('Disabling camera\'s alert mode requested')
    # event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_ALARM,
    #          'service_type': ServiceType.ALARM,
    #          'name': Alarm.ALARM, 'params': {'switch': False}}
    event = AlertConfEvent(
        cam=cam,
        event=Event.CONFIGURE_ALARM,
        service_type=ServiceType.ALARM,
        service_name=Alarm.ALARM,
        message=message,
        switch=False,
    )
    await bot.inbound_dispatcher.dispatch(event)


@authorization_check
async def cmd_help(
    bot: CameraBot,
    message: Message,
    append: bool = False,
    requested: bool = True,
    cam_id: str = None,
) -> None:
    """Send help message to telegram chat."""
    log.info('Help message has been requested')
    await message.reply_text(
        'Use /list_cams command to show available cameras and commands',
        reply_to_message_id=message.message_id,
    )
    log.debug('Help message has been sent')
