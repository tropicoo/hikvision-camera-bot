"""Camera Bot Module."""

import logging
import re
from datetime import datetime
from functools import wraps
from pathlib import PurePath
from threading import Thread

from telegram import Bot
from telegram.ext import run_async
from telegram.utils.request import Request

from hikcamerabot.config import get_main_config
from hikcamerabot.constants import (SEND_TIMEOUT, SWITCH_MAP, DETECTIONS,
                                    STREAMS, ALARMS, CMD_CAM_ID_REGEX)
from hikcamerabot.exceptions import UserAuthError
from hikcamerabot.service import ServiceStreamerThread, ServiceAlarmPusherThread
from hikcamerabot.utils import make_html_bold


def authorization_check(func):
    """Decorator which checks that user is authorized to interact with bot."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        bot, update, context = args
        try:
            if update.message.chat.id not in bot.user_ids:
                raise UserAuthError
            return func(*args, **kwargs)
        except UserAuthError:
            bot._log.error('User authorization error')
            bot._log.error(bot._get_user_info(update))
            bot._print_access_error(update)
    return wrapper


def camera_selection(func):
    """Decorator which checks which camera instance to use."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        cambot, update, context = args

        cam_id = re.split(CMD_CAM_ID_REGEX, update.message.text)[-1]
        cam = cambot._pool.get_instance(cam_id)
        return func(*args, cam=cam, cam_id=cam_id, **kwargs)
    return wrapper


