"""Camera callbacks module."""

import logging
from threading import Thread

from telegram.ext import run_async

from hikcamerabot.constants import Detections, Streams, Alarms, Events
from hikcamerabot.decorators import authorization_check, camera_selection
from hikcamerabot.utils import (build_commands_presentation, make_bold,
                                get_user_info)

log = logging.getLogger(__name__)


def error_handler(update, ctx):
    """Handle known Telegram bot API errors."""
    log.exception('Got error: %s', ctx.error)


@authorization_check
@camera_selection
@run_async
def cmds(update, ctx, cam_id, cam_meta, event_id):
    """Print camera commands."""
    cmd_help(update, ctx, append=True, requested=False, cam_id=cam_id)


@authorization_check
@camera_selection
@run_async
def cmd_getpic(update, ctx, cam_id, cam_meta, event_id):
    """Get and send resized snapshot from the camera."""
    log.info('Resized cam snapshot from %s requested', cam_meta.description)
    log.debug(get_user_info(update))
    payload = {'event': Events.TAKE_SNAPSHOT,
               'event_id': event_id,
               'params': {'resize': True}}
    ctx.bot.event_manager.send_event(cam_id, payload)


@authorization_check
@camera_selection
@run_async
def cmd_getfullpic(update, ctx, cam_id, cam_meta, event_id):
    """Get and send full snapshot from the camera."""
    log.info('Full cam snapshot requested')
    log.debug(get_user_info(update))
    payload = {'event': Events.TAKE_SNAPSHOT,
               'event_id': event_id,
               'params': {'resize': False}}
    ctx.bot.event_manager.send_event(cam_id, payload)


@authorization_check
@run_async
def cmd_stop(update, ctx):
    """Terminate bot."""
    msg = f'Stopping {ctx.bot.first_name} bot'
    log.info(msg)
    log.debug(get_user_info(update))
    update.message.reply_text(msg)
    ctx.bot.thread_manager.stop_threads()
    ctx.bot.proc_manager.stop_processes()
    thread = Thread(target=ctx.bot.stop_polling)
    thread.start()


@authorization_check
@run_async
def cmd_list_cams(update, ctx):
    """List user's cameras."""
    log.info('Camera list has been requested')

    cam_count = ctx.bot.cam_registry.get_count()
    msg = [make_bold('You have {0} camera{1}'.format(
        cam_count, '' if cam_count == 1 else 's'))]

    for cam_id, meta in ctx.bot.cam_registry.get_all().items():
        presentation = build_commands_presentation(ctx.bot, cam_id)
        msg.append(
            '<b>Camera:</b> {0}\n'
            '<b>Description:</b> {1}\n'
            '<b>Commands</b>\n'
            '{2}'.format(cam_id, meta['conf'].description, presentation))

    update.message.reply_html('\n\n'.join(msg))
    log.info('Camera list has been sent')


@authorization_check
@camera_selection
@run_async
def cmd_intrusion_detection_off(update, ctx, cam_id, cam_meta, event_id):
    """Disable camera's Intrusion Detection."""
    payload = {'event': Events.CONFIGURE_DETECTION,
               'event_id': event_id,
               'name': Detections.INTRUSION,
               'params': {'switch': False}}
    ctx.bot.event_manager.send_event(cam_id, payload)


@authorization_check
@camera_selection
@run_async
def cmd_intrusion_detection_on(update, ctx, cam_id, cam_meta, event_id):
    """Enable camera's Intrusion Detection."""
    payload = {'event': Events.CONFIGURE_DETECTION,
               'event_id': event_id,
               'name': Detections.INTRUSION,
               'params': {'switch': True}}
    ctx.bot.event_manager.send_event(cam_id, payload)


@authorization_check
@camera_selection
@run_async
def cmd_motion_detection_off(update, ctx, cam_id, cam_meta, event_id):
    """Disable camera's Motion Detection."""
    payload = {'event': Events.CONFIGURE_DETECTION,
               'event_id': event_id,
               'name': Detections.MOTION,
               'params': {'switch': False}}
    ctx.bot.event_manager.send_event(cam_id, payload)


