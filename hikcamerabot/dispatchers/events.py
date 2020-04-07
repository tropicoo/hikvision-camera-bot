"""Event dispatchers module."""

import logging

from hikcamerabot.constants import Events
from hikcamerabot.decorators import event_error_handler, result_error_handler
from hikcamerabot.handlers.event_result import (
    ResultAlarmConfHandler,
    ResultAlertMessageHandler,
    ResultAlertSnapshotHandler,
    ResultAlertVideoHandler,
    ResultDetectionConfHandler,
    ResultStreamConfHandler,
    ResultStreamMessageHandler,
    ResultTakeSnapshotHandler)
from hikcamerabot.handlers.event_task import (TakeSnapshotHandler,
                                              AlarmConfHandler,
                                              DetectionConfHandler,
                                              StreamConfHandler)


class EventDispatcher:
    """Event Dispatcher Class."""

    DISPATCH = {Events.CONFIGURE_ALARM: AlarmConfHandler,
                Events.CONFIGURE_DETECTION: DetectionConfHandler,
                Events.STREAM: StreamConfHandler,
                Events.TAKE_SNAPSHOT: TakeSnapshotHandler}

    def __init__(self, camera):
        self._log = logging.getLogger(self.__class__.__name__)
        self._dispatch = {}
        for event, handler in self.DISPATCH.items():
            self._dispatch[event] = handler(camera)

    @event_error_handler
    def handle(self, data):
        """Dispatch data to appropriate handler."""
        self._log.debug('Received data: %s', data)
        return self._dispatch[data['event']](data)


class ResultDispatcher:
    """Result Dispatcher Class."""

    DISPATCH = {Events.ALERT_MSG: ResultAlertMessageHandler,
                Events.ALERT_SNAPSHOT: ResultAlertSnapshotHandler,
                Events.ALERT_VIDEO: ResultAlertVideoHandler,
                Events.CONFIGURE_ALARM: ResultAlarmConfHandler,
                Events.CONFIGURE_DETECTION: ResultDetectionConfHandler,
                Events.STREAM: ResultStreamConfHandler,
                Events.STREAM_MSG: ResultStreamMessageHandler,
                Events.TAKE_SNAPSHOT: ResultTakeSnapshotHandler}

    def __init__(self, bot, cam_registry):
        self._log = logging.getLogger(self.__class__.__name__)
        self._dispatch = {}
        for event, handler in self.DISPATCH.items():
            self._dispatch[event] = handler(bot, cam_registry)

    @result_error_handler
    def handle(self, data):
        """Dispatch data to appropriate handler."""
        self._log.debug('Received data: %s', data)
        self._dispatch[data['event']](data)
