"""Camera Services Module."""

import abc
import logging
import re
import time

from collections import defaultdict
from datetime import datetime
from threading import Thread

from telegram import ParseMode

from camerabot.constants import (SEND_TIMEOUT, SWITCH_MAP, DETECTION_REGEX,
                                 STREAMS, ALARMS)
from camerabot.exceptions import HikvisionCamError, CameraBotError


class BaseService(metaclass=abc.ABCMeta):
    """Base Service class."""

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        self._cls_name = self.__class__.__name__

        # e.g. alarm, stream (are used from constants.py module)
        self.type = None

    def __str__(self):
        return self._cls_name

    @abc.abstractmethod
    def start(self):
        pass

    @abc.abstractmethod
    def stop(self):
        pass

    @abc.abstractmethod
    def is_started(self):
        pass

    @abc.abstractmethod
    def is_enabled_in_conf(self):
        pass


class ServiceController:
    """Service Controller class."""

    def __init__(self):
        # service type as key e.g. {'stream': {'youtube': <instance>}}
        self._log = logging.getLogger(self.__class__.__name__)
        self._services = defaultdict(dict)

    def __repr__(self):
        return '<Registered services: {0}>'.format(self._services)

    def register_services(self, service_instances):
        """Register service instances.
        One instance or iterable object.
        """
        try:
            iterator = iter(service_instances)
            for obj in iterator:
                self._services[obj.type][obj.name] = obj
        except TypeError:
            self._services[service_instances.type][service_instances.name] = \
                service_instances

    def unregister_service(self, service_instance):
        self._services[service_instance.type].pop(service_instance.name, None)

    def start_services(self, enabled_in_conf=False):
        for service_type_dict in self._services.values():
            for service in service_type_dict.values():
                if enabled_in_conf:
                    if service.is_enabled_in_conf():
                        service.start()
                    else:
                        self._log.info('Do not starting service "%s" - '
                                       'disabled by default', service)
                else:
                    service.start()

    def stop_services(self):
        for service_type_dict in self._services.values():
            for service in service_type_dict.values():
                try:
                    service.stop()
                except HikvisionCamError as err:
                    self._log.warning('Warning while stopping service "%s": '
                                      '%s', service.name, err)

    def get_service(self, service_type, service_name):
        return self._services[service_type][service_name]

    def get_services(self):
        services = []
        for service_type_dict in self._services.values():
            services.extend(service_type_dict.values())
        return services

    def get_count(self, stream_type=None):
        try:
            return len(self._services[stream_type])
        except KeyError:
            count = 0
            for service_names_dict in self._services.values():
                count += len(service_names_dict)
            return count

    def get_count_per_type(self):
        return {_type: len(val) for _type, val in self._services.items()}


class ServiceThread(Thread, metaclass=abc.ABCMeta):
    type = None

    def __init__(self, bot, cam_id, cam, update, log, service, service_name, name):
        super().__init__(name=name)
        self._log = log
        self._bot = bot
        self._service = service
        self._service_name = service_name
        self._cam_id = cam_id
        self._cam = cam
        self._update = update

        if self._service and self._service_name:
            raise HikvisionCamError('Provide service instance or service name, '
                                    'not both')
        if self._service_name:
            self._service = self._cam.service_controller.get_service(self.type,
                                                                     self._service_name)

    @abc.abstractmethod
    def run(self):
        pass


