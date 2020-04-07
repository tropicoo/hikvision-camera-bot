"""Camera Services Module."""

import abc
import logging
import re
import time
from threading import Thread

from hikcamerabot.constants import (DETECTION_SWITCH_MAP,
                                    DETECTION_REGEX,
                                    Streams, Alarms)
from hikcamerabot.exceptions import HikvisionCamError, CameraBotError
from hikcamerabot.managers.event import AlertEventManager, LivestreamEventManager


class BaseServiceThread(Thread, metaclass=abc.ABCMeta):
    """Base Service Thread Class."""

    type = None

    def __init__(self, cam, service, service_name, name, event_manager):
        super().__init__(name=name)
        self._log = logging.getLogger(self.__class__.__name__)
        self.service = service
        self._service_name = service_name
        self._cam = cam
        self._event_manager = event_manager

        if self.service and self._service_name:
            raise HikvisionCamError('Provide service instance or service name, '
                                    'not both')
        if self._service_name:
            self.service = self._cam.service_manager.get_service(
                self.type, self._service_name)

    @abc.abstractmethod
    def run(self):
        """Main service thread run."""
        pass


class ServiceAlarmPusherThread(BaseServiceThread):
    """Alarm Pusher Service Class."""

    type = Alarms.SERVICE_TYPE

    def __init__(self, cam, service=None, service_name=None):
        super().__init__(cam, service, service_name,
                         event_manager=AlertEventManager(),
                         name=self.__class__.__name__)

    def run(self):
        """Main service thread run."""
        while self.service.is_started():
            self._log.debug('Starting alert pusher thread for camera: "%s"',
                            self._cam.description)
            # Blocking
            self._process_chunks()

    def _process_chunks(self):
        """Process chunks received from Hikvision camera alert stream."""
        wait_before = 0
        stream = self.service.get_alert_stream()

        for chunk in stream.iter_lines():
            if not self.service.is_started():
                self._log.info('Exiting alert pusher thread for %s',
                               self._cam.description)
                break

            if int(time.time()) < wait_before or not chunk:
                continue

            try:
                detection_key = self._detect_chunk(chunk)
            except CameraBotError as err:
                self._event_manager.send_alert_msg(msg=str(err),
                                                   cam_id=self._cam.id)
                continue
            if detection_key:
                self.service.alert_count += 1
                self._log.debug('Detected chunk: %s', chunk)
                self._cam.video_manager.start_rec()
                try:
                    self._send_alert(detection_key)
                except Exception as err:
                    self._log.exception('Exception in thread %s: %s',
                                        self.__class__.__name__, err)
                wait_before = int(time.time()) + self.service.alert_delay

    def _detect_chunk(self, chunk):
        """Detect chunk in regard of `DETECTION_REGEX` string and return
        detection key.

        :Parameters:
            - `chunk`: byte string, one line from alert stream.
        """
        match = re.match(DETECTION_REGEX, chunk.decode(errors='ignore'))
        if not match:
            return None

        event_name = match.group(2)
        for key, inner_map in DETECTION_SWITCH_MAP.items():
            if inner_map['event_name'] == event_name:
                return key
        else:
            raise CameraBotError(f'Unknown alert stream event {event_name}')

    def _send_alert(self, detection_key):
        """Send alert to the user."""
        resize = not self._cam.conf.alert[detection_key].fullpic
        photo, ts = self._cam.take_snapshot(resize=resize)
        self._event_manager.send_alert_snapshot(
            img=photo,
            ts=ts,
            resized=resize,
            cam_id=self._cam.id,
            detection_key=detection_key,
            alert_count=self.service.alert_count)


class ServiceStreamerThread(BaseServiceThread):
    type = Streams.SERVICE_TYPE

    def __init__(self, cam, service=None, service_name=None):
        super().__init__(cam, service, service_name,
                         event_manager=LivestreamEventManager(),
                         name=self.__class__.name)
        self._exit_msg = f'Exiting {self.service.name} stream thread ' \
                         f'for "{self._cam.description}"'

    def _send_event_msg(self, msg):
        self._event_manager.send_msg(msg=msg, cam_id=self._cam.id)

    def run(self):
        self._log.debug('Starting %s stream thread for "%s"',
                        self.service.name, self._cam.description)
        if not self.service:
            raise HikvisionCamError(f'No such service: {self._service_name}')

        def should_exit():
            if not self.service.is_started():
                self._log.info(self._exit_msg)
                self._send_event_msg(self._exit_msg)
                return True
            return False

        try:
            while self.service.is_started():
                while not self.service.need_restart() and self.service.is_alive():
                    if should_exit():
                        break
                    self._log.info('FFMPEG: %s', self.service.get_stdout())
                else:
                    if should_exit():
                        break
                    self._log.info('Restarting %s stream', self.service.name)
                    self.service.restart()
        except HikvisionCamError as err:
            self._send_event_msg(str(err))
        except Exception as err:
            err_msg = f'Unknown error in {self.service.name} stream thread'
            self._log.exception(err_msg)
            self._send_event_msg(f'{err_msg}: {err}')
        self._log.debug(self._exit_msg)
