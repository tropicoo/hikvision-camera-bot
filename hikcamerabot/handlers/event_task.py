"""Task event handlers module."""

import abc
import logging

from hikcamerabot.constants import DETECTION_SWITCH_MAP, Events
from hikcamerabot.exceptions import ServiceRuntimeError
from hikcamerabot.services.threads import (ServiceStreamerThread,
                                           ServiceAlarmPusherThread)


class BaseTaskEventHandler(metaclass=abc.ABCMeta):

    def __init__(self, camera):
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam = camera

    def __call__(self, data):
        return self._handle(data)

    @abc.abstractmethod
    def _handle(self, data):
        pass


class TakeSnapshotHandler(BaseTaskEventHandler):

    def _handle(self, data):
        img, create_ts = self._cam.take_snapshot(
            resize=data['event'] == Events.TAKE_SNAPSHOT)

        data.update({'img': img,
                     'taken_count': self._cam.snapshots_taken,
                     'create_ts': create_ts})
        return data


class DetectionConfHandler(BaseTaskEventHandler):

    def _handle(self, data):
        key_name = data['name']
        name = DETECTION_SWITCH_MAP[key_name]['name']
        switch = data['params']['switch']

        self._log.info('%s camera\'s %s has been requested',
                       'Enabling' if switch else 'Disabling', name)
        data['msg'] = self._cam.alarm.trigger_switch(enable=switch,
                                                     key=key_name)
        return data


class AlarmConfHandler(BaseTaskEventHandler):

    def _handle(self, data):
        service_type = service_name = data['name']
        switch = data['params']['switch']
        # TODO: Code dup.
        try:
            if switch:
                self._cam.service_manager.start_service(service_type,
                                                        service_name)
                ServiceAlarmPusherThread(cam=self._cam,
                                         service_name=service_name).start()
            else:
                self._cam.service_manager.stop_service(service_type,
                                                       service_name)
        except ServiceRuntimeError as err:
            data['msg'] = str(err)
        return data


class StreamConfHandler(BaseTaskEventHandler):

    def _handle(self, data):
        self._log.info('Starting YouTube stream')
        service_type = data['event']
        service_name = data['name']
        switch = data['params']['switch']
        # TODO: Code dup.
        try:
            if switch:
                self._cam.service_manager.start_service(service_type,
                                                        service_name)
                ServiceStreamerThread(cam=self._cam,
                                      service_name=service_name).start()
            else:
                self._cam.service_manager.stop_service(service_type,
                                                       service_name)
        except ServiceRuntimeError as err:
            data['msg'] = str(err)
        return data
