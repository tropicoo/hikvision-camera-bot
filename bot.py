#!/usr/bin/env python3

import json
import logging
import os

from telegram.ext import CommandHandler, Updater

from camerabot.camerabot import CameraBot
from camerabot.error import ConfigError
from camerabot.homecam import HomeCam


class CameraBotLauncher:
    """Bot launcher which parses configuration file, creates bot and camera instances and finally starts bot."""

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        self._config_file = 'config.json'
        self._config_options = self._load_config()
        self._welcome_sent = False

        telegram_options = self._config_options['telegram']
        telegram_token = telegram_options['token']
        telegram_allowed_uids = telegram_options['allowed_user_ids']

        cam_list = self._config_options['camera_list']
        cam_instances = self._create_cameras(cam_list)

        cambot = CameraBot(token=telegram_token,
                           user_id_list=telegram_allowed_uids,
                           cam_instances=cam_instances,
                           stop_polling=self._stop_polling)

        self._updater = Updater(bot=cambot)

        getpic_commands, getfullpic_commands = self._create_setup_commands(cam_instances)
        self._setup_commands(getpic_commands, getfullpic_commands)

    def _create_cameras(self, camera_list):
        """Creates dict with camera ids, instances and commands."""
        cams = {}

        for cam_id, cam_data in camera_list.items():
            user = cam_data['auth']['user']
            password = cam_data['auth']['password']
            api = cam_data['api']
            description = cam_data['desc']

            cams[cam_id] = {"instance": HomeCam(api, user, password, description),
                            'commands': ['getpic_{0}'.format(cam_id),
                                         'getfullpic_{0}'.format(cam_id)]}

        self._log.debug('Creating cameras: {0}'.format(cams))
        return cams

    @staticmethod
    def _create_setup_commands(cams):
        """Returns lists of commands which are passed to Dispatcher handler."""
        getpic_commands = []
        getfullpic_commands = []

        for cam in cams.values():
            getpic_commands.append(cam['commands'][0])
            getfullpic_commands.append(cam['commands'][1])

        return getpic_commands, getfullpic_commands

    def run(self):
        """Starts and runs bot."""
        self._log.info('Starting {0} bot'.format(self._updater.bot.first_name))

        if not self._welcome_sent:
            self._updater.bot.send_startup_message()
            self._welcome_sent = True

        self._updater.start_polling()
        self._updater.idle()

    def _stop_polling(self):
        """Stops bot and exits application."""
        self._updater.stop()
        self._updater.is_idle = False

    def _load_config(self):
        """Loads telegram and camera configuration from config file and returns json object."""
        if not os.path.isfile(self._config_file):
            error_message = 'Cannot find {0} file'.format(self._config_file)
            self._log.error(error_message)
            raise ConfigError(error_message)

        with open(self._config_file, 'r') as f:
            self._log.debug('Reading config file {0}'.format(self._config_file))
            config = f.read()

        try:
            config_json = json.loads(config, object_pairs_hook=self._conf_raise_on_duplicates)
        except json.decoder.JSONDecodeError:
            error_message = 'Malformed configuration file {0}'.format(self._config_file)
            self._log.error(error_message)
            raise ConfigError(error_message)

        return config_json

    def _conf_raise_on_duplicates(self, config_data):
        """Raise ConfigError on duplicate keys."""
        conf_dict = {}

        for key, value in config_data:
            if key in conf_dict:
                error_message = "Malformed configuration file {0}, duplicate key: {1}".format(self._config_file, key)
                self._log.error(error_message)
                raise ConfigError(error_message)
            else:
                conf_dict[key] = value

        return conf_dict

    def _setup_commands(self, getpic_commands, getfullpic_commands):
        """Setup for Dispatcher with bot commands and error handler."""
        dispatcher = self._updater.dispatcher

        dispatcher.add_handler(CommandHandler('help', CameraBot.cmd_help))
        dispatcher.add_handler(CommandHandler('start', CameraBot.cmd_help))
        dispatcher.add_handler(CommandHandler(getpic_commands, CameraBot.cmd_getpic))
        dispatcher.add_handler(CommandHandler(getfullpic_commands, CameraBot.cmd_getfullpic))
        dispatcher.add_handler(CommandHandler('list', CameraBot.cmd_list_cams))
        dispatcher.add_handler(CommandHandler('stop', CameraBot.cmd_stop))

        dispatcher.add_error_handler(CameraBot.error_handler)


if __name__ == '__main__':
    log_level = logging.DEBUG
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=log_format, level=log_level)

    bot = CameraBotLauncher()
    bot.run()
