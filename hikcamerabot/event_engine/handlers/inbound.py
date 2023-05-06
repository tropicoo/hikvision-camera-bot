"""Task event s module."""

import abc
import logging
from typing import TYPE_CHECKING, Optional

from hikcamerabot.constants import DETECTION_SWITCH_MAP
from hikcamerabot.enums import Event
from hikcamerabot.event_engine.events.abstract import BaseInboundEvent
from hikcamerabot.event_engine.events.inbound import (
    AlertConfEvent,
    DetectionConfEvent,
    GetPicEvent,
    GetVideoEvent,
    IrcutConfEvent,
    StreamEvent,
)
from hikcamerabot.event_engine.events.outbound import (
    AlarmConfOutboundEvent,
    DetectionConfOutboundEvent,
    SendTextOutboundEvent,
    SnapshotOutboundEvent,
    StreamOutboundEvent,
)
from hikcamerabot.event_engine.queue import get_result_queue
from hikcamerabot.exceptions import ServiceRuntimeError
from hikcamerabot.utils.shared import bold

if TYPE_CHECKING:
    from hikcamerabot.camerabot import CameraBot


class AbstractTaskEvent(metaclass=abc.ABCMeta):
    def __init__(self, bot: 'CameraBot') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._bot = bot
        self._result_queue = get_result_queue()

    async def handle(self, event: BaseInboundEvent) -> None:
        return await self._handle(event)

    @abc.abstractmethod
    async def _handle(self, event: BaseInboundEvent) -> None:
        pass


class TaskTakeSnapshot(AbstractTaskEvent):
    async def _handle(self, event: GetPicEvent) -> None:
        channel: int = event.cam.conf.picture.on_demand.channel
        img, create_ts = await event.cam.take_snapshot(
            channel=channel, resize=event.resize
        )
        await self._result_queue.put(
            SnapshotOutboundEvent(
                event=event.event,
                img=img,
                create_ts=create_ts,
                taken_count=event.cam.snapshots_taken,
                resized=event.resize,
                message=event.message,
                cam=event.cam,
            )
        )


class TaskRecordVideoGif(AbstractTaskEvent):
    async def _handle(self, event: GetVideoEvent) -> None:
        await event.cam.start_videogif_record(
            message=event.message, rewind=event.rewind
        )


class TaskDetectionConf(AbstractTaskEvent):
    async def _handle(self, event: DetectionConfEvent) -> None:
        cam = event.cam
        trigger = event.type
        name = DETECTION_SWITCH_MAP[trigger]['name'].value
        state = event.state

        self._log.info(
            '%s camera\'s %s has been requested',
            'Enabling' if state else 'Disabling',
            name,
        )
        text = await cam.services.alarm.trigger_switch(trigger=trigger, state=state)
        await self._result_queue.put(
            DetectionConfOutboundEvent(
                event=event.event,
                type=event.type,
                state=state,
                cam=cam,
                message=event.message,
                text=text,
            )
        )


class TaskAlarmConf(AbstractTaskEvent):
    async def _handle(self, event: AlertConfEvent) -> None:
        cam = event.cam
        service_type = event.service_type
        service_name = event.service_name
        state = event.state
        text: Optional[str] = None
        try:
            if state:
                await cam.service_manager.start(service_type, service_name)
            else:
                await cam.service_manager.stop(service_type, service_name)
        except ServiceRuntimeError as err:
            text = str(err)

        await self._result_queue.put(
            AlarmConfOutboundEvent(
                event=event.event,
                service_type=service_type,
                service_name=service_name,
                state=event.state,
                cam=cam,
                message=event.message,
                text=text,
            )
        )


class TaskStreamConf(AbstractTaskEvent):
    async def _handle(self, event: StreamEvent) -> None:
        self._log.info('Starting stream')
        cam = event.cam
        service_type = event.service_type
        service_name = event.stream_type
        state = event.state
        text: Optional[str] = None
        try:
            if state:
                await cam.service_manager.start(service_type, service_name)
            else:
                await cam.service_manager.stop(service_type, service_name)
        except ServiceRuntimeError as err:
            text = str(err)

        await self._result_queue.put(
            StreamOutboundEvent(
                event=event.event,
                service_type=service_type,
                stream_type=event.stream_type,
                state=event.state,
                cam=cam,
                message=event.message,
                text=text,
            )
        )


class TaskIrcutFilterConf(AbstractTaskEvent):
    async def _handle(self, event: IrcutConfEvent) -> None:
        await event.cam.set_ircut_filter(filter_type=event.filter_type)
        await self._result_queue.put(
            SendTextOutboundEvent(
                event=Event.SEND_TEXT,
                message=event.message,
                text=bold(f'IrcutFilter set to "{event.filter_type.value}"'),
            )
        )
