import logging

from hikcamerabot.commons import CommonThread
from hikcamerabot.config import get_result_queue
from hikcamerabot.constants import Events
from hikcamerabot.decorators import event_error_handler, result_error_handler
from hikcamerabot.handlers.result_event_handlers import (
    ResultAlarmConfHandler,
    ResultAlertSnapshotHandler,
    ResultDetectionConfHandler,
    ResultStreamConfHandler,
    ResultTakeSnapshotHandler,
    ResultAlertVideoHandler,
    ResultAlertMessageHandler,
    ResultStreamMessageHandler)
from hikcamerabot.handlers.task_event_handlers import (TakeSnapshotHandler,
                                                       AlarmConfHandler,
                                                       DetectionConfHandler,
                                                       StreamConfHandler)
from hikcamerabot.utils import shallow_sleep

EVENT_DISPATCH = {Events.TAKE_SNAPSHOT: TakeSnapshotHandler,
                  Events.CONFIGURE_DETECTION: DetectionConfHandler,
                  Events.STREAM: StreamConfHandler,
                  Events.CONFIGURE_ALARM: AlarmConfHandler}

RESULT_DISPATCH = {Events.TAKE_SNAPSHOT: ResultTakeSnapshotHandler,
                   Events.CONFIGURE_DETECTION: ResultDetectionConfHandler,
                   Events.STREAM: ResultStreamConfHandler,
                   Events.CONFIGURE_ALARM: ResultAlarmConfHandler,
                   Events.ALERT_SNAPSHOT: ResultAlertSnapshotHandler,
                   Events.ALERT_VIDEO: ResultAlertVideoHandler,
                   Events.ALERT_MSG: ResultAlertMessageHandler,
                   Events.STREAM_MSG: ResultStreamMessageHandler}


class EventDispatcher:
    """Event Dispatcher Class."""

    def __init__(self, camera):
        self._log = logging.getLogger(self.__class__.__name__)
        self._dispatch_map = {}
        for event, handler in EVENT_DISPATCH.items():
            self._dispatch_map[event] = handler(camera)

    @event_error_handler
    def handle(self, data):
        self._log.debug('Received data: %s', data)
        return self._dispatch_map[data['event']](data)


class ResultDispatcher:
    """Result Dispatcher Class."""

    def __init__(self, bot, cam_registry):
        self._log = logging.getLogger(self.__class__.__name__)
        self._dispatch_map = {}
        for event, handler in RESULT_DISPATCH.items():
            self._dispatch_map[event] = handler(bot, cam_registry)

    @result_error_handler
    def handle(self, data):
        self._log.debug('Received data: %s', data)
        self._dispatch_map[data['event']](data)


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
