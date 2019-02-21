"""Camerabot Module"""

import logging
import os
import re
import time
from datetime import datetime
from functools import wraps
from threading import Thread

from telegram import Bot, ParseMode
from telegram.utils.request import Request

from camerabot.constants import SEND_TIMEOUT
from camerabot.errors import (HomeCamError, UserAuthError,
                              HomeCamAlertAlreadyOffError,
                              HomeCamAlertAlreadyOnError)


def authorization_check(func):
    """Decorator which checks that user is authorized to interact with bot."""

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
    """Decorator which checks which camera instance to use."""

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
        self._initialize_alerter()

    def _initialize_alerter(self):
        for cam_id, cam_instance in self._cam_instances.items():
            cam = cam_instance['instance']
            if cam.alert_enabled:
                thread = Thread(target=self._alert_pusher,
                                args=(cam_id, cam))
                thread.start()

    def send_startup_message(self):
        """Send welcome message after bot launch."""
        self._log.info('Sending welcome message')

        for user_id in self._user_ids:
            self.send_message(user_id,
                              '{0} bot started, see /help for available commands'.format(
                                  self.first_name))

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
    def cmd_getpic(self, update, cam, cam_id):
        """Gets and sends resized snapshot from the camera."""
        self._log.info(
            'Resized cam snapshot from {0} requested'.format(cam.description))
        self._log.debug(self._get_user_info(update))

        try:
            photo, snapshot_timestamp = cam.take_snapshot(resize=True)
        except HomeCamError as err:
            update.message.reply_text(
                '{0}\nTry later or /list other cameras'.format(str(err)))
            return

        caption = 'Pic taken on {0:%a %b %-d %H:%M:%S %Y} (pic #{1})'.format(
            datetime.fromtimestamp(snapshot_timestamp), cam.snapshots_taken)
        reply_html = '<b>Sending pic from {0}</b>'.format(cam.description)
        self._log.info('Sending resized cam snapshot')
        self.reply_cam_photo(photo=photo, update=update, caption=caption,
                             reply_html=reply_html)

        self._log.info('Resized snapshot sent')
        self._print_helper(update, cam_id)

    @authorization_check
    @camera_selection
    def cmd_getfullpic(self, update, cam, cam_id):
        """Gets and sends full snapshot from the camera."""
        self._log.info('Full cam snapshot requested')
        self._log.debug(self._get_user_info(update))

        try:
            photo, snapshot_timestamp = cam.take_snapshot(resize=False)
        except HomeCamError as err:
            update.message.reply_text(
                '{0}\nTry later or /list other cameras'.format(str(err)))
            return

        fullpic_name = 'Full_snapshot_{:%a_%b_%-d_%H.%M.%S_%Y}.jpg'.format(
            datetime.fromtimestamp(snapshot_timestamp))
        caption = 'Full pic taken on {0:%a %b %-d %H:%M:%S %Y} (pic #{1})'.format(
            datetime.fromtimestamp(snapshot_timestamp), cam.snapshots_taken)
        reply_html = '<b>Sending full pic from {0}</b>'.format(cam.description)
        self._log.info('Sending full snapshot')
        self.reply_cam_photo(photo=photo, update=update, caption=caption,
                             reply_html=reply_html,
                             fullpic_name=fullpic_name,
                             fullpic=True)
        self._log.info('Full cam snapshot {0} sent'.format(fullpic_name))
        self._print_helper(update, cam_id)

    @authorization_check
    def cmd_stop(self, update):
        """Terminates bot."""
        msg = 'Stopping {0} bot'.format(self.first_name)
        self._log.info(msg)
        self._log.debug(self._get_user_info(update))
        update.message.reply_text(msg)
        thread = Thread(target=self._stop_polling)
        thread.start()

    @authorization_check
    def cmd_list_cams(self, update):
        """Lists user's cameras."""
        self._log.info('Camera list has been requested')

        cam_count = len(self._cam_instances)
        msg = ['<b>You have {0} camera{1}</b>'.format(cam_count,
                                                '' if cam_count == 1 else 's')]

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
    def cmd_motion_detection_off(self, update, cam, cam_id):
        """Disable camera's Motion Detection."""
        self._log.info('Disabling camera\'s Motion Detection has been '
                       'requested')
        self._log.debug(self._get_user_info(update))
        try:
            msg = cam.motion_detection_switch(enable=False)
            msg = msg or '<b>Motion Detection successfully disabled</b>'
            update.message.reply_html(msg)
            self._log.info(msg)
        except HomeCamError as err:
            update.message.reply_text(str(err))

    @authorization_check
    @camera_selection
    def cmd_motion_detection_on(self, update, cam, cam_id):
        """Enable camera's Motion Detection."""
        self._log.info('Enabling camera\'s Motion Detection has been '
                       'requested')
        self._log.debug(self._get_user_info(update))
        try:
            msg = cam.motion_detection_switch(enable=True)
            msg = msg or '<b>Motion Detection successfully enabled</b>'
            update.message.reply_html(msg)
            self._log.info(msg)
        except HomeCamError as err:
            update.message.reply_text(str(err))

    @authorization_check
    @camera_selection
    def cmd_alert_on(self, update, cam, cam_id):
        """Enable camera's Alert Mode."""
        self._log.info('Enabling camera\'s alert mode requested')
        self._log.debug(self._get_user_info(update))
        try:
            cam.alert(enable=True)
            thread = Thread(target=self._alert_pusher,
                            args=(cam_id, cam))
            thread.start()
            update.message.reply_html('<b>Motion Detection Alert successfully '
                                      'enabled</b>')
        except (HomeCamAlertAlreadyOnError, HomeCamError) as err:
            update.message.reply_html(str(err))

    @authorization_check
    @camera_selection
    def cmd_alert_off(self, update, cam, cam_id):
        """Disable camera's Alert Mode."""
        self._log.info('Disabling camera\'s alert mode requested')
        try:
            cam.alert(enable=False)
            update.message.reply_html('<b>Motion Detection Alert successfully '
                                      'disabled</b>')
        except (HomeCamAlertAlreadyOffError, HomeCamError) as err:
            update.message.reply_html(str(err))

    def cmd_help(self, update, append=False, requested=True, cam_id=None):
        """Sends help message to telegram chat."""
        if requested:
            self._log.info('Help message has been requested')
            self._log.debug(self._get_user_info(update))
            update.message.reply_text(
                'Use /list command to list available cameras and commands')
        elif append:
            update.message.reply_html(
                '<b>Available commands</b>\n\n{0}\n\n/list '
                'cameras'.format('\n'.join('/{0}'.format(x) for x in
                                 self._cam_instances[cam_id]['commands'])))

        self._log.info('Help message has been sent')

    def error_handler(self, update, error):
        """Handles known telegram bot api errors."""
        self._log.exception('Got error: {0}'.format(error))

    def _print_helper(self, update, cam_id):
        """Sends help message to telegram chat after sending picture."""
        self.cmd_help(update, append=True, requested=False, cam_id=cam_id)

    def _print_access_error(self, update):
        """Sends authorization error to telegram chat."""
        update.message.reply_text('Not authorized')

    def _alert_pusher(self, cam_id, cam):
        while cam.alert_on.is_set():
            self._log.debug('Started thread for '
                            'camera: "{0}"'.format(cam.description))
            wait_before = 0
            stream = cam.get_alert_stream()
            for chunk in stream.iter_lines(chunk_size=1024):
                if not cam.alert_on.is_set():
                    break

                if wait_before > int(time.time()):
                    continue

                if chunk and chunk.startswith(b'<eventType>VMD<'):
                    photo, ts = cam.take_snapshot(resize=False if
                                                  cam.alert_fullpic else True)
                    cam.alert_count += 1
                    wait_before = int(time.time()) + cam.alert_delay
                    self._send_alert(cam, photo, ts)

    def _send_alert(self, cam, photo, ts):
        caption = 'Alert Pic taken on {0:%a %b %-d %H:%M:%S %Y} (alert ' \
                  '#{1})\n/list cameras'.format(datetime.fromtimestamp(ts),
                                                cam.alert_count)
        reply_html = '<b>Motion Detection Alert</b>\nSending pic ' \
                     'from {0}'.format(cam.description)

        for uid in self._user_ids:
            self.send_message(chat_id=uid, text=reply_html,
                              parse_mode=ParseMode.HTML)
            if cam.alert_fullpic:
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
        """Returns user information who interacts with bot."""
        return 'Request from user_id: {0}, username: {1},' \
               'first_name: {2}, last_name: {3}'.format(
                                                update.message.chat.id,
                                                update.message.chat.username,
                                                update.message.chat.first_name,
                                                update.message.chat.last_name)