@authorization_check
@camera_selection
@run_async
def cmd_motion_detection_on(update, ctx, cam_id, cam_meta, event_id):
    """Enable camera's Motion Detection."""
    payload = {'event': Events.CONFIGURE_DETECTION,
               'event_id': event_id,
               'name': Detections.MOTION,
               'params': {'switch': True}}
    ctx.bot.event_manager.send_event(cam_id, payload)


@authorization_check
@camera_selection
@run_async
def cmd_line_detection_off(update, ctx, cam_id, cam_meta, event_id):
    """Disable camera's Line Crossing Detection."""
    payload = {'event': Events.CONFIGURE_DETECTION,
               'event_id': event_id,
               'name': Detections.LINE,
               'params': {'switch': False}}
    ctx.bot.event_manager.send_event(cam_id, payload)


@authorization_check
@camera_selection
@run_async
def cmd_line_detection_on(update, ctx, cam_id, cam_meta, event_id):
    """Enable camera's Line Crossing Detection."""
    payload = {'event': Events.CONFIGURE_DETECTION,
               'event_id': event_id,
               'name': Detections.LINE,
               'params': {'switch': True}}
    ctx.bot.event_manager.send_event(cam_id, payload)


@authorization_check
@camera_selection
@run_async
def cmd_stream_yt_on(update, ctx, cam_id, cam_meta, event_id):
    """Start YouTube stream."""
    payload = {'event': Events.STREAM,
               'event_id': event_id,
               'name': Streams.YOUTUBE,
               'params': {'switch': True}}
    ctx.bot.event_manager.send_event(cam_id, payload)


@authorization_check
@camera_selection
@run_async
def cmd_stream_yt_off(update, ctx, cam_id, cam_meta, event_id):
    """Stop YouTube stream."""
    payload = {'event': Events.STREAM,
               'event_id': event_id,
               'name': Streams.YOUTUBE,
               'params': {'switch': False}}
    ctx.bot.event_manager.send_event(cam_id, payload)


@authorization_check
@camera_selection
@run_async
def cmd_stream_icecast_on(update, ctx, cam_id, cam_meta, event_id):
    """Start Icecast stream."""
    payload = {'event': Events.STREAM,
               'event_id': event_id,
               'name': Streams.ICECAST,
               'params': {'switch': True}}
    ctx.bot.event_manager.send_event(cam_id, payload)


@authorization_check
@camera_selection
@run_async
def cmd_stream_icecast_off(update, ctx, cam_id, cam_meta, event_id):
    """Stop Icecast stream."""
    payload = {'event': Events.STREAM,
               'event_id': event_id,
               'name': Streams.ICECAST,
               'params': {'switch': False}}
    ctx.bot.event_manager.send_event(cam_id, payload)


@authorization_check
@camera_selection
@run_async
def cmd_alert_on(update, ctx, cam_id, cam_meta, event_id):
    """Enable camera's Alert Mode."""
    log.info('Enabling camera\'s alert mode requested')
    log.debug(get_user_info(update))
    payload = {'event': Events.CONFIGURE_ALARM,
               'event_id': event_id,
               'name': Alarms.ALARM,
               'params': {'switch': True}}
    ctx.bot.event_manager.send_event(cam_id, payload)


@authorization_check
@camera_selection
@run_async
def cmd_alert_off(update, ctx, cam_id, cam_meta, event_id):
    """Disable camera's Alert Mode."""
    log.info('Disabling camera\'s alert mode requested')
    log.debug(get_user_info(update))
    payload = {'event': Events.CONFIGURE_ALARM,
               'event_id': event_id,
               'name': Alarms.ALARM,
               'params': {'switch': False}}
    ctx.bot.event_manager.send_event(cam_id, payload)


@authorization_check
@run_async
def cmd_help(update, ctx, append=False, requested=True, cam_id=None):
    """Send help message to telegram chat."""
    if requested:
        log.info('Help message has been requested')
        log.debug(get_user_info(update))
        update.message.reply_text(
            'Use /list command to list available cameras and commands\n'
            'Use /stop command to fully stop the bot')
    elif append:
        presentation = build_commands_presentation(ctx.bot, cam_id)
        update.message.reply_html(
            f'<b>Available commands</b>\n\n{presentation}\n\n/list cameras')

    log.info('Help message has been sent')
