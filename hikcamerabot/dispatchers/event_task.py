"""Event dispatcher module."""

from hikcamerabot.constants import Event
from hikcamerabot.dispatchers.abstract import AbstractDispatcher
from hikcamerabot.handlers.event_task import (
    TaskAlarmConf,
    TaskDetectionConf,
    TaskStreamConf,
    TaskTakeSnapshot,
)


class EventDispatcher(AbstractDispatcher):
    """Event Dispatcher Class."""

    DISPATCH = {
        Event.CONFIGURE_ALARM: TaskAlarmConf,
        Event.CONFIGURE_DETECTION: TaskDetectionConf,
        Event.STREAM: TaskStreamConf,
        Event.TAKE_SNAPSHOT: TaskTakeSnapshot,
    }

    async def dispatch(self, data: dict) -> None:
        """Dispatch data to appropriate handler."""
        self._log.debug('Incoming event data for %s: %s', data['cam'].id, data)
        await self._dispatch[data['event']].handle(data)
