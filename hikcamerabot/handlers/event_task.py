"""Task event s module."""

import abc
import logging

from aiogram.types import Message

from hikcamerabot.constants import DETECTION_SWITCH_MAP
from hikcamerabot.exceptions import ServiceRuntimeError


class AbstractTaskEvent(metaclass=abc.ABCMeta):

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)

    async def handle(self, event: dict) -> None:
        return await self._handle(event)

    @abc.abstractmethod
    async def _handle(self, event: dict) -> None:
        pass


class TaskTakeSnapshot(AbstractTaskEvent):

    async def _handle(self, event: dict) -> None:
        cam = event['cam']
        img, create_ts = await cam.take_snapshot(resize=event['params']['resize'])
        event.update({'img': img,
                      'taken_count': cam.snapshots_taken,
                      'create_ts': create_ts})
        await cam.bot.result_dispatcher.dispatch(event)


class TaskRecordVideoGif(AbstractTaskEvent):

    async def _handle(self, event: dict) -> None:
        message: Message = event['message']
        cam = event['cam']
        cam.video_manager.start_rec(context=message)
        record_time = cam.conf.alert.video_gif.record_time
        await message.answer(
            f'Recording video gif for {record_time} seconds')


class TaskDetectionConf(AbstractTaskEvent):

    async def _handle(self, event: dict) -> None:
        cam = event['cam']
        trigger = event['name']
        name = DETECTION_SWITCH_MAP[trigger]['name']
        enable = event['params']['switch']

        self._log.info('%s camera\'s %s has been requested',
                       'Enabling' if enable else 'Disabling', name)
        event['msg'] = await cam.alarm.trigger_switch(enable, trigger)
        await cam.bot.result_dispatcher.dispatch(event)


class TaskAlarmConf(AbstractTaskEvent):

    async def _handle(self, event: dict) -> None:
        cam = event['cam']
        service_type = service_name = event['name']
        enable = event['params']['switch']
        try:
            if enable:
                await cam.service_manager.start(service_type, service_name)
            else:
                await cam.service_manager.stop(service_type, service_name)
        except ServiceRuntimeError as err:
            event['msg'] = str(err)
        await cam.bot.result_dispatcher.dispatch(event)


class TaskStreamConf(AbstractTaskEvent):

    async def _handle(self, event: dict) -> None:
        self._log.info('Starting YouTube stream')
        cam = event['cam']
        service_type = event['event']
        service_name = event['name']
        enable = event['params']['switch']
        try:
            if enable:
                await cam.service_manager.start(service_type, service_name)
            else:
                await cam.service_manager.stop(service_type, service_name)
        except ServiceRuntimeError as err:
            event['msg'] = str(err)
        await cam.bot.result_dispatcher.dispatch(event)
