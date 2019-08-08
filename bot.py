#!/usr/bin/env python3
"""Bot Launcher Module."""

import logging
import itertools
import sys
from collections import defaultdict

from telegram.ext import CommandHandler, Updater

from camerabot.camerabot import CameraBot
from camerabot.config import get_main_config
from camerabot.directorywatcher import DirectoryWatcher
from camerabot.exceptions import DirectoryWatcherError
from camerabot.homecam import HomeCam, CameraPoolController

COMMANDS_TPL = {CameraBot.cmds: 'cmds_{0}',
                CameraBot.cmd_getpic: 'getpic_{0}',
                CameraBot.cmd_getfullpic: 'getfullpic_{0}',
                CameraBot.cmd_motion_detection_on: 'md_on_{0}',
                CameraBot.cmd_motion_detection_off: 'md_off_{0}',
                CameraBot.cmd_line_detection_on: 'ld_on_{0}',
                CameraBot.cmd_line_detection_off: 'ld_off_{0}',
                CameraBot.cmd_alert_on: 'alert_on_{0}',
                CameraBot.cmd_alert_off: 'alert_off_{0}',
                CameraBot.cmd_stream_yt_on: 'yt_on_{0}',
                CameraBot.cmd_stream_yt_off: 'yt_off_{0}',
                CameraBot.cmd_stream_icecast_on: 'icecast_on_{0}',
                CameraBot.cmd_stream_icecast_off: 'icecast_off_{0}'}

COMMANDS = {CameraBot.cmd_help: ('start', 'help'),
            CameraBot.cmd_stop: 'stop',
            CameraBot.cmd_list_cams: 'list'}


class CameraBotLauncher:
    """Bot launcher which parses configuration file, creates bot and
    camera instances and finally starts the bot.
    """

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        self._conf = get_main_config()

        logging.getLogger().setLevel(self._conf.log_level)

        cam_pool, cmds = self._create_cameras()
        cambot = CameraBot(pool=cam_pool, stop_polling=self._stop_polling)

        self._updater = Updater(bot=cambot)
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

        # Blocks code execution until signal is received, therefore
        # 'self._directory_watcher.run' won't execute.
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
            cam_cmds = []
            for handler_func, cmd_tpl in COMMANDS_TPL.items():
                cmd = cmd_tpl.format(cam_id)
                cam_cmds.append(cmd)
                cmd_cam_map[handler_func].append(cmd)

            cam_pool.add(cam_id, cam_cmds, HomeCam(conf=cam_conf))

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
                in itertools.chain(cmds.items(), COMMANDS.items()):
            dispatcher.add_handler(CommandHandler(event_funcs, handler_func))

        dispatcher.add_error_handler(CameraBot.error_handler)


if __name__ == '__main__':
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=LOG_FORMAT)

    BOT = CameraBotLauncher()
    BOT.run()
