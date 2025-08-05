"""EventType dispatcher module."""

from typing import ClassVar

from hikcamerabot.enums import EventType
from hikcamerabot.event_engine.dispatchers.abstract import AbstractDispatcher
from hikcamerabot.event_engine.events.abstract import BaseInboundEvent
from hikcamerabot.event_engine.handlers.inbound import (
    AbstractTaskEvent,
    TaskAlarmConf,
    TaskDetectionConf,
    TaskIrcutFilterConf,
    TaskRecordVideoGif,
    TaskStreamConf,
    TaskTakeSnapshot,
)


class InboundEventDispatcher(AbstractDispatcher):
    """Inbound EventType Dispatcher Class."""

    DISPATCH: ClassVar[dict[EventType, type[AbstractTaskEvent]]] = {
        EventType.CONFIGURE_ALARM: TaskAlarmConf,
        EventType.CONFIGURE_DETECTION: TaskDetectionConf,
        EventType.CONFIGURE_IRCUT_FILTER: TaskIrcutFilterConf,
        EventType.STREAM: TaskStreamConf,
        EventType.TAKE_SNAPSHOT: TaskTakeSnapshot,
        EventType.RECORD_VIDEOGIF: TaskRecordVideoGif,
    }

    async def dispatch(self, event: BaseInboundEvent) -> None:
        """Dispatch inbound event to appropriate handler."""
        self._log.debug('Inbound event for %s: %s', event.cam.id, event)
        await self._dispatch[event.event].handle(event)
