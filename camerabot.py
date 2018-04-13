#!/usr/bin/env python3

import json
import logging
import os
from datetime import datetime
from functools import wraps
from io import BytesIO
from threading import Thread

import requests
from PIL import Image
from requests.auth import HTTPDigestAuth
from telegram import Bot
from telegram.ext import CommandHandler, Updater
from telegram.utils.request import Request


class ConfigError(Exception):
    pass


class UserAuthError(Exception):
    pass


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
    """CameraBot class where main bot things are done"""

    def __init__(self, token, user_id_list, cam_instances):
        super(CameraBot, self).__init__(token, request=(Request(con_pool_size=10)))
        self.cam_instances = cam_instances
        self.user_id_list = user_id_list
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.addHandler(file_handler)

    def send_startup_message(self):
        """Send welcome message after bot launch"""
        self.log.info('Sending welcome message')
        [self.send_message(user_id, '{0} bot started, see /help for available commands'.format(self.first_name)) for
         user_id in self.user_id_list]

    @authorization_check
    @camera_selection
    def cmd_getpic(self, update, cam, cam_id):
        """Gets and sends resized snapshot from the camera"""
        self.log.info('Resized snapshot requested')
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
        """Gets and sends full snapshot from the camera"""
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
        """Terminates bot"""
        msg = 'Stopping {0} bot'.format(self.first_name)

        self.log.info(msg)
        self.log.debug(self._get_user_info(update))

        update.message.reply_text(msg)

        thread = Thread(target=bot.stop_polling)
        thread.start()

    @authorization_check
    def cmd_list_cams(self, update):
        """Lists user's cameras"""
        self.log.info('Camera list has been requested')

        msg = ['<b>You have {0} cameras:</b>'.format(len(self.cam_instances))]

        for cam_id, cam_data in self.cam_instances.items():
            msg.append('<b>Camera:</b> {0}\n<b>Description:</b> {1}\n<b>Commands:</b> {2}'.format(
                cam_id, cam_data['instance'].description,
                ', '.join('/{0}'.format(cmds) for cmds in cam_data['commands'])))

        update.message.reply_html('\n\n'.join(msg))

        self.log.info('Camera list has been sent')

    def cmd_help(self, update, append=False, requested=True, cam_id=None):
        """Sends help message to telegram chat"""
        if requested:
            self.log.info('Help message has been requested')
            self.log.debug(self._get_user_info(update))
            update.message.reply_text('Use /list command to list available cameras and commands')
        elif append:
            update.message.reply_text('{0} to get pic or /list available cameras'.format(
                ', '.join('/{0}'.format(x) for x in self.cam_instances[cam_id]['commands'])))

        self.log.info('Help message has been sent')

    def error_handler(self, update, error):
        """Handles known telegram bot api errors"""
        self.log.error('Got error: {0}'.format(error))

    def print_helper(self, update, cam_id):
        """Sends help message to telegram chat after sending picture"""
        self.cmd_help(update, append=True, requested=False, cam_id=cam_id)

    def _print_access_error(self, update):
        """Sends authorization error to telegram chat"""
        update.message.reply_text('Not authorized')

    @staticmethod
    def _get_user_info(update):
        """Returns user information who interacts with bot"""
        return 'Request from user_id: {0}, username: {1}, first_name: {2}, last_name: {3}'.format(
            update.message.chat.id,
            update.message.chat.username,
            update.message.chat.first_name,
            update.message.chat.last_name
        )


class HomeCam:
    """Camera class"""

    def __init__(self, api, user, password, description):
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.addHandler(file_handler)
        self.api = api
        self.user = user
        self.password = password
        self.description = description
        self.r = requests
        self.snapshots_taken = 0

    def take_snapshot(self, update, resize=False):
        """Takes and returns full or resized snapshot from the camera"""
        self.log.debug('Snapshot from {0}'.format(self.api))

        try:
            auth = HTTPDigestAuth(self.user, self.password)
            response = self.r.get(self.api, auth=auth, stream=True)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            self.log.error('Connection to {0} failed'.format(self.description))
            update.message.reply_text(
                'Connection to {0} failed, try later or /list other cameras'.format(self.description))
            return None, None

        snapshot_timestamp = int(datetime.now().timestamp())
        self.snapshots_taken += 1

        snapshot = self.resize_snapshot(response.raw) if resize else response.raw

        return snapshot, snapshot_timestamp

    def resize_snapshot(self, raw_snapshot):
        """Resizes and returns JPEG snapshot"""
        size = 1280, 724
        snapshot = Image.open(raw_snapshot)
        resized_snapshot = BytesIO()

        snapshot.resize(size, Image.ANTIALIAS)
        snapshot.save(resized_snapshot, 'JPEG', quality=90)
        resized_snapshot.seek(0)

        self.log.debug("Raw snapshot: {0}, {1}, {2}".format(snapshot.format, snapshot.mode, snapshot.size))
        self.log.debug("Resized snapshot: {0}".format(size))

        return resized_snapshot


