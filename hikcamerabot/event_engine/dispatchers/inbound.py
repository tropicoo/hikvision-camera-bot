"""Event dispatcher module."""

from hikcamerabot.enums import Event
from hikcamerabot.event_engine.dispatchers.abstract import AbstractDispatcher
from hikcamerabot.event_engine.events.abstract import BaseInboundEvent
from hikcamerabot.event_engine.handlers.inbound import (
    TaskAlarmConf,
    TaskDetectionConf,
    TaskIrcutFilterConf,
    TaskRecordVideoGif,
    TaskStreamConf,
    TaskTakeSnapshot,
)


class InboundEventDispatcher(AbstractDispatcher):
    """Inbound Event Dispatcher Class."""

    DISPATCH = {
        Event.CONFIGURE_ALARM: TaskAlarmConf,
        Event.CONFIGURE_DETECTION: TaskDetectionConf,
        Event.CONFIGURE_IRCUT_FILTER: TaskIrcutFilterConf,
        Event.STREAM: TaskStreamConf,
        Event.TAKE_SNAPSHOT: TaskTakeSnapshot,
        Event.RECORD_VIDEOGIF: TaskRecordVideoGif,
    }

    async def dispatch(self, event: BaseInboundEvent) -> None:
        """Dispatch inbound event to appropriate handler."""
        self._log.debug('Inbound event for %s: %s', event.cam.id, event)
        await self._dispatch[event.event].handle(event)