class CameraBot(Bot):
    """CameraBot class where main bot things are done."""

    def __init__(self, stop_polling):
        conf = get_main_config()
        super(CameraBot, self).__init__(conf.telegram.token,
                                        request=(Request(con_pool_size=10)))
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.info('Initializing %s bot', self.first_name)
        self._pool = None
        self._stop_polling = stop_polling
        self.user_ids = conf.telegram.allowed_user_ids
        self._service_threads = {
            ServiceStreamerThread.type: ServiceStreamerThread,
            ServiceAlarmPusherThread.type: ServiceAlarmPusherThread}

    def _start_thread(self, thread, cam_id, cam, service=None, service_name=None,
                      update=None):
        thread(self, cam_id, cam, update, self._log, service, service_name).start()

    def add_camera_pool(self, pool):
        self._pool = pool

    def start_enabled_services(self):
        """Start services enabled in conf."""
        for cam_id, cam_data in self._pool.get_all().items():
            cam = cam_data['instance']
            cam.service_controller.start_services(enabled_in_conf=True)

            for svc in cam.service_controller.get_services():
                self._start_thread(thread=self._service_threads.get(svc.type),
                                   cam_id=cam_id,
                                   cam=cam,
                                   service=svc)

    def _stop_running_services(self):
        """Stop any running services."""
        for cam_id, cam_data in self._pool.get_all().items():
            cam_data['instance'].service_controller.stop_services()

    def send_startup_message(self):
        """Send welcome message after bot launch."""
        self._log.info('Sending welcome message')
        self.send_message_all('{0} bot started, see /help for '
                              'available commands'.format(self.first_name))

    def send_message_all(self, msg):
        """Send message to all defined user IDs in config.json."""
        for user_id in self.user_ids:
            self.send_message(user_id, msg)

    def reply_cam_photo(self, photo, update=None, caption=None, reply_text=None,
                        fullpic_name=None, fullpic=False, reply_html=None,
                        from_watchdog=False):
        """Send received photo."""
        if from_watchdog:
            for uid in self.user_ids:
                self.send_document(chat_id=uid,
                                   document=photo,
                                   caption=caption,
                                   filename=PurePath(photo.name).name,
                                   timeout=SEND_TIMEOUT)
        else:
            if reply_text:
                update.message.reply_text(reply_text)
            elif reply_html:
                update.message.reply_html(reply_html)
            if fullpic:
                update.message.reply_document(document=photo,
                                              filename=fullpic_name,
                                              caption=caption)
            else:
                update.message.reply_photo(photo=photo, caption=caption)

    @authorization_check
    @camera_selection
    @run_async
    def cmds(self, update, context, cam, cam_id):
        """Print camera commands."""
        self._print_helper(update, context, cam_id)

    @authorization_check
    @camera_selection
    @run_async
    def cmd_getpic(self, update, context, cam, cam_id):
        """Get and send resized snapshot from the camera."""
        self._log.info('Resized cam snapshot from %s requested',
                       cam.description)
        self._log.debug(self._get_user_info(update))

        try:
            photo, snapshot_timestamp = cam.take_snapshot(resize=True)
        except Exception as err:
            update.message.reply_text(
                '{0}\nTry later or /list other cameras'.format(err))
            return

        caption = 'Snapshot taken on {0:%a %b %d %H:%M:%S %Y} ' \
                  '(snapshot #{1})'.format(
            datetime.fromtimestamp(snapshot_timestamp),
            cam.snapshots_taken)

        caption = '{0}\n/cmds_{1}, /list'.format(caption, cam_id)

        reply_html = 'Sending snapshot from {0}'.format(cam.description)
        self._log.info('Sending resized cam snapshot')
        self.reply_cam_photo(photo=photo, update=update, caption=caption,
                             reply_html=make_html_bold(reply_html))

        self._log.info('Resized snapshot sent')

    @authorization_check
    @camera_selection
    @run_async
    def cmd_getfullpic(self, update, context, cam, cam_id):
        """Get and send full snapshot from the camera."""
        self._log.info('Full cam snapshot requested')
        self._log.debug(self._get_user_info(update))

        try:
            photo, snapshot_timestamp = cam.take_snapshot(resize=False)
        except Exception as err:
            update.message.reply_text(
                '{0}\nTry later or /list other cameras'.format(err))
            return

        fullpic_name = 'Full_snapshot_{:%a_%b_%d_%H.%M.%S_%Y}.jpg'.format(
            datetime.fromtimestamp(snapshot_timestamp))
        caption = 'Full snapshot taken on {0:%a %b %d %H:%M:%S %Y} ' \
                  '(snapshot #{1})'.format(
            datetime.fromtimestamp(snapshot_timestamp), cam.snapshots_taken)
        caption = '{0}\n/cmds_{1}, /list'.format(caption, cam_id)
        reply_html = 'Sending full snapshot from {0}'.format(cam.description)
        self._log.info('Sending full snapshot')
        self.reply_cam_photo(photo=photo, update=update, caption=caption,
                             reply_html=make_html_bold(reply_html),
                             fullpic_name=fullpic_name,
                             fullpic=True)
        self._log.info('Full cam snapshot %s sent', fullpic_name)

    @authorization_check
    @run_async
    def cmd_stop(self, update):
        """Terminate bot."""
        msg = 'Stopping {0} bot'.format(self.first_name)
        self._log.info(msg)
        self._log.debug(self._get_user_info(update))
        update.message.reply_text(msg)
        self._stop_running_services()
        thread = Thread(target=self._stop_polling)
        thread.start()

    @authorization_check
    @run_async
    def cmd_list_cams(self, update, context):
        """List user's cameras."""
        self._log.info('Camera list has been requested')

        cam_count = self._pool.get_count()
        msg = [make_html_bold('You have {0} camera{1}'.format(
            cam_count, '' if cam_count == 1 else 's'))]

        for cam_id, cam_data in self._pool.get_all().items():
            presentation = self._build_commands_presentation(cam_id)
            msg.append(
                '<b>Camera:</b> {0}\n<b>Description:</b> '
                '{1}\n<b>Commands</b>\n{2}'.format(
                    cam_id, cam_data['instance'].description, presentation))

        update.message.reply_html('\n\n'.join(msg))

        self._log.info('Camera list has been sent')

    @authorization_check
    @camera_selection
    @run_async
    def cmd_motion_detection_off(self, update, context, cam, cam_id):
        """Disable camera's Motion Detection."""
        self._trigger_switch(enable=False,
                             _type=DETECTIONS.MOTION,
                             update=update,
                             context=context,
                             cam=cam,
                             cam_id=cam_id)

    @authorization_check
    @camera_selection
    @run_async
    def cmd_motion_detection_on(self, update, context, cam, cam_id):
        """Enable camera's Motion Detection."""
        self._trigger_switch(enable=True,
                             _type=DETECTIONS.MOTION,
                             update=update,
                             context=context,
                             cam=cam,
                             cam_id=cam_id)

    @authorization_check
    @camera_selection
    @run_async
    def cmd_line_detection_off(self, update, context, cam, cam_id):
        """Disable camera's Line Crossing Detection."""
        self._trigger_switch(enable=False,
                             _type=DETECTIONS.LINE,
                             update=update,
                             context=context,
                             cam=cam,
                             cam_id=cam_id)

    @authorization_check
    @camera_selection
    @run_async
    def cmd_line_detection_on(self, update, context, cam, cam_id):
        """Enable camera's Line Crossing Detection."""
        self._trigger_switch(enable=True,
                             _type=DETECTIONS.LINE,
                             update=update,
                             context=context,
                             cam=cam,
                             cam_id=cam_id)

    @authorization_check
    @camera_selection
    @run_async
    def cmd_stream_yt_on(self, update, context, cam, cam_id):
        """Start YouTube stream."""
        self._log.info('Starting YouTube stream')
        self._log.debug(self._get_user_info(update))
        try:
            cam.stream_yt.start()
            self._start_thread(
                thread=self._service_threads.get(STREAMS.SERVICE_TYPE),
                cam_id=cam_id,
                cam=cam,
                service_name=STREAMS.YOUTUBE,
                update=update)
            update.message.reply_html(
                make_html_bold('YouTube stream successfully enabled'))
        except Exception as err:
            update.message.reply_html(make_html_bold(err))

    @authorization_check
    @camera_selection
    @run_async
    def cmd_stream_yt_off(self, update, context, cam, cam_id):
        """Stop YouTube stream."""
        self._log.info('Stopping YouTube stream')
        self._log.debug(self._get_user_info(update))
        try:
            cam.stream_yt.stop()
            update.message.reply_html(
                make_html_bold('YouTube stream successfully disabled'))
        except Exception as err:
            update.message.reply_html(make_html_bold(err))

    @authorization_check
    @camera_selection
    @run_async
    def cmd_stream_icecast_on(self, update, context, cam, cam_id):
        """Start Icecast stream."""
        self._log.info('Starting Icecast stream')
        self._log.debug(self._get_user_info(update))
        try:
            cam.stream_icecast.start()
            self._start_thread(
                thread=self._service_threads.get(STREAMS.SERVICE_TYPE),
                cam_id=cam_id,
                cam=cam,
                service_name=STREAMS.ICECAST,
                update=update)
            update.message.reply_html(
                make_html_bold('Icecast stream successfully enabled'))
        except Exception as err:
            update.message.reply_html(make_html_bold(err))

    @authorization_check
    @camera_selection
    @run_async
    def cmd_stream_icecast_off(self, update, context, cam, cam_id):
        """Stop Icecast stream."""
        self._log.info('Stopping Icecast stream')
        self._log.debug(self._get_user_info(update))
        try:
            cam.stream_icecast.stop()
            update.message.reply_html(
                make_html_bold('Icecast stream successfully disabled'))
        except Exception as err:
            update.message.reply_html(make_html_bold(err))

    @authorization_check
    @camera_selection
    @run_async
    def cmd_alert_on(self, update, context, cam, cam_id):
        """Enable camera's Alert Mode."""
        self._log.info('Enabling camera\'s alert mode requested')
        self._log.debug(self._get_user_info(update))
        try:
            cam.alarm.start()
            self._start_thread(
                thread=self._service_threads.get(ALARMS.SERVICE_TYPE),
                cam_id=cam_id,
                cam=cam,
                service_name=ALARMS.ALARM,
                update=update)
            update.message.reply_html(
                make_html_bold('Alarm alert mode successfully enabled'))
        except Exception as err:
            update.message.reply_html(make_html_bold(err))

    @authorization_check
    @camera_selection
    @run_async
    def cmd_alert_off(self, update, context, cam, cam_id):
        """Disable camera's Alert Mode."""
        self._log.info('Disabling camera\'s alert mode requested')
        try:
            cam.alarm.stop()
            update.message.reply_html(
                make_html_bold('Alarm alert mode successfully disabled'))
        except Exception as err:
            update.message.reply_html(make_html_bold(err))

    @authorization_check
    @run_async
    def cmd_help(self, update, context, append=False, requested=True, cam_id=None):
        """Send help message to telegram chat."""
        if requested:
            self._log.info('Help message has been requested')
            self._log.debug(self._get_user_info(update))
            update.message.reply_text(
                'Use /list command to list available cameras and commands\n'
                'Use /stop command to fully stop the bot')
        elif append:
            presentation = self._build_commands_presentation(cam_id)
            update.message.reply_html(
                '<b>Available commands</b>\n\n{0}\n\n/list '
                'cameras'.format(presentation))

        self._log.info('Help message has been sent')

    def _build_commands_presentation(self, cam_id):
        groups = []
        for desc, cmds in self._pool.get_commands(cam_id).items():
            groups.append('{0}\n{1}'.format(desc, '\n'.join(['/' + c for c in cmds])))
        return '\n\n'.join(groups)

    @staticmethod
    def error_handler(update, context):
        """Handle known Telegram bot api errors."""
        context.bot._log.exception('Got error: %s', context.error)

    def _print_helper(self, update, context, cam_id):
        """Send help message to telegram chat after sending picture."""
        self.cmd_help(update, context, append=True, requested=False,
                      cam_id=cam_id)

    def _print_access_error(self, update):
        """Send authorization error to telegram chat."""
        update.message.reply_text('Not authorized')

    def _trigger_switch(self, enable, _type, update, context, cam, cam_id):
        name = SWITCH_MAP[_type]['name']
        self._log.info('%s camera\'s %s has been requested',
                       'Enabling' if enable else 'Disabling', name)
        self._log.debug(self._get_user_info(update))
        try:
            msg = cam.alarm.trigger_switch(enable=enable, _type=_type)
            msg = msg or '{0} successfully {1}'.format(
                name, 'enabled' if enable else 'disabled')
            update.message.reply_html(make_html_bold(msg))
            self._log.info(msg)
        except Exception as err:
            err_msg = 'Failed to {0} {1}: {2}'.format(
                'enable' if enable else 'disable', name, err)
            update.message.reply_text(err_msg)

    def _get_user_info(self, update):
        """Return user information who interacts with bot."""
        return 'Request from user_id: {0}, username: {1},' \
               'first_name: {2}, last_name: {3}'.format(
                                                update.message.chat.id,
                                                update.message.chat.username,
                                                update.message.chat.first_name,
                                                update.message.chat.last_name)
