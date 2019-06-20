"""Camera Bot Module."""

import logging
import os
import re
import time
from datetime import datetime
from functools import wraps
from threading import Thread

from telegram import Bot, ParseMode
from telegram.utils.request import Request

from camerabot.constants import (SEND_TIMEOUT, SWITCH_MAP, MOTION_DETECTION,
                                 LINE_DETECTION, DETECTION_REGEX)
from camerabot.exceptions import HomeCamError, UserAuthError, CameraBotError
from camerabot.utils import make_html_bold


def authorization_check(func):

    """Decorator which check that user is authorized to interact with bot."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        bot, update = args
        try:
            if update.message.chat.id not in bot._user_ids:
                raise UserAuthError
            return func(*args, **kwargs)
        except UserAuthError:
            bot._log.error('User authorization error')
            bot._log.error(bot._get_user_info(update))
            bot._print_access_error(update)

    return wrapper


def camera_selection(func):

    """Decorator which check which camera instance to use."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        cambot, update = args
        cam_id = re.split(r'^.*(?=cam_)', update.message.text)[-1]
        cam = cambot._cam_instances[cam_id]['instance']
        args = args + (cam, cam_id)
        return func(*args, **kwargs)

    return wrapper


class CameraBot(Bot):

    """CameraBot class where main bot things are done."""

    def __init__(self, token, user_ids, cam_instances, stop_polling):
        super(CameraBot, self).__init__(token,
                                        request=(Request(con_pool_size=10)))
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam_instances = cam_instances
        self._user_ids = user_ids
        self._stop_polling = stop_polling
        self._log.info('Initializing {0} bot'.format(self.first_name))
        self._start_enabled_services()

    def _start_enabled_services(self):
        """Start services enabled in conf."""

        # TODO: implement some better approach with starting/stopping services
        for cam_id, cam_instance in self._cam_instances.items():
            cam = cam_instance['instance']
            if cam.alarm.is_enabled():
                Thread(target=self._alert_pusher, args=(cam_id, cam)).start()
            if cam.stream_yt.is_enabled():
                cam.stream_yt.start()
                Thread(target=self._yt_streamer, args=(cam_id, cam)).start()

    def _stop_running_services(self):
        """Stop any running services."""
        for cam_id, cam_instance in self._cam_instances.items():
            cam = cam_instance['instance']
            try:
                cam.alarm.disable()
            except HomeCamError as err:
                self._log.warning(str(err))
            try:
                cam.stream_yt.stop()
            except HomeCamError as err:
                self._log.warning(str(err))

    def send_startup_message(self):
        """Send welcome message after bot launch."""
        self._log.info('Sending welcome message')

        msg = '{0} bot started, see /help for ' \
              'available commands'.format(self.first_name)
        self._send_message_all(msg)

    def _send_message_all(self, msg):
        for user_id in self._user_ids:
            self.send_message(user_id, msg)

    def reply_cam_photo(self, photo, update=None, caption=None, reply_text=None,
                        fullpic_name=None, fullpic=False, reply_html=None,
                        from_watchdog=False):
        """Send received photo."""
        if from_watchdog:
            for uid in self._user_ids:
                filename = os.path.basename(photo.name)
                self.send_document(chat_id=uid, document=photo,
                                   caption=caption, filename=filename,
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
    def cmds(self, update, cam, cam_id):
        """Print camera commands."""
        self._print_helper(update, cam_id)

    @authorization_check
    @camera_selection
    def cmd_getpic(self, update, cam, cam_id):
        """Get and send resized snapshot from the camera."""
        self._log.info('Resized cam snapshot from {0} requested'.format(
            cam.description))
        self._log.debug(self._get_user_info(update))

        try:
            photo, snapshot_timestamp = cam.take_snapshot(resize=True)
        except Exception as err:
            update.message.reply_text(
                '{0}\nTry later or /list other cameras'.format(str(err)))
            return

        caption = 'Snapshot taken on {0:%a %b %-d %H:%M:%S %Y} ' \
                  '(snapshot #{1})'.format(
            datetime.fromtimestamp(snapshot_timestamp), cam.snapshots_taken)
        caption = '{0}\n/cmds_{1}, /list'.format(caption, cam_id)

        reply_html = 'Sending snapshot from {0}'.format(cam.description)
        self._log.info('Sending resized cam snapshot')
        self.reply_cam_photo(photo=photo, update=update, caption=caption,
                             reply_html=make_html_bold(reply_html))

        self._log.info('Resized snapshot sent')

    @authorization_check
    @camera_selection
    def cmd_getfullpic(self, update, cam, cam_id):
        """Get and send full snapshot from the camera."""
        self._log.info('Full cam snapshot requested')
        self._log.debug(self._get_user_info(update))

        try:
            photo, snapshot_timestamp = cam.take_snapshot(resize=False)
        except Exception as err:
            update.message.reply_text(
                '{0}\nTry later or /list other cameras'.format(str(err)))
            return

        fullpic_name = 'Full_snapshot_{:%a_%b_%-d_%H.%M.%S_%Y}.jpg'.format(
            datetime.fromtimestamp(snapshot_timestamp))
        caption = 'Full snapshot taken on {0:%a %b %-d %H:%M:%S %Y} ' \
                  '(snapshot #{1})'.format(
            datetime.fromtimestamp(snapshot_timestamp), cam.snapshots_taken)
        caption = '{0}\n/cmds_{1}, /list'.format(caption, cam_id)
        reply_html = 'Sending full snapshot from {0}'.format(cam.description)
        self._log.info('Sending full snapshot')
        self.reply_cam_photo(photo=photo, update=update, caption=caption,
                             reply_html=make_html_bold(reply_html),
                             fullpic_name=fullpic_name,
                             fullpic=True)
        self._log.info('Full cam snapshot {0} sent'.format(fullpic_name))

    @authorization_check
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
    def cmd_list_cams(self, update):
        """List user's cameras."""
        self._log.info('Camera list has been requested')

        cam_count = len(self._cam_instances)
        msg = [make_html_bold('You have {0} camera{1}'.format(
            cam_count, '' if cam_count == 1 else 's'))]

        for cam_id, cam_data in self._cam_instances.items():
            msg.append(
                '<b>Camera:</b> {0}\n<b>Description:</b> '
                '{1}\n<b>Commands</b>\n{2}'.format(
                    cam_id, cam_data['instance'].description,
                    '\n'.join('/{0}'.format(cmds) for cmds in cam_data['commands'])))

        update.message.reply_html('\n\n'.join(msg))

        self._log.info('Camera list has been sent')

    @authorization_check
    @camera_selection
    def cmd_motion_detection_off(self, *args):
        """Disable camera's Motion Detection."""
        self._trigger_switch(enable=False, _type=MOTION_DETECTION, args=args)

    @authorization_check
    @camera_selection
    def cmd_motion_detection_on(self, *args):
        """Enable camera's Motion Detection."""
        self._trigger_switch(enable=True, _type=MOTION_DETECTION, args=args)
        
    @authorization_check
    @camera_selection
    def cmd_line_detection_off(self, *args):
        """Disable camera's Line Crossing Detection."""
        self._trigger_switch(enable=False, _type=LINE_DETECTION, args=args)

    @authorization_check
    @camera_selection
    def cmd_line_detection_on(self, *args):
        """Enable camera's Line Crossing Detection."""
        self._trigger_switch(enable=True, _type=LINE_DETECTION, args=args)

    @authorization_check
    @camera_selection
    def cmd_stream_yt_on(self, update, cam, cam_id):
        """Start YouTube stream."""
        self._log.info('Starting YouTube stream.')
        self._log.debug(self._get_user_info(update))
        try:
            cam.stream_yt.start()
            thread = Thread(target=self._yt_streamer, args=(cam_id, cam))
            thread.start()
            update.message.reply_html(
                make_html_bold('YouTube stream successfully enabled'))
        except Exception as err:
            update.message.reply_html(make_html_bold(str(err)))

    @authorization_check
    @camera_selection
    def cmd_stream_yt_off(self, update, cam, cam_id):
        """Start YouTube stream."""
        self._log.info('Starting YouTube stream.')
        self._log.debug(self._get_user_info(update))
        try:
            cam.stream_yt.stop()
            update.message.reply_html(
                make_html_bold('YouTube stream successfully disabled'))
        except Exception as err:
            update.message.reply_html(make_html_bold(str(err)))

    @authorization_check
    @camera_selection
    def cmd_alert_on(self, update, cam, cam_id):
        """Enable camera's Alert Mode."""
        self._log.info('Enabling camera\'s alert mode requested')
        self._log.debug(self._get_user_info(update))
        try:
            cam.alarm.enable()
            thread = Thread(target=self._alert_pusher,
                            args=(cam_id, cam))
            thread.start()
            update.message.reply_html(
                make_html_bold('Motion Detection Alert successfully enabled'))
        except Exception as err:
            update.message.reply_html(make_html_bold(str(err)))

    @authorization_check
    @camera_selection
    def cmd_alert_off(self, update, cam, cam_id):
        """Disable camera's Alert Mode."""
        self._log.info('Disabling camera\'s alert mode requested')
        try:
            cam.alarm.disable()
            update.message.reply_html(
                make_html_bold('Motion Detection Alert successfully disabled'))
        except Exception as err:
            update.message.reply_html(make_html_bold(str(err)))

    @authorization_check
    def cmd_help(self, update, append=False, requested=True, cam_id=None):
        """Send help message to telegram chat."""
        if requested:
            self._log.info('Help message has been requested')
            self._log.debug(self._get_user_info(update))
            update.message.reply_text(
                'Use /list command to list available cameras and commands\n'
                'Use /stop command to fully stop the bot')
        elif append:
            update.message.reply_html(
                '<b>Available commands</b>\n\n{0}\n\n/list '
                'cameras'.format('\n'.join('/{0}'.format(x) for x in
                                 self._cam_instances[cam_id]['commands'])))

        self._log.info('Help message has been sent')

    def error_handler(self, update, error):
        """Handle known Telegram bot api errors."""
        self._log.exception('Got error: {0}'.format(error))

    def _print_helper(self, update, cam_id):
        """Send help message to telegram chat after sending picture."""
        self.cmd_help(update, append=True, requested=False, cam_id=cam_id)

    def _print_access_error(self, update):
        """Send authorization error to telegram chat."""
        update.message.reply_text('Not authorized')

    def _trigger_switch(self, enable, _type, args):
        name = SWITCH_MAP[_type]['name']
        update, cam, cam_id = args
        self._log.info('{0} camera\'s {1} has been requested'.format(
            'Enabling' if enable else 'Disabling', name))
        self._log.debug(self._get_user_info(update))
        try:
            msg = cam.trigger_switch(enable=enable, _type=_type)
            msg = msg or '{0} successfully {1}'.format(
                name, 'enabled' if enable else 'disabled')
            update.message.reply_html(make_html_bold(msg))
            self._log.info(msg)
        except Exception as err:
            err_msg = 'Failed to {0} {1}: {2}'.format(
                'enable' if enable else 'disable', name, str(err))
            update.message.reply_text(err_msg)

    def _yt_streamer(self, cam_id, cam):
        self._log.debug('Started YouTube streamer thread for '
                        'camera: "{0}"'.format(cam.description))
        while cam.stream_yt.is_enabled():
            while not cam.stream_yt.need_restart():
                if not cam.stream_yt.is_started():
                    self._log.info('Exiting YouTube stream '
                                   'thread for {0}'.format(cam.description))
                    break
                time.sleep(1)
            else:
                self._log.debug('Restarting YouTube stream')
                cam.stream_yt.restart()

    def _alert_pusher(self, cam_id, cam):
        while cam.alarm.is_enabled():
            self._log.debug('Started alert pusher thread for '
                            'camera: "{0}"'.format(cam.description))
            wait_before = 0
            stream = cam.get_alert_stream()
            for chunk in stream.iter_lines(chunk_size=1024):
                if not cam.alarm.is_enabled():
                    self._log.info('Exiting alert pusher '
                                   'thread for {0}'.format(cam.description))
                    break

                if wait_before > int(time.time()):
                    continue
                if chunk:
                    try:
                        detection_key = self.chunk_belongs_to_detection(chunk)
                    except CameraBotError as err:
                        self._send_message_all(str(err))
                        continue
                    if detection_key:
                        photo, ts = cam.take_snapshot(resize=False if
                            cam.conf.alert[detection_key].fullpic else True)
                        cam.alarm.alert_count += 1
                        wait_before = int(time.time()) + cam.alarm.alert_delay
                        self._send_alert(cam, photo, ts, detection_key)

    def chunk_belongs_to_detection(self, chunk):
        match = re.match(DETECTION_REGEX, chunk.decode())
        if match:
            event_name = match.group(2)
            for key, inner_map in SWITCH_MAP.items():
                if inner_map['event_name'] == event_name:
                    return key
            else:
                raise CameraBotError('Detected event {0} but don\'t know what '
                                     'to do'.format(event_name))
        return None

    def _send_alert(self, cam, photo, ts, detection_key):
        caption = 'Alert snapshot taken on {0:%a %b %-d %H:%M:%S %Y} (alert ' \
                  '#{1})\n/list cameras'.format(datetime.fromtimestamp(ts),
                                                cam.alarm.alert_count)
        reply_html = '<b>{0} Alert</b>\nSending snapshot ' \
                     'from {1}'.format(cam.description,
                                       SWITCH_MAP[detection_key]['name'])

        for uid in self._user_ids:
            self.send_message(chat_id=uid, text=reply_html,
                              parse_mode=ParseMode.HTML)
            if cam.conf.alert[detection_key].fullpic:
                name = 'Full_alert_snapshot_{:%a_%b_%-d_%H.%M.%S_%Y}.jpg'.format(
                    datetime.fromtimestamp(ts))
                self.send_document(chat_id=uid, document=photo,
                                   caption=caption,
                                   filename=name,
                                   timeout=SEND_TIMEOUT)
            else:
                self.send_photo(chat_id=uid, photo=photo,
                                caption=caption,
                                timeout=SEND_TIMEOUT)

    def _get_user_info(self, update):
        """Return user information who interacts with bot."""
        return 'Request from user_id: {0}, username: {1},' \
               'first_name: {2}, last_name: {3}'.format(
                                                update.message.chat.id,
                                                update.message.chat.username,
                                                update.message.chat.first_name,
                                                update.message.chat.last_name)
