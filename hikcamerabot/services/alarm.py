"""Alarm module."""

from queue import Queue
from threading import Event

from hikcamerabot.constants import DETECTION_SWITCH_MAP, ALARM_TRIGGERS, Alarms
from hikcamerabot.exceptions import APIError
from hikcamerabot.exceptions import ServiceRuntimeError
from hikcamerabot.services import BaseService


class AlarmService(BaseService):
    """Alarm Service Class."""

    def __init__(self, conf, api):
        super().__init__()
        self._conf = conf
        self._api = api
        self.alert_delay = conf.delay
        self.alert_count = 0
        self._started = Event()
        self.type = Alarms.SERVICE_TYPE
        self.name = Alarms.ALARM

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
            raise ServiceRuntimeError('Alarm alert mode already started')
        for _type in ALARM_TRIGGERS:
            if self._conf[_type].enabled:
                self.trigger_switch(enable=True, key=_type)
        self._started.set()

    def stop(self):
        """Disable alarm."""
        if not self.is_started():
            raise ServiceRuntimeError('Alarm alert mode already stopped')
        self._started.clear()

    def get_alert_stream(self):
        """Get Alarm stream from Hikvision Camera."""
        try:
            return self._api.get_alert_stream()
        except APIError:
            err_msg = 'Failed to get Alert Streams'
            self._log.error(err_msg)
            raise ServiceRuntimeError(err_msg)

    def trigger_switch(self, enable, key):
        """Trigger switch."""
        full_name = DETECTION_SWITCH_MAP[key]['name']
        self._log.debug('%s %s', 'Enabling' if enable else 'Disabling', full_name)
        try:
            msg = self._api.switch(enable=enable, key=key)
        except APIError:
            err_msg = f'{full_name} Switch encountered an error'
            self._log.error(err_msg)
            raise ServiceRuntimeError(err_msg)
        return msg
