"""Directory Watcher Module."""

import datetime
import logging
import os
import time

from pathlib import Path
from subprocess import call
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from camerabot.exceptions import DirectoryWatcherError


class DirectoryWatcher:

    """Watchdog class."""

    def __init__(self, bot, directory):
        self._log = logging.getLogger(self.__class__.__name__)
        self.directory = directory
        self._event_handler = DirectoryWatcherEventHandler(bot=bot)
        self._observer = Observer()

        self._log.info('Initializing DirectoryWatcher')

    def watch(self):
        """Watches directory for new files."""
        path = Path(self.directory)
        if not path.exists() and not path.is_dir():
            err_msg = 'Watchdog directory "{0}" ' \
                      'doesn\'t exist.'.format(self.directory)
            self._log.error(err_msg)
            raise DirectoryWatcherError(err_msg)

        self._log.info('Starting to watch {0}'.format(self.directory))
        self._observer.schedule(self._event_handler, self.directory)
        self._observer.start()
        try:
            while True:
                time.sleep(1)
        except Exception as err:
            self._log.error('Watchdog encountered an error: {0}'.format(str(err)))
            self._observer.stop()
        self._observer.join()


class DirectoryWatcherEventHandler(FileSystemEventHandler):

    """EventHandler class."""

    def __init__(self, bot):
        self._log = logging.getLogger(self.__class__.__name__)
        self._bot = bot

    def on_created(self, event):
        """Handles Watchdog's 'on_create' event."""
        file_path = event.src_path
        cmd = "lsof|awk 'match($9,/{0}/){{print $9}}'".format(
            os.path.basename(file_path))
        while True:
            try:
                if not call(cmd, shell=True):
                    break
            except Exception as err:
                self._log.error('EventHandler encountered an '
                                'error: {0}'.format(str(err)))
                raise DirectoryWatcherError(err)
        try:
            self._log.info('Sending {0} to {1}'.format(file_path,
                                                       self._bot.bot.first_name))
            now = datetime.datetime.now()
            caption = 'Directory Watcher Alert at {0}'.format(
                now.strftime('%Y-%m-%d %H:%M:%S'))
            with open(file_path, 'rb') as fd:
                self._bot.bot.reply_cam_photo(photo=fd, caption=caption,
                                              from_watchdog=True)
        except Exception as err:
            self._log.error('Can\'t open {0} for sending: {1}'.format(file_path,
                                                                      str(err)))
            raise DirectoryWatcherError(err)
        try:
            self._log.info('{0} sent, deleting'.format(file_path))
            os.remove(file_path)
        except Exception as err:
            self._log.error('Can\'t delete {0}: {1}'.format(file_path, str(err)))
            raise DirectoryWatcherError(err)