class CameraBotLauncher:
    """Bot launcher which parses configuration file, creates bot and camera instances and finally starts bot"""

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.addHandler(file_handler)
        self.config_file = 'config.json'
        self._config_options = self.load_config()
        self.welcome_sent = False

        options_telegram = self._config_options['telegram']
        telegram_token = options_telegram['token']
        telegram_allowed_uids = options_telegram['allowed_user_ids']

        cam_list = self._config_options['camera_list']
        cam_instances = self.create_cameras(cam_list)

        cambot = CameraBot(token=telegram_token,
                           user_id_list=telegram_allowed_uids,
                           cam_instances=cam_instances)

        self.updater = Updater(bot=cambot)

        getpic_commands, getfullpic_commands = self.create_setup_commands(cam_instances)
        self.setup_commands(getpic_commands, getfullpic_commands)

    def create_cameras(self, camera_list):
        """Creates dict with camera ids, instances and commands"""
        cams = {}

        for cam_id, cam_data in camera_list.items():
            user = cam_data['auth']['user']
            password = cam_data['auth']['password']
            api = cam_data['api']
            description = cam_data['desc']

            cams[cam_id] = {"instance": HomeCam(api, user, password, description),
                            'commands': ['getpic_{0}'.format(cam_id), 'getfullpic_{0}'.format(cam_id)]}

        self.log.debug('Creating cameras: {0}'.format(cams))

        return cams

    def create_setup_commands(self, cams):
        """Returns lists of commands which are passed to Dispatcher handler"""
        getpic_commands = []
        getfullpic_commands = []

        for cam in cams.values():
            getpic_commands.append(cam['commands'][0])
            getfullpic_commands.append(cam['commands'][1])

        return getpic_commands, getfullpic_commands

    def run(self):
        """Starts and runs bot"""
        self.log.info('Starting {0} bot'.format(self.updater.bot.first_name))

        if not self.welcome_sent:
            self.updater.bot.send_startup_message()
            self.welcome_sent = True

        self.updater.start_polling()
        self.updater.idle()

    def stop_polling(self):
        """Stops bot and exits application"""
        self.updater.stop()
        self.updater.is_idle = False

    def load_config(self):
        """Loads telegram and camera configuration from config file and returns json object"""
        if not os.path.isfile(self.config_file):
            error_message = 'Cannot find {0} file'.format(self.config_file)
            self.log.error(error_message)
            raise ConfigError(error_message)

        with open(self.config_file, 'r') as f:
            self.log.debug('Reading config file {0}'.format(self.config_file))
            config = f.read()

        try:
            config_json = json.loads(config, object_pairs_hook=self.conf_raise_on_duplicates)
        except json.decoder.JSONDecodeError:
            error_message = 'Malformed configuration file {0}'.format(self.config_file)
            self.log.error(error_message)
            raise ConfigError(error_message)

        return config_json

    def conf_raise_on_duplicates(self, config_data):
        """Raise ConfigError on duplicate keys"""
        conf_dict = {}

        for key, value in config_data:
            if key in conf_dict:
                error_message = "Malformed configuration file {0}, duplicate key: {1}".format(self.config_file, key)
                self.log.error(error_message)
                raise ConfigError(error_message)
            else:
                conf_dict[key] = value

        return conf_dict

    def setup_commands(self, getpic_commands, getfullpic_commands):
        """Setup for Dispatcher with bot commands and error handler"""
        dispatcher = self.updater.dispatcher

        dispatcher.add_handler(CommandHandler('help', CameraBot.cmd_help))
        dispatcher.add_handler(CommandHandler('start', CameraBot.cmd_help))
        dispatcher.add_handler(CommandHandler(getpic_commands, CameraBot.cmd_getpic))
        dispatcher.add_handler(CommandHandler(getfullpic_commands, CameraBot.cmd_getfullpic))
        dispatcher.add_handler(CommandHandler('list', CameraBot.cmd_list_cams))
        dispatcher.add_handler(CommandHandler('stop', CameraBot.cmd_stop))

        dispatcher.add_error_handler(CameraBot.error_handler)


if __name__ == '__main__':
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=log_format, level=logging.INFO)
    file_handler = logging.FileHandler('{0}.log'.format(os.path.splitext(os.path.basename(__file__))[0]))
    file_handler.setFormatter(logging.Formatter(log_format))

    bot = CameraBotLauncher()
    bot.run()
