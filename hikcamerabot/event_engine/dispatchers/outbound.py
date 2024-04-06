"""Result dispatcher module."""

from hikcamerabot.enums import Event
from hikcamerabot.event_engine.dispatchers.abstract import AbstractDispatcher
from hikcamerabot.event_engine.events.abstract import BaseOutboundEvent
from hikcamerabot.event_engine.handlers.outbound import (
    ResultAlarmConfHandler,
    ResultAlertSnapshotHandler,
    ResultAlertVideoHandler,
    ResultDetectionConfHandler,
    ResultRecordVideoGifHandler,
    ResultSendTextHandler,
    ResultStreamConfHandler,
    ResultTakeSnapshotHandler,
)


class OutboundEventDispatcher(AbstractDispatcher):
    """Outbound (Result) Dispatcher Class."""

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

    async def dispatch(self, event: BaseOutboundEvent) -> None:
        """Dispatch outbound event to appropriate handler."""
        self._log.debug('Outbound event: %s', event)
        await self._dispatch[event.event].handle(event)
