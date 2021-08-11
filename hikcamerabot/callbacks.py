"""Camera callbacks module."""
import logging

from aiogram.types import Message

from hikcamerabot.camera import HikvisionCam
from hikcamerabot.camerabot import CameraBot
from hikcamerabot.constants import Alarm, Detection, Event, Stream
from hikcamerabot.decorators import authorization_check, camera_selection
from hikcamerabot.utils.utils import build_command_presentation, make_bold

log = logging.getLogger(__name__)


@authorization_check
@camera_selection
async def cmds(message: Message, bot: CameraBot, cam: HikvisionCam) -> None:
    """Print camera commands."""
    commands = message.bot.cam_registry.get_commands(cam.id)
    presentation = build_command_presentation(commands)
    await message.answer(
        f'<b>Available commands</b>\n\n{presentation}\n\n/list_cams',
        parse_mode='HTML')


@authorization_check
@camera_selection
async def cmd_getpic(message: Message, bot: CameraBot, cam: HikvisionCam) -> None:
    """Get and send resized snapshot from the camera."""
    log.info('Resized cam snapshot from %s requested', cam.description)
    event = {'cam': cam, 'event': Event.TAKE_SNAPSHOT, 'message': message,
             'params': {'resize': True}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_getfullpic(message: Message, bot: CameraBot,
                         cam: HikvisionCam) -> None:
    """Get and send full snapshot from the camera."""
    log.info('Full cam snapshot requested')
    event = {'cam': cam, 'event': Event.TAKE_SNAPSHOT, 'message': message,
             'params': {'resize': False}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_getvideo(message: Message, bot: CameraBot,
                       cam: HikvisionCam) -> None:
    """Get and send full snapshot from the camera."""
    log.info('Get video gif requested')
    event = {'cam': cam, 'event': Event.RECORD_VIDEOGIF, 'message': message,
             'params': {}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
async def cmd_stop(message: Message) -> None:
    """Terminate the bot."""
    # log.info(f'Stopping {(await bot.first_name)} bot')
    # TODO: Is this even needed?
    pass


@authorization_check
async def cmd_list_cams(message: Message) -> None:
    """List user's cameras."""
    log.info('Camera list has been requested')

    cam_count: int = message.bot.cam_registry.get_count()
    msg = [make_bold('You have {0} camera{1}'.format(
        cam_count, '' if cam_count == 1 else 's'))]

    for cam_id, meta in message.bot.cam_registry.get_all().items():
        msg.append(
            f'<b>Camera:</b> {cam_id}\n'
            f'<b>Description:</b> {meta["cam"].description}\n'
            f'<b>Commands</b>: /cmds_{cam_id}')

    await message.answer('\n\n'.join(msg), parse_mode='HTML')
    log.info('Camera list has been sent')


@authorization_check
@camera_selection
async def cmd_intrusion_detection_on(message: Message, bot: CameraBot,
                                     cam: HikvisionCam) -> None:
    """Enable camera's Intrusion Detection."""
    event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_DETECTION,
             'name': Detection.INTRUSION.value, 'params': {'switch': True}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_intrusion_detection_off(message: Message, bot: CameraBot,
                                      cam: HikvisionCam) -> None:
    """Disable camera's Intrusion Detection."""
    event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_DETECTION,
             'name': Detection.INTRUSION.value, 'params': {'switch': False}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_motion_detection_on(message: Message, bot: CameraBot,
                                  cam: HikvisionCam) -> None:
    """Enable camera's Motion Detection."""
    event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_DETECTION,
             'name': Detection.MOTION.value, 'params': {'switch': True}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_motion_detection_off(message: Message, bot: CameraBot,
                                   cam: HikvisionCam) -> None:
    """Disable camera's Motion Detection."""
    event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_DETECTION,
             'name': Detection.MOTION.value, 'params': {'switch': False}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_line_detection_on(message: Message, bot: CameraBot,
                                cam: HikvisionCam) -> None:
    """Enable camera's Line Crossing Detection."""
    event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_DETECTION,
             'name': Detection.LINE.value, 'params': {'switch': True}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_line_detection_off(message: Message, bot: CameraBot,
                                 cam: HikvisionCam) -> None:
    """Disable camera's Line Crossing Detection."""
    event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_DETECTION,
             'name': Detection.LINE.value, 'params': {'switch': False}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_yt_on(message: Message, bot: CameraBot,
                           cam: HikvisionCam) -> None:
    """Start YouTube stream."""
    event = {'cam': cam, 'message': message, 'event': Event.STREAM,
             'name': Stream.YOUTUBE, 'params': {'switch': True}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_yt_off(message: Message, bot: CameraBot,
                            cam: HikvisionCam) -> None:
    """Stop YouTube stream."""
    event = {'cam': cam, 'message': message, 'event': Event.STREAM,
             'name': Stream.YOUTUBE, 'params': {'switch': False}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_icecast_on(message: Message, bot: CameraBot,
                                cam: HikvisionCam) -> None:
    """Start Icecast stream."""
    event = {'cam': cam, 'message': message, 'event': Event.STREAM,
             'name': Stream.ICECAST, 'params': {'switch': True}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_stream_icecast_off(message: Message, bot: CameraBot,
                                 cam: HikvisionCam) -> None:
    """Stop Icecast stream."""
    event = {'cam': cam, 'message': message, 'event': Event.STREAM,
             'name': Stream.ICECAST, 'params': {'switch': False}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_alert_on(message: Message, bot: CameraBot,
                       cam: HikvisionCam) -> None:
    """Enable camera's Alert Mode."""
    log.info('Enabling camera\'s alert mode requested')
    event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_ALARM,
             'name': Alarm.ALARM, 'params': {'switch': True}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
@camera_selection
async def cmd_alert_off(message: Message, bot: CameraBot,
                        cam: HikvisionCam) -> None:
    """Disable camera's Alert Mode."""
    log.info('Disabling camera\'s alert mode requested')
    event = {'cam': cam, 'message': message, 'event': Event.CONFIGURE_ALARM,
             'name': Alarm.ALARM, 'params': {'switch': False}}
    await bot.event_dispatcher.dispatch(event)


@authorization_check
async def cmd_help(message: Message, append: bool = False, requested: bool = True,
                   cam_id: str = None) -> None:
    """Send help message to telegram chat."""
    log.info('Help message has been requested')
    await message.answer(
        'Use /list_cams command to show available cameras and commands')
    log.debug('Help message has been sent')
