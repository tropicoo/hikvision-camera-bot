#!/usr/bin/env python3
"""Bot Launcher Module."""

import logging
import itertools
import re
import sys
from collections import defaultdict

from telegram.ext import CommandHandler, Updater

from camerabot.camera import HikvisionCam, CameraPoolController
from camerabot.camerabot import CameraBot
from camerabot.config import get_main_config
from camerabot.constants import CONF_CAM_ID_REGEX
from camerabot.directorywatcher import DirectoryWatcher
from camerabot.exceptions import DirectoryWatcherError, ConfigError


class CameraBotLauncher:
    """Bot launcher which parses configuration file, creates bot and
    camera instances and finally starts the bot.
    """

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        self._conf = get_main_config()
        logging.getLogger().setLevel(self._conf.log_level)

        cambot = CameraBot(stop_polling=self._stop_polling)
        self._commands_tpl = {cambot.cmds: 'cmds_{0}',
                              cambot.cmd_getpic: 'getpic_{0}',
                              cambot.cmd_getfullpic: 'getfullpic_{0}',
                              cambot.cmd_motion_detection_on: 'md_on_{0}',
                              cambot.cmd_motion_detection_off: 'md_off_{0}',
                              cambot.cmd_line_detection_on: 'ld_on_{0}',
                              cambot.cmd_line_detection_off: 'ld_off_{0}',
                              cambot.cmd_alert_on: 'alert_on_{0}',
                              cambot.cmd_alert_off: 'alert_off_{0}',
                              cambot.cmd_stream_yt_on: 'yt_on_{0}',
                              cambot.cmd_stream_yt_off: 'yt_off_{0}',
                              cambot.cmd_stream_icecast_on: 'icecast_on_{0}',
                              cambot.cmd_stream_icecast_off: 'icecast_off_{0}'}
        self._commands = {cambot.cmd_help: ('start', 'help'),
                          cambot.cmd_stop: 'stop',
                          cambot.cmd_list_cams: 'list'}

        cam_pool, cmds = self._create_cameras()
        cambot.add_camera_pool(cam_pool)

        self._updater = Updater(bot=cambot, use_context=True)
        self._setup_commands(cmds)

        self._directory_watcher = DirectoryWatcher(bot=self._updater)
        self._welcome_sent = False

    def run(self):
        """Run bot and DirectoryWatcher."""
        self._log.info('Starting %s bot', self._updater.bot.first_name)

        if not self._welcome_sent:
            self._updater.bot.send_startup_message()
            self._welcome_sent = True

        self._updater.start_polling()
        self._updater.bot.start_enabled_services()

        # Blocking
        # self._updater.idle()

        try:
            if self._conf.watchdog.enabled:
                self._directory_watcher.watch()
        except DirectoryWatcherError as err:
            self._stop_polling()
            sys.exit(err)

    def _create_cameras(self):
        """Create dict with camera IDs, instances and commands."""
        cmd_cam_map = defaultdict(list)
        cam_pool = CameraPoolController()
        for cam_id, cam_conf in self._conf.camera_list.items():
            if not re.match(CONF_CAM_ID_REGEX, cam_id):
                msg = 'Wrong camera name "{0}". Follow "cam_1, cam_2, ..., ' \
                      'cam_<number>" naming pattern.'.format(cam_id)
                self._log.error(msg)
                raise ConfigError(msg)

            cam_cmds = []
            for handler_func, cmd_tpl in self._commands_tpl.items():
                cmd = cmd_tpl.format(cam_id)
                cam_cmds.append(cmd)
                cmd_cam_map[handler_func].append(cmd)

            self._log.info(cam_pool)
            cam_pool.add(cam_id, cam_cmds, HikvisionCam(conf=cam_conf))

        self._log.debug('Created Camera Pool: %s', cam_pool)
        return cam_pool, cmd_cam_map

    def _stop_polling(self):
        """Stop bot and exits application."""
        self._updater.stop()
        self._updater.is_idle = False

    def _setup_commands(self, cmds):
        """Setup for Dispatcher with bot commands and error handler."""
        dispatcher = self._updater.dispatcher

        for handler_func, event_funcs \
                in itertools.chain(cmds.items(), self._commands.items()):
            dispatcher.add_handler(CommandHandler(event_funcs, handler_func))

        dispatcher.add_error_handler(CameraBot.error_handler)


if __name__ == '__main__':
    if sys.version_info[:2] < (3, 6):
        sys.exit('Python version needs to be at least 3.6.\n'
                 'Current version: {0}\n'
                 'Please update and try again.'.format(sys.version))

    log_format = '%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=log_format)

    bot = CameraBotLauncher()
    bot.run()
