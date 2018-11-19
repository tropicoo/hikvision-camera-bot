import logging
from datetime import datetime
from functools import wraps
from threading import Thread

from telegram import Bot
from telegram.utils.request import Request

from camerabot.error import UserAuthError


def authorization_check(func):
    """Decorator which checks that user is authorized to interact with bot."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        bot, update = args

        try:
            if update.message.chat.id not in bot._user_id_list:
                raise UserAuthError

            return func(*args, **kwargs)

        except UserAuthError:
            bot._log.error('User authorization error')
            bot._log.error(bot._get_user_info(update))
            bot._print_access_error(update)

    return wrapper


def camera_selection(f):
    """Decorator which checks which camera instance to use."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        self, update = args
        cam_id = update.message.text.split('_', 1)[1]
        cam = self._cam_instances[cam_id]['instance']
        args = args + (cam, cam_id)

        return f(*args, **kwargs)

    return wrapper


class CameraBot(Bot):
    """CameraBot class where main bot things are done."""

    def __init__(self, token, user_id_list, cam_instances, stop_polling):
        super(CameraBot, self).__init__(token, request=(Request(con_pool_size=10)))
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam_instances = cam_instances
        self._user_id_list = user_id_list
        self._stop_polling = stop_polling

        self._log.debug('Initializing {0} bot'.format(self.first_name))

    def send_startup_message(self):
        """Send welcome message after bot launch."""
        self._log.info('Sending welcome message')

        for user_id in self._user_id_list:
            self.send_message(user_id, '{0} bot started, see /help for available commands'.format(self.first_name))

    @authorization_check
    @camera_selection
    def cmd_getpic(self, update, cam, cam_id):
        """Gets and sends resized snapshot from the camera."""
        self._log.info('Resized snapshot from {0} requested'.format(cam.description))
        self._log.debug(self._get_user_info(update))

        photo, snapshot_timestamp = cam.take_snapshot(update, resize=True)

        if not photo:
            return

        caption = 'Pic taken on {0:%a %b %-d %H:%M:%S %Y} (pic #{1})'.format(
            datetime.fromtimestamp(snapshot_timestamp), cam.snapshots_taken)

        self._log.info('Sending resized snapshot')
        update.message.reply_text('Sending pic from {0}...'.format(cam.description))
        update.message.reply_photo(photo=photo, caption=caption)

        self._log.info('Resized snapshot sent')
        self._print_helper(update, cam_id)

    @authorization_check
    @camera_selection
    def cmd_getfullpic(self, update, cam, cam_id):
        """Gets and sends full snapshot from the camera."""
        self._log.info('Full snapshot requested')
        self._log.debug(self._get_user_info(update))

        photo, snapshot_timestamp = cam.take_snapshot(update)

        if not photo:
            return

        full_snapshot_name = 'Full_snapshot_{:%a_%b_%-d_%H.%M.%S_%Y}.jpg'.format(
            datetime.fromtimestamp(snapshot_timestamp))
        caption = 'Full pic taken on {0:%a %b %-d %H:%M:%S %Y} (pic #{1})'.format(
            datetime.fromtimestamp(snapshot_timestamp), cam.snapshots_taken)

        self._log.info('Sending full snapshot')
        update.message.reply_text('Sending full pic from {0}...'.format(cam.description))
        update.message.reply_document(document=photo, filename=full_snapshot_name, caption=caption)

        self._log.info('Full snapshot {0} sent'.format(full_snapshot_name))
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

        msg = ['<b>You have {0} cameras:</b>'.format(len(self._cam_instances))]

        for cam_id, cam_data in self._cam_instances.items():
            msg.append('<b>Camera:</b> {0}\n<b>Description:</b> {1}\n<b>Commands:</b> {2}'.format(
                cam_id, cam_data['instance'].description,
                ', '.join('/{0}'.format(cmds) for cmds in cam_data['commands'])))

        update.message.reply_html('\n\n'.join(msg))

        self._log.info('Camera list has been sent')

    def cmd_help(self, update, append=False, requested=True, cam_id=None):
        """Sends help message to telegram chat."""
        if requested:
            self._log.info('Help message has been requested')
            self._log.debug(self._get_user_info(update))
            update.message.reply_text('Use /list command to list available cameras and commands')
        elif append:
            update.message.reply_text('{0} to get pic or /list available cameras'.format(
                ', '.join('/{0}'.format(x) for x in self._cam_instances[cam_id]['commands'])))

        self._log.info('Help message has been sent')

    def error_handler(self, update, error):
        """Handles known telegram bot api errors."""
        self._log.error('Got error: {0}'.format(error))

    def _print_helper(self, update, cam_id):
        """Sends help message to telegram chat after sending picture."""
        self.cmd_help(update, append=True, requested=False, cam_id=cam_id)

    def _print_access_error(self, update):
        """Sends authorization error to telegram chat."""
        update.message.reply_text('Not authorized')

    @staticmethod
    def _get_user_info(update):
        """Returns user information who interacts with bot."""
        return 'Request from user_id: {0}, username: {1}, first_name: {2}, last_name: {3}'.format(
            update.message.chat.id,
            update.message.chat.username,
            update.message.chat.first_name,
            update.message.chat.last_name)
