"""Camera Bot Module."""

import logging
from pathlib import PurePath

from telegram import Bot
from telegram.utils.request import Request

from hikcamerabot.config import get_main_config
from hikcamerabot.constants import (SEND_TIMEOUT)
from hikcamerabot.handlers import ResultDispatcher, ResultHandlerThread
from hikcamerabot.managers.event import TaskEventManager
from hikcamerabot.managers.process import CameraProcessManager
from hikcamerabot.managers.thread import ThreadManager


class CameraBot(Bot):
    """CameraBot class where main bot things are done."""

    def __init__(self, event_queues, cam_registry, stop_polling):
        conf = get_main_config()
        super().__init__(conf.telegram.token,
                         request=(Request(con_pool_size=10)))
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.info('Initializing %s bot', self.first_name)
        self.stop_polling = stop_polling
        self.user_ids = conf.telegram.allowed_user_ids
        self._updates = {}
        self.cam_registry = cam_registry

        dispatcher = ResultDispatcher(bot=self, cam_registry=cam_registry)

        self.event_manager = TaskEventManager(event_queues)
        self.proc_manager = CameraProcessManager(cam_registry, event_queues)
        self.thread_manager = ThreadManager([ResultHandlerThread(dispatcher=dispatcher)])

    def start_processes(self):
        self.thread_manager.start_threads()
        self.proc_manager.start_processes()

    def send_startup_message(self):
        """Send welcome message after bot launch."""
        self._log.info('Sending welcome message')
        self.send_message_all(f'{self.first_name} bot started, see /help for '
                              'available commands')

    def send_message_all(self, msg):
        """Send message to all defined user IDs in config.json."""
        for user_id in self.user_ids:
            self.send_message(user_id, msg)

    def reply_cam_photo(self, photo, update=None, caption=None,
                        reply_text=None,
                        fullpic_name=None, fullpic=False, reply_html=None,
                        from_watchdog=False):
        """Send received photo."""
        if from_watchdog:
            for uid in self.user_ids:
                self.send_document(chat_id=uid,
                                   document=photo,
                                   caption=caption,
                                   filename=PurePath(photo.name).name,
                                   timeout=SEND_TIMEOUT)
        else:
            if reply_text:
                update.message.reply_text(reply_text)
            elif reply_html:
                update.message.reply_html(reply_html)
            if fullpic:
                update.message.reply_document(document=photo,
                                              filename=fullpic_name,
                                              caption=caption)
            else:
                update.message.reply_photo(photo=photo, caption=caption)

