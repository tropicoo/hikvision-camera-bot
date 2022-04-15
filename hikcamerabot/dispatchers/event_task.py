"""Event dispatcher module."""

from hikcamerabot.constants import Event
from hikcamerabot.dispatchers.abstract import AbstractDispatcher
from hikcamerabot.handlers.event_task import (
    TaskAlarmConf,
    TaskDetectionConf,
    TaskIrcutFilterConf,
    TaskRecordVideoGif,
    TaskStreamConf,
    TaskTakeSnapshot,
)


class EventDispatcher(AbstractDispatcher):
    """Event Dispatcher Class."""

    DISPATCH = {
        Event.CONFIGURE_ALARM: TaskAlarmConf,
        Event.CONFIGURE_DETECTION: TaskDetectionConf,
        Event.CONFIGURE_IRCUT_FILTER: TaskIrcutFilterConf,
        Event.STREAM: TaskStreamConf,
        Event.TAKE_SNAPSHOT: TaskTakeSnapshot,
        Event.RECORD_VIDEOGIF: TaskRecordVideoGif,
    }

    async def dispatch(self, data: dict) -> None:
        """Dispatch data to appropriate handler."""
        self._log.debug('Incoming event data for %s: %s', data['cam'].id, data)
        await self._dispatch[data['event']].handle(data)
