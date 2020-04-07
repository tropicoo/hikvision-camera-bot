"""Common threads module."""

import logging
from threading import Thread

from hikcamerabot.config import get_result_queue
from hikcamerabot.utils import shallow_sleep


class CommonThread(Thread):
    def __init__(self):
        super().__init__()
        self._run_trigger = None

    def add_run_trigger(self, run_trigger):
        self._run_trigger = run_trigger


class ResultHandlerThread(CommonThread):
    """Result Handler Thread Class."""

    def __init__(self, dispatcher):
        super().__init__()
        self._log = logging.getLogger(self.__class__.__name__)
        self._queue_res = get_result_queue()
        self._dispatcher = dispatcher

    def run(self):
        """Run thread."""
        while self._run_trigger.is_set():
            while not self._queue_res.empty():
                data = self._queue_res.get()
                self._dispatcher.handle(data)
            shallow_sleep()
