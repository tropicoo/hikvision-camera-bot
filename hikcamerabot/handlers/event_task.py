"""Task event s module."""

import abc
import logging
from typing import TYPE_CHECKING

from pyrogram.types import Message

from hikcamerabot.clients.hikvision.constants import IrcutFilterType
from hikcamerabot.constants import (
    Alarm, DETECTION_SWITCH_MAP, Detection, Event, ServiceType,
)
from hikcamerabot.exceptions import ServiceRuntimeError
from hikcamerabot.utils.utils import make_bold

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam
    from hikcamerabot.camerabot import CameraBot


class AbstractTaskEvent(metaclass=abc.ABCMeta):

    def __init__(self, bot: 'CameraBot') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._bot = bot

    async def handle(self, event: dict) -> None:
        return await self._handle(event)

    @abc.abstractmethod
    async def _handle(self, event: dict) -> None:
        pass


class TaskTakeSnapshot(AbstractTaskEvent):

    async def _handle(self, event: dict) -> None:
        cam: 'HikvisionCam' = event['cam']
        img, create_ts = await cam.take_snapshot(resize=event['params']['resize'])
        event.update({'img': img,
                      'taken_count': cam.snapshots_taken,
                      'create_ts': create_ts})
        await self._bot.result_dispatcher.dispatch(event)


class TaskRecordVideoGif(AbstractTaskEvent):

    async def _handle(self, event: dict) -> None:
        message: Message = event['message']
        cam: 'HikvisionCam' = event['cam']
        await cam.start_videogif_record(context=message)
        record_time: int = cam.conf.alert.video_gif.record_time
        text = f'Recording video gif for {record_time} seconds'
        result_event = {'event': Event.SEND_TEXT, 'message': message,
                        'text': make_bold(text), 'parse_mode': 'HTML'}
        await self._bot.result_dispatcher.dispatch(result_event)


class TaskDetectionConf(AbstractTaskEvent):

    async def _handle(self, event: dict) -> None:
        cam: 'HikvisionCam' = event['cam']
        trigger: Detection = event['name']
        name = DETECTION_SWITCH_MAP[trigger]['name'].value
        enable: bool = event['params']['switch']

        self._log.info('%s camera\'s %s has been requested',
                       'Enabling' if enable else 'Disabling', name)
        event['text'] = await cam.services.alarm.trigger_switch(enable, trigger)
        await self._bot.result_dispatcher.dispatch(event)


class TaskAlarmConf(AbstractTaskEvent):

    async def _handle(self, event: dict) -> None:
        cam: 'HikvisionCam' = event['cam']
        service_type: ServiceType = event['service_type']
        service_name: Alarm = event['name']
        enable: bool = event['params']['switch']
        try:
            if enable:
                await cam.service_manager.start(service_type, service_name)
            else:
                await cam.service_manager.stop(service_type, service_name)
        except ServiceRuntimeError as err:
            event['text'] = str(err)
        await self._bot.result_dispatcher.dispatch(event)


class TaskStreamConf(AbstractTaskEvent):

    async def _handle(self, event: dict) -> None:
        self._log.info('Starting stream')
        cam: 'HikvisionCam' = event['cam']
        event_type: Event = event['event']
        service_type: ServiceType = event['service_type']
        service_name: Detection = event['name']
        enable: bool = event['params']['switch']
        try:
            if enable:
                await cam.service_manager.start(service_type, service_name)
            else:
                await cam.service_manager.stop(service_type, service_name)
        except ServiceRuntimeError as err:
            event['text'] = str(err)
        await self._bot.result_dispatcher.dispatch(event)


class TaskIrcutFilterConf(AbstractTaskEvent):
    async def _handle(self, event: dict) -> None:
        cam: 'HikvisionCam' = event['cam']
        filter_type: IrcutFilterType = event['params']['filter_type']
        await cam.set_ircut_filter(filter_type=filter_type)
        result_event = {'event': Event.SEND_TEXT, 'message': event['message'],
                        'text': make_bold('OK'), 'parse_mode': 'HTML'}
        await self._bot.result_dispatcher.dispatch(result_event)
