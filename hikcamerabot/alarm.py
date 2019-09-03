"""Alarm module."""

from queue import Queue
from threading import Event

from hikcamerabot.constants import SWITCH_MAP, ALARM_TRIGGERS, ALARMS
from hikcamerabot.exceptions import HikvisionCamError, APIError
from hikcamerabot.service import BaseService


class AlarmService(BaseService):
    """Alarm Service class."""

    def __init__(self, conf, api):
        super().__init__()
        self._conf = conf
        self._api = api
        self.alert_queue = Queue()
        self.alert_delay = conf.delay
        self.alert_count = 0
        self._started = Event()
        self.type = self.name = ALARMS.SERVICE_TYPE

    def is_started(self):
        """Check if alarm is enabled."""
        return self._started.is_set()

    def is_enabled_in_conf(self):
        """Check if any alarm trigger is enabled in conf."""
        for trigger in ALARM_TRIGGERS:
            if self._conf[trigger].enabled:
                return True
        return False

    def start(self):
        """Enable alarm."""
        if self.is_started():
            raise HikvisionCamError('Alarm alert mode already started')
        for _type in ALARM_TRIGGERS:
            if self._conf[_type].enabled:
                self.trigger_switch(enable=True, _type=_type)
        self._started.set()

    def stop(self):
        """Disable alarm."""
        if not self.is_started():
            raise HikvisionCamError('Alarm alert mode already stopped')
        self._started.clear()

    def get_alert_stream(self):
        """Get Alarm stream from Hikvision Camera."""
        try:
            return self._api.get_alert_stream()
        except APIError:
            err_msg = 'Failed to get Alert Stream'
            self._log.error(err_msg)
            raise HikvisionCamError(err_msg)

    def trigger_switch(self, enable, _type):
        """Trigger switch."""
        name = SWITCH_MAP[_type]['name']
        self._log.debug('%s %s', 'Enabling' if enable else 'Disabling', name)
        try:
            msg = self._api.switch(enable=enable, _type=_type)
        except APIError:
            err_msg = '{0} Switch encountered an error'.format(name)
            self._log.error(err_msg)
            raise HikvisionCamError(err_msg)
        return msg
