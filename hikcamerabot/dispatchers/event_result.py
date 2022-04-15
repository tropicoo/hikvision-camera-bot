"""Result dispatcher module."""

from hikcamerabot.constants import Event
from hikcamerabot.dispatchers.abstract import AbstractDispatcher
from hikcamerabot.handlers.event_result import (
    ResultAlarmConfHandler,
    ResultAlertSnapshotHandler,
    ResultAlertVideoHandler,
    ResultDetectionConfHandler,
    ResultRecordVideoGifHandler,
    ResultSendTextHandler,
    ResultStreamConfHandler,
    ResultTakeSnapshotHandler,
)


class ResultDispatcher(AbstractDispatcher):
    """Result Dispatcher Class."""

    DISPATCH = {
        Event.ALERT_SNAPSHOT: ResultAlertSnapshotHandler,
        Event.ALERT_VIDEO: ResultAlertVideoHandler,
        Event.CONFIGURE_ALARM: ResultAlarmConfHandler,
        Event.CONFIGURE_DETECTION: ResultDetectionConfHandler,
        Event.SEND_TEXT: ResultSendTextHandler,
        Event.STREAM: ResultStreamConfHandler,
        Event.TAKE_SNAPSHOT: ResultTakeSnapshotHandler,
        Event.RECORD_VIDEOGIF: ResultRecordVideoGifHandler,
    }

    async def dispatch(self, data: dict) -> None:
        """Dispatch data to appropriate handler."""
        self._log.debug('Result event data: %s', data)
        await self._dispatch[data['event']].handle(data)
