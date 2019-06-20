#!/usr/bin/env python3
"""Bot Launcher Module."""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict

from telegram.ext import CommandHandler, Updater

from camerabot.camerabot import CameraBot
from camerabot.directorywatcher import DirectoryWatcher, DirectoryWatcherError
from camerabot.exceptions import ConfigError
from camerabot.homecam import HomeCam
from camerabot.constants import CONFIG_FILE, LOG_LEVELS_STR, COMMANDS


class Config:

    """Dot notation for JSON config file."""

    def __init__(self, conf_data):
        self.__conf_data = conf_data

    def __iter__(self):
        return self.__conf_data

    def __repr__(self):
        return repr(self.__conf_data)

    def __getitem__(self, item):
        return self.__conf_data[item]

    def items(self):
        return self.__conf_data.items()

    @classmethod
    def from_dict(cls, conf_data):
        """Make dot-mapped object."""
        conf_dict = cls._conf_raise_on_duplicates(conf_data)
        obj = cls(conf_dict)
        obj.__dict__.update(conf_data)
        return obj

    @classmethod
    def _conf_raise_on_duplicates(cls, conf_data):
        """Raise ConfigError on duplicate keys."""
        conf_dict = {}
        for key, value in conf_data:
            if key in conf_dict:
                err_msg = "Malformed configuration file, duplicate key: {0}".format(key)
                raise ConfigError(err_msg)
            else:
                conf_dict[key] = value
        return conf_dict


class CameraBotLauncher:

    """Bot launcher which parses configuration file, creates bot and
    camera instances and finally starts bot.
    """

    def __init__(self, conf_path=CONFIG_FILE):
        self._log = logging.getLogger(self.__class__.__name__)

        try:
            conf = self._load_config(conf_path)
        except ConfigError as err:
            sys.exit(str(err))

        tg_token = conf.telegram.token
        tg_allowed_uids = conf.telegram.allowed_user_ids
        cam_list = conf.camera_list
        self._wd_is_enabled = conf.watchdog.enabled
        wd_directory = conf.watchdog.directory

        log_level = self._get_int_log_level(conf.log_level)
        logging.getLogger().setLevel(log_level)

        cam_instances, cmds = self._create_cameras(cam_list)

        cambot = CameraBot(token=tg_token,
                           user_ids=tg_allowed_uids,
                           cam_instances=cam_instances,
                           stop_polling=self._stop_polling)

        self._updater = Updater(bot=cambot)
        self._setup_commands(cmds)

        self._directory_watcher = DirectoryWatcher(bot=self._updater,
                                                   directory=wd_directory)
        self._welcome_sent = False

    def run(self):
        """Run bot and DirectoryWatcher."""
        self._log.info('Starting {0} bot'.format(self._updater.bot.first_name))

        if not self._welcome_sent:
            self._updater.bot.send_startup_message()
            self._welcome_sent = True

        self._updater.start_polling()

        # Blocks code execution until signal is received, therefore
        # 'self._directory_watcher.run' won't execute.
        # self._updater.idle()

        try:
            if self._wd_is_enabled:
                self._directory_watcher.watch()
        except DirectoryWatcherError as err:
            self._stop_polling()
            sys.exit(str(err))

    def _create_cameras(self, camera_list):
        """Creates dict with camera ids, instances and commands."""
        cams = {}
        cmds = defaultdict(list)
        for cam_id, cam_conf in camera_list.items():
            cams[cam_id] = {"instance": HomeCam(conf=cam_conf),
                            'commands': []}
            for key, cmd_tpl in COMMANDS.items():
                cmd = cmd_tpl.format(cam_id)
                cams[cam_id]['commands'].append(cmd)
                cmds[key].append(cmd)

        self._log.debug('Creating cameras: {0}'.format(cams))
        return cams, cmds

    def _stop_polling(self):
        """Stops bot and exits application."""
        self._updater.stop()
        self._updater.is_idle = False

    def _load_config(self, path):
        """Loads telegram and camera configuration from config file
        and returns json object.
        """
        if not os.path.isfile(path):
            err_msg = 'Can\'t find {0} configuration file'.format(path)
            raise ConfigError(err_msg)

        self._log.info('Reading config file {0}'.format(path))
        with open(path, 'r') as fd:
            config = fd.read()
        try:
            config = json.loads(config, object_pairs_hook=Config.from_dict)
        except json.decoder.JSONDecodeError:
            err_msg = 'Malformed JSON in {0} configuration file'.format(path)
            raise ConfigError(err_msg)

        return config

    def _setup_commands(self, cmds):
        """Setup for Dispatcher with bot commands and error handler."""
        dispatcher = self._updater.dispatcher

        dispatcher.add_handler(CommandHandler('help', CameraBot.cmd_help))
        dispatcher.add_handler(CommandHandler('start', CameraBot.cmd_help))
        dispatcher.add_handler(CommandHandler(cmds['getpic'],
                                              CameraBot.cmd_getpic))
        dispatcher.add_handler(CommandHandler(cmds['getfullpic'],
                                              CameraBot.cmd_getfullpic))
        dispatcher.add_handler(CommandHandler(cmds['md_on'],
                                              CameraBot.cmd_motion_detection_on))
        dispatcher.add_handler(CommandHandler(cmds['md_off'],
                                              CameraBot.cmd_motion_detection_off))
        dispatcher.add_handler(CommandHandler(cmds['ld_on'],
                                              CameraBot.cmd_line_detection_on))
        dispatcher.add_handler(CommandHandler(cmds['ld_off'],
                                              CameraBot.cmd_line_detection_off))
        dispatcher.add_handler(CommandHandler(cmds['alert_on'],
                                              CameraBot.cmd_alert_on))
        dispatcher.add_handler(CommandHandler(cmds['alert_off'],
                                              CameraBot.cmd_alert_off))
        dispatcher.add_handler(CommandHandler(cmds['yt_on'],
                                              CameraBot.cmd_stream_yt_on))
        dispatcher.add_handler(CommandHandler(cmds['yt_off'],
                                              CameraBot.cmd_stream_yt_off))
        dispatcher.add_handler(CommandHandler(cmds['cmds'], CameraBot.cmds))
        dispatcher.add_handler(CommandHandler('list', CameraBot.cmd_list_cams))
        dispatcher.add_handler(CommandHandler('stop', CameraBot.cmd_stop))

        dispatcher.add_error_handler(CameraBot.error_handler)

    def _get_int_log_level(self, log_level_str):
        if log_level_str not in LOG_LEVELS_STR:
            warn_msg = 'Invalid log level "{0}", using "INFO". ' \
                       'Choose from {1})'.format(log_level_str, LOG_LEVELS_STR)
            self._log.warning(warn_msg)
        return getattr(logging, log_level_str, logging.INFO)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HikVision Telegram Camera Bot')
    parser.add_argument('-c', '--config', action='store',
                        dest='conf_path', default='config.json',
                        help='path to configuration json file')
    args = parser.parse_args()

    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=log_format)

    bot = CameraBotLauncher(conf_path=args.conf_path)
    bot.run()
