"""Result dispatcher module."""

from typing import ClassVar

from hikcamerabot.enums import EventType
from hikcamerabot.event_engine.dispatchers.abstract import AbstractDispatcher
from hikcamerabot.event_engine.events.abstract import BaseOutboundEvent
from hikcamerabot.event_engine.handlers.outbound import (
    AbstractResultEventHandler,
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

    DISPATCH: ClassVar[dict[EventType, AbstractResultEventHandler]] = {
        EventType.ALERT_SNAPSHOT: ResultAlertSnapshotHandler,
        EventType.ALERT_VIDEO: ResultAlertVideoHandler,
        EventType.CONFIGURE_ALARM: ResultAlarmConfHandler,
        EventType.CONFIGURE_DETECTION: ResultDetectionConfHandler,
        EventType.SEND_TEXT: ResultSendTextHandler,
        EventType.STREAM: ResultStreamConfHandler,
        EventType.TAKE_SNAPSHOT: ResultTakeSnapshotHandler,
        EventType.RECORD_VIDEOGIF: ResultRecordVideoGifHandler,
    }

    async def dispatch(self, event: BaseOutboundEvent) -> None:
        """Dispatch outbound event to appropriate handler."""
        self._log.debug('Outbound event: %s', event)
        await self._dispatch[event.event].handle(event)
