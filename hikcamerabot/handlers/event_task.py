"""Task event s module."""

import abc
import logging

from hikcamerabot.constants import DETECTION_SWITCH_MAP
from hikcamerabot.exceptions import ServiceRuntimeError


class AbstractTaskEvent(metaclass=abc.ABCMeta):

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)

    async def handle(self, data: dict) -> None:
        return await self._handle(data)

    @abc.abstractmethod
    async def _handle(self, data: dict) -> None:
        pass


class TaskTakeSnapshot(AbstractTaskEvent):

    async def _handle(self, data: dict) -> None:
        cam = data['cam']
        img, create_ts = await cam.take_snapshot(resize=data['params']['resize'])
        data.update({'img': img,
                     'taken_count': cam.snapshots_taken,
                     'create_ts': create_ts})
        await cam.bot.result_dispatcher.dispatch(data)


class TaskDetectionConf(AbstractTaskEvent):

    async def _handle(self, data: dict) -> None:
        cam = data['cam']
        trigger = data['name']
        name = DETECTION_SWITCH_MAP[trigger]['name']
        enable = data['params']['switch']

        self._log.info('%s camera\'s %s has been requested',
                       'Enabling' if enable else 'Disabling', name)
        data['msg'] = await cam.alarm.trigger_switch(enable, trigger)
        await cam.bot.result_dispatcher.dispatch(data)


class TaskAlarmConf(AbstractTaskEvent):

    async def _handle(self, data: dict) -> None:
        cam = data['cam']
        service_type = service_name = data['name']
        enable = data['params']['switch']
        try:
            if enable:
                await cam.service_manager.start(service_type, service_name)
            else:
                await cam.service_manager.stop(service_type, service_name)
        except ServiceRuntimeError as err:
            data['msg'] = str(err)
        await cam.bot.result_dispatcher.dispatch(data)


class TaskStreamConf(AbstractTaskEvent):

    async def _handle(self, data: dict) -> None:
        self._log.info('Starting YouTube stream')
        cam = data['cam']
        service_type = data['event']
        service_name = data['name']
        enable = data['params']['switch']
        try:
            if enable:
                await cam.service_manager.start(service_type, service_name)
            else:
                await cam.service_manager.stop(service_type, service_name)
        except ServiceRuntimeError as err:
            data['msg'] = str(err)
        await cam.bot.result_dispatcher.dispatch(data)
