#!/usr/bin/env python3
"""Bot Launcher Module."""

import logging
import re
import sys
from collections import defaultdict
from multiprocessing import Queue

from telegram.ext import CommandHandler, Updater

import hikcamerabot.callbacks.callbacks as cb
from hikcamerabot.camerabot import CameraBot
from hikcamerabot.commands import setup_commands
from hikcamerabot.config import get_main_config
from hikcamerabot.constants import CONF_CAM_ID_REGEX
from hikcamerabot.directorywatcher import DirectoryWatcher
from hikcamerabot.exceptions import DirectoryWatcherError, ConfigError
from hikcamerabot.registry import CameraRegistry


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

        bot = CameraBot(event_queues=event_queues,
                        cam_registry=cam_registry,
                        stop_polling=self._stop_polling)

        self._updater = Updater(bot=bot, use_context=True)
        self._setup_dispatcher(cmd_handlers)

        self._directory_watcher = DirectoryWatcher(bot=self._updater.bot)
        self._welcome_sent = False

    def _setup_dispatcher(self, cmd_handlers):
        """Setup Dispatcher.

        Parameters:
            - `cmd_handlers`: list of `CommandHandler` objects.
        """
        for handler in cmd_handlers:
            self._updater.dispatcher.add_handler(handler)
        self._updater.dispatcher.add_error_handler(cb.error_handler)

    def run(self):
        """Run bot and DirectoryWatcher."""
        self._log.info('Starting %s bot', self._updater.bot.first_name)

        if not self._welcome_sent:
            self._updater.bot.send_startup_message()
            self._welcome_sent = True

        self._updater.bot.start_processes()
        self._updater.start_polling()

        # Blocking main thread
        # self._updater.idle()

        try:
            if self._conf.watchdog.enabled:
                self._directory_watcher.watch()
        except DirectoryWatcherError as err:
            self._stop_polling()
            sys.exit(err)

    def _create_and_setup_cameras(self):
        """Create cameras and setup for Dispatcher."""

        event_queue = {}
        cmd_handlers = []
        cam_registry = CameraRegistry()

        tpl_cmds, bot_wide_cmds = setup_commands()

        # Iterate trough the config, setup command handlers, setup camera
        # registry and create event queues per camera
        for cam_id, cam_conf in self._conf.camera_list.items():
            if not re.match(CONF_CAM_ID_REGEX, cam_id):
                msg = f'Wrong camera name "{cam_id}". Follow "cam_1, cam_2, ' \
                      f'..., cam_<number>" naming pattern.'
                self._log.error(msg)
                raise ConfigError(msg)

            # Create event queue for particular camera
            event_queue[cam_id] = Queue()

            # Format command templates and setup for Dispatcher
            cam_cmds = defaultdict(list)
            for desc, group in tpl_cmds.items():
                for cmd, handler_func in group['commands'].items():
                    cmd = cmd.format(cam_id)
                    cam_cmds[desc].append(cmd)
                    cmd_handlers.append(CommandHandler(cmd, handler_func))

            cam_registry.add(cam_id, cam_cmds, cam_conf)

        # Setup bot-wide command handlers
        for cmd, handler_func in bot_wide_cmds.items():
            cmd_handlers.append(CommandHandler(cmd, handler_func))

        self._log.debug('Camera Registry: %r', cam_registry)
        return event_queue, cam_registry, cmd_handlers

    def _stop_polling(self):
        """Stop bot and exit application."""
        self._updater.stop()
        self._updater.is_idle = False


if __name__ == '__main__':
    log_format = '%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=log_format)

    bot_engine = CameraBotLauncher()
    bot_engine.run()
