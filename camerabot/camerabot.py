import logging
from datetime import datetime
from functools import wraps
from threading import Thread

from telegram import Bot
from telegram.utils.request import Request

from camerabot.error import UserAuthError


def authorization_check(f):
    """Decorator which checks that user is authorized to interact with bot."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        self, update = args

        try:
            if update.message.chat.id not in self.user_id_list:
                raise UserAuthError

            return f(*args, **kwargs)

        except UserAuthError:
            self.log.error('User authorization error')
            self.log.error(self._get_user_info(update))
            self._print_access_error(update)

    return wrapper


def camera_selection(f):
    """Decorator which checks which camera instance to use."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        self, update = args
        cam_id = update.message.text.split('_', 1)[1]
        cam = self.cam_instances[cam_id]['instance']
        args = args + (cam, cam_id)

        return f(*args, **kwargs)

    return wrapper


class CameraBot(Bot):
    """CameraBot class where main bot things are done."""

    def __init__(self, token, user_id_list, cam_instances, stop):
        super(CameraBot, self).__init__(token, request=(Request(con_pool_size=10)))
        self.log = logging.getLogger(self.__class__.__name__)
        self.cam_instances = cam_instances
        self.user_id_list = user_id_list
        self.stop = stop

        self.log.debug('Initializing {0} bot'.format(self.first_name))

    def send_startup_message(self):
        """Send welcome message after bot launch."""
        self.log.info('Sending welcome message')

        for user_id in self.user_id_list:
            self.send_message(user_id, '{0} bot started, see /help for available commands'.format(self.first_name))

    @authorization_check
    @camera_selection
    def cmd_getpic(self, update, cam, cam_id):
        """Gets and sends resized snapshot from the camera."""
        self.log.info('Resized snapshot from {0} requested'.format(cam.description))
        self.log.debug(self._get_user_info(update))

        photo, snapshot_timestamp = cam.take_snapshot(update, resize=True)

        if not photo:
            return

        caption = 'Your pic taken on {0:%a %b %-d %H:%M:%S %Y} (pic #{1})'.format(
            datetime.fromtimestamp(snapshot_timestamp), cam.snapshots_taken)

        self.log.info('Sending resized snapshot')
        update.message.reply_text('Sending your pic from {0}...'.format(cam.description))
        update.message.reply_photo(photo=photo, caption=caption)

        self.log.info('Resized snapshot sent')
        self.print_helper(update, cam_id)

    @authorization_check
    @camera_selection
    def cmd_getfullpic(self, update, cam, cam_id):
        """Gets and sends full snapshot from the camera."""
        self.log.info('Full snapshot requested')
        self.log.debug(self._get_user_info(update))

        photo, snapshot_timestamp = cam.take_snapshot(update)

        if not photo:
            return

        full_snapshot_name = 'full_snapshot_{:%a_%b_%-d_%H.%M.%S_%Y}.jpg'.format(
            datetime.fromtimestamp(snapshot_timestamp))
        caption = 'Your full pic taken on {0:%a %b %-d %H:%M:%S %Y} (pic #{1})'.format(
            datetime.fromtimestamp(snapshot_timestamp), cam.snapshots_taken)

        self.log.info('Sending full snapshot')
        update.message.reply_text('Sending your full pic from {0}...'.format(cam.description))
        update.message.reply_document(document=photo, filename=full_snapshot_name, caption=caption)

        self.log.info('Full snapshot {0} sent'.format(full_snapshot_name))
        self.print_helper(update, cam_id)

    @authorization_check
    def cmd_stop(self, update):
        """Terminates bot."""
        msg = 'Stopping {0} bot'.format(self.first_name)

        self.log.info(msg)
        self.log.debug(self._get_user_info(update))

        update.message.reply_text(msg)

        thread = Thread(target=self.stop)
        thread.start()

    @authorization_check
    def cmd_list_cams(self, update):
        """Lists user's cameras."""
        self.log.info('Camera list has been requested')

        msg = ['<b>You have {0} cameras:</b>'.format(len(self.cam_instances))]

        for cam_id, cam_data in self.cam_instances.items():
            msg.append('<b>Camera:</b> {0}\n<b>Description:</b> {1}\n<b>Commands:</b> {2}'.format(
                cam_id, cam_data['instance'].description,
                ', '.join('/{0}'.format(cmds) for cmds in cam_data['commands'])))

        update.message.reply_html('\n\n'.join(msg))

        self.log.info('Camera list has been sent')

    def cmd_help(self, update, append=False, requested=True, cam_id=None):
        """Sends help message to telegram chat."""
        if requested:
            self.log.info('Help message has been requested')
            self.log.debug(self._get_user_info(update))
            update.message.reply_text('Use /list command to list available cameras and commands')
        elif append:
            update.message.reply_text('{0} to get pic or /list available cameras'.format(
                ', '.join('/{0}'.format(x) for x in self.cam_instances[cam_id]['commands'])))

        self.log.info('Help message has been sent')

    def error_handler(self, update, error):
        """Handles known telegram bot api errors."""
        self.log.error('Got error: {0}'.format(error))

    def print_helper(self, update, cam_id):
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
            update.message.chat.last_name
        )