class ServiceAlarmPusherThread(ServiceThread):
    """Alarm Pusher Service Class."""

    type = ALARMS.SERVICE_TYPE

    def __init__(self, bot, cam_id, cam, update, log, service, service_name):
        super().__init__(bot, cam_id, cam, update, log, service, service_name,
                         name=self.__class__.__name__)

    def run(self):
        while self._service.is_started():
            self._log.debug('Starting alert pusher thread for camera: "%s"',
                            self._cam.description)
            wait_before = 0
            stream = self._service.get_alert_stream()
            for chunk in stream.iter_lines(chunk_size=1024):
                if not self._service.is_started():
                    self._log.info('Exiting alert pusher thread for %s',
                                   self._cam.description)
                    break

                if wait_before > int(time.time()):
                    continue
                if chunk:
                    try:
                        detection_key = self.chunk_belongs_to_detection(chunk)
                    except CameraBotError as err:
                        self._bot.send_message_all(err)
                        continue
                    if detection_key:
                        photo, ts = self._cam.take_snapshot(resize=
                        not self._cam.conf.alert[detection_key].fullpic)
                        self._service.alert_count += 1
                        wait_before = int(
                            time.time()) + self._service.alert_delay
                        self._send_alert(photo, ts, detection_key)

    def chunk_belongs_to_detection(self, chunk):
        match = re.match(DETECTION_REGEX, chunk.decode())
        if match:
            event_name = match.group(2)
            for key, inner_map in SWITCH_MAP.items():
                if inner_map['event_name'] == event_name:
                    return key
            else:
                raise CameraBotError('Detected event {0} but don\'t know what '
                                     'to do'.format(event_name))
        return None

    def _send_alert(self, photo, ts, detection_key):
        caption = 'Alert snapshot taken on {0:%a %b %d %H:%M:%S %Y} (alert ' \
                  '#{1})\n/list cameras'.format(datetime.fromtimestamp(ts),
                                                self._service.alert_count)
        reply_html = '<b>{0} Alert</b>\nSending snapshot ' \
                     'from {1}'.format(self._cam.description,
                                       SWITCH_MAP[detection_key]['name'])

        for uid in self._bot.user_ids:
            self._bot.send_message(chat_id=uid, text=reply_html,
                                   parse_mode=ParseMode.HTML)
            if self._cam.conf.alert[detection_key].fullpic:
                name = 'Full_alert_snapshot_{:%a_%b_%d_%H.%M.%S_%Y}.jpg'.format(
                    datetime.fromtimestamp(ts))
                self._bot.send_document(chat_id=uid, document=photo,
                                        caption=caption,
                                        filename=name,
                                        timeout=SEND_TIMEOUT)
            else:
                self._bot.send_photo(chat_id=uid, photo=photo,
                                     caption=caption,
                                     timeout=SEND_TIMEOUT)


class ServiceStreamerThread(ServiceThread):
    type = STREAMS.SERVICE_TYPE

    def __init__(self, bot, cam_id, cam, update, log, service, service_name):
        super().__init__(bot, cam_id, cam, update, log, service, service_name,
                         name=self.__class__.name)
        self._exit_msg = 'Exiting {0} stream thread for "{1}"'.format(
                    self._service.name, self._cam.description)

    def run(self):
        self._log.debug('Starting %s stream thread for "%s"',
                        self._service.name, self._cam.description)
        if not self._service:
            raise HikvisionCamError(
                'No such self._service: {0}'.format(self._service_name))

        def should_exit():
            if not self._service.is_started():
                self._log.info(self._exit_msg)
                self._bot.send_message_all(self._exit_msg)
                return True
            return False

        try:
            while self._service.is_started():
                while not self._service.need_restart() and self._service.is_alive():
                    if should_exit():
                        break
                    self._log.info('FFMPEG: %s', self._service.get_stdout())
                else:
                    if should_exit():
                        break
                    self._log.info('Restarting %s stream', self._service.name)
                    self._service.restart()
        except HikvisionCamError as err:
            if self._update:
                self._update.message.reply_text(err)
            else:
                for uid in self._bot.user_ids:
                    self._bot.send_message(chat_id=uid, text=err)
        except Exception as err:
            err_msg = 'Unknown error in {0} stream thread'.format(self._service.name)
            self._log.exception(err_msg)
            err_msg = '{0}: {1}'.format(err_msg, err)
            if self._update:
                self._update.message.reply_text(err_msg)
            else:
                for uid in self._bot.user_ids:
                    self._bot.send_message(chat_id=uid, text=err_msg)
        self._log.debug(self._exit_msg)
