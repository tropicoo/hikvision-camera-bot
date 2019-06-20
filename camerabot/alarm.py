"""Alarm module."""

from queue import Queue
from threading import Event

from camerabot.exceptions import HomeCamError


class Alarm:

    """Alarm class."""

    def __init__(self, conf):
        self._conf = conf
        self.alert_queue = Queue()
        self._alert_on = Event()

        if self._conf.motion_detection.enabled or \
                self._conf.line_crossing_detection.enabled:
            self.enable()

        self.alert_delay = conf.delay
        self.alert_count = 0

    def is_enabled(self):
        """Check if alarm is enabled."""
        return self._alert_on.is_set()

    def enable(self):
        """Enable alarm."""
        if self.is_enabled():
            raise HomeCamError('Alert Mode already enabled')
        self._alert_on.set()

    def disable(self):
        """Disable alarm."""
        if not self.is_enabled():
            raise HomeCamError('Alert Mode already disabled')
        self._alert_on.clear()
