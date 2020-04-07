#!/usr/bin/env python3
"""Bot Launcher Module."""

import logging
import re
import sys
from collections import defaultdict
from multiprocessing import Queue

from telegram.ext import CommandHandler, Updater

import hikcamerabot.callbacks as cb
from hikcamerabot.camerabot import CameraBot
from hikcamerabot.commands import setup_commands
from hikcamerabot.config import get_main_config
from hikcamerabot.constants import CONF_CAM_ID_REGEX
from hikcamerabot.directorywatcher import DirectoryWatcher
from hikcamerabot.exceptions import DirectoryWatcherError, ConfigError
from hikcamerabot.registry import CameraMetaRegistry


class CameraBotLauncher:
    """Bot launcher which parses configuration file, creates bot and
    camera instances and finally starts the bot.
    """

    def __init__(self):
        """Constructor."""
        self._log = logging.getLogger(self.__class__.__name__)
        self._conf = get_main_config()
        logging.getLogger().setLevel(self._conf.log_level)

        event_queues, cam_registry, cmd_handlers = self._create_and_setup_cameras()
        self._bot = CameraBot(event_queues=event_queues,
                              cam_registry=cam_registry,
                              stop_polling=self._stop_polling)
        self._updater = Updater(bot=self._bot, use_context=True)
        self._setup_dispatcher(cmd_handlers)
        self._directory_watcher = DirectoryWatcher(bot=self._bot)
        self._welcome_sent = False

    def run(self):
        """Run bot and DirectoryWatcher."""
        self._log.info('Starting %s bot', self._updater.bot.first_name)
        self._send_welcome_message()
        self._start_bot()
        self._start_directory_watcher()

    def _start_bot(self):
        """Start telegram bot and related processes."""
        self._updater.bot.start_processes()
        self._updater.start_polling()

        # Blocks main thread, do not uncomment if something should be
        # executed after this code block.
        # self._updater.idle()

    def _start_directory_watcher(self):
        """Start Directory Watcher service."""
        if self._conf.watchdog.enabled:
            try:
                self._directory_watcher.watch()
            except DirectoryWatcherError as err:
                self._stop_polling()
                sys.exit(err)

    def _send_welcome_message(self):
        """Send welcome message to the user after start."""
        if not self._welcome_sent:
            self._updater.bot.send_startup_message()
            self._welcome_sent = True

    def _setup_dispatcher(self, cmd_handlers):
        """Setup Dispatcher.

        :Parameters:
            - `cmd_handlers`: list of `CommandHandler` objects.
        """
        for handler in cmd_handlers:
            self._updater.dispatcher.add_handler(handler)
        self._updater.dispatcher.add_error_handler(cb.error_handler)

    def _create_and_setup_cameras(self):
        """Create cameras and setup for the `telegram.Dispatcher`.

        Iterate trough the config, create event queues per camera,
        setup camera registry and command handlers.
        """
        event_queue = {}
        cmd_handlers = []
        cam_registry = CameraMetaRegistry()
        tpl_cmds, bot_wide_cmds = setup_commands()

        for cam_id, cam_conf in self._conf.camera_list.items():
            self._validate_camera_name(cam_id)

            event_queue[cam_id] = Queue()
            cam_cmds = defaultdict(list)

            for description, group in tpl_cmds.items():
                for cmd, handler_func in group['commands'].items():
                    cmd = cmd.format(cam_id)
                    cam_cmds[description].append(cmd)
                    cmd_handlers.append(CommandHandler(cmd, handler_func))

            cam_registry.add(cam_id, cam_cmds, cam_conf)

        self._setup_bot_wide_cmds(bot_wide_cmds, cmd_handlers)
        self._log.debug('Camera Meta Registry: %r', cam_registry)
        return event_queue, cam_registry, cmd_handlers

    def _setup_bot_wide_cmds(self, bot_wide_cmds, cmd_handlers):
        """Setup bot-wide command handlers."""
        for cmd, handler_func in bot_wide_cmds.items():
            cmd_handlers.append(CommandHandler(cmd, handler_func))

    def _validate_camera_name(self, cam_id):
        """Validate camera name followed by pattern `cam_<int_id>`."""
        if not re.match(CONF_CAM_ID_REGEX, cam_id):
            msg = f'Wrong camera name "{cam_id}". Follow "cam_1, cam_2, ' \
                  f'..., cam_<number>" naming pattern.'
            self._log.error(msg)
            raise ConfigError(msg)

    def _stop_polling(self):
        """Stop bot and exit application."""
        self._updater.stop()
        self._updater.is_idle = False


if __name__ == '__main__':
    log_format = '%(asctime)s - [%(levelname)s] - [%(name)s:%(lineno)s] - %(message)s'
    logging.basicConfig(format=log_format)

    bot_engine = CameraBotLauncher()
    bot_engine.run()
