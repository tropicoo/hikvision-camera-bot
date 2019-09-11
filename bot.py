#!/usr/bin/env python3
"""Bot Launcher Module."""

import logging
import re
import sys
from collections import defaultdict

from telegram.ext import CommandHandler, Updater

from hikcamerabot.camera import HikvisionCam, CameraPoolController
from hikcamerabot.camerabot import CameraBot
from hikcamerabot.config import get_main_config
from hikcamerabot.constants import CONF_CAM_ID_REGEX
from hikcamerabot.directorywatcher import DirectoryWatcher
from hikcamerabot.exceptions import DirectoryWatcherError, ConfigError


class CameraBotLauncher:
    """Bot launcher which parses configuration file, creates bot and
    camera instances and finally starts the bot.
    """

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        self._conf = get_main_config()
        logging.getLogger().setLevel(self._conf.log_level)

        cambot = CameraBot(stop_polling=self._stop_polling)

        # Not the prettiest way in v.12 of the telegram-bot framework.
        # TODO: Create pure callback functions and call hikbot's public methods?
        # TODO: Extend mapping for dot notation object.
        self._tpl_commands = {
            'General Commands': {
                'commands': {
                    'cmds_{0}': cambot.cmds,
                    'getpic_{0}': cambot.cmd_getpic,
                    'getfullpic_{0}': cambot.cmd_getfullpic}},
            'Motion Detection Commands': {
                'commands': {
                    'md_on_{0}': cambot.cmd_motion_detection_on,
                    'md_off_{0}': cambot.cmd_motion_detection_off}},
            'Line Crossing Detection Commands': {
                'commands': {
                    'ld_on_{0}': cambot.cmd_line_detection_on,
                    'ld_off_{0}': cambot.cmd_line_detection_off}},
            'Alert Commands': {
                'commands': {
                    'alert_on_{0}': cambot.cmd_alert_on,
                    'alert_off_{0}': cambot.cmd_alert_off}},
            'YouTube Stream Commands': {
                'commands': {
                    'yt_on_{0}': cambot.cmd_stream_yt_on,
                    'yt_off_{0}': cambot.cmd_stream_yt_off}},
            'Icecast Stream Commands': {
                'commands': {
                    'icecast_on_{0}': cambot.cmd_stream_icecast_on,
                    'icecast_off_{0}': cambot.cmd_stream_icecast_off}}}
        self._commands = {('start', 'help'): cambot.cmd_help,
                          'stop': cambot.cmd_stop,
                          'list': cambot.cmd_list_cams}

        self._updater = Updater(bot=cambot, use_context=True)
        cam_pool = self._create_and_setup_cameras()
        self._updater.bot.add_camera_pool(cam_pool)

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

    def _create_and_setup_cameras(self):
        """Create cameras, camera pool and setup for Dispatcher."""
        cam_pool = CameraPoolController()
        setup_dispatcher = lambda command, handler: \
            self._updater.dispatcher.add_handler(
                CommandHandler(command, handler_func))

        # Iterate trough config, setup Dispatcher commands and create cameras
        for cam_id, cam_conf in self._conf.camera_list.items():
            if not re.match(CONF_CAM_ID_REGEX, cam_id):
                msg = 'Wrong camera name "{0}". Follow "cam_1, cam_2, ..., ' \
                      'cam_<number>" naming pattern.'.format(cam_id)
                self._log.error(msg)
                raise ConfigError(msg)

            # Format command templates and setup for Dispatcher
            cam_commands = defaultdict(list)
            for desc, group in self._tpl_commands.items():
                for command, handler_func in group['commands'].items():
                    command = command.format(cam_id)
                    cam_commands[desc].append(command)
                    setup_dispatcher(command, handler_func)

            self._log.info(cam_pool)
            cam_pool.add(cam_id, cam_commands, HikvisionCam(conf=cam_conf))

        # Setup bot-wide commands
        for command, handler_func in self._commands.items():
            setup_dispatcher(command, handler_func)
        self._updater.dispatcher.add_error_handler(CameraBot.error_handler)

        self._log.debug('Created Camera Pool: %s', cam_pool)
        return cam_pool

    def _stop_polling(self):
        """Stop bot and exit application."""
        self._updater.stop()
        self._updater.is_idle = False


if __name__ == '__main__':
    if sys.version_info[:2] < (3, 6):
        sys.exit('Python version needs to be at least 3.6.\n'
                 'Current version: {0}\n'
                 'Please update and try again.'.format(sys.version))

    log_format = '%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=log_format)

    bot = CameraBotLauncher()
    bot.run()
