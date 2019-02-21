"""Home Camera Module"""

import logging
import time
from datetime import datetime
from io import BytesIO
from queue import Queue
from threading import Event, Thread

from PIL import Image

from camerabot.api import API
from camerabot.constants import (IMG_SIZE, IMG_FORMAT, IMG_QUALITY)
from camerabot.errors import (HomeCamError, HomeCamResizeSnapshotError,
                              HomeCamAlertAlreadyOnError,
                              HomeCamAlertAlreadyOffError)


class HomeCam:
    """Camera class."""

    def __init__(self, cam_data):
        self._log = logging.getLogger(self.__class__.__name__)
        self.description = cam_data['description']
        self._log.debug('Initializing {0}'.format(self.description))
        self._api = API(api_conf=cam_data['api'])
        self.snapshots_taken = 0
        self.alert_on = Event()

        self.alert_enabled = cam_data['motion_detection']['alert']['enabled']
        if self.alert_enabled:
            self.alert_on.set()
        self.alert_queue = Queue()

        self.alert_delay = cam_data['motion_detection']['alert']['delay']
        self.alert_fullpic = cam_data['motion_detection']['alert']['fullpic']
        self.alert_count = 0

    def __repr__(self):
        return '<HomeCam desc="{0}">'.format(self.description)

    def take_snapshot(self, resize=False):
        """Takes and returns full or resized snapshot from the camera."""
        self._log.debug('Taking snapshot from {0}'.format(self.description))
        try:
            res = self._api.take_snapshot()
            snapshot_timestamp = int(datetime.now().timestamp())
            self.snapshots_taken += 1
            snapshot = self._resize_snapshot(res.raw) if resize else res.raw
        except HomeCamResizeSnapshotError as err:
            raise HomeCamError(str(err)) from err
        except Exception as err:
            err_msg = 'Failed to take snapshot from {0}'.format(self.description)
            self._log.error(err_msg)
            raise HomeCamError(err_msg) from err
        return snapshot, snapshot_timestamp

    def alert(self, enable=True):
        if enable and self.alert_on.is_set():
            raise HomeCamAlertAlreadyOnError('<b>Alert Mode already '
                                             'enabled</b>')
        elif not enable and not self.alert_on.is_set():
            raise HomeCamAlertAlreadyOffError('<b>Alert Mode already '
                                              'disabled</b>')
        if enable:
            self.alert_on.set()
        else:
            self.alert_on.clear()

    def get_alert_stream(self):
        return self._api.get_alert_stream()

    def motion_detection_switch(self, enable=True):
        """Motion Detection Switch."""
        try:
            self._log.debug('{0} Motion Detection'.format('Enabling' if enable
                                                         else 'Disabling'))
            msg = self._api.motion_detection_switch(enable=enable)
        except Exception as err:
            err_msg = 'Motion Detection Switch encountered an error.'
            self._log.exception(err_msg)
            raise HomeCamError(err_msg) from err
        return msg

    def _resize_snapshot(self, raw_snapshot):
        """Returns resized JPEG snapshot."""
        try:
            snapshot = Image.open(raw_snapshot)
            resized_snapshot = BytesIO()

            snapshot.resize(IMG_SIZE, Image.ANTIALIAS)
            snapshot.save(resized_snapshot, IMG_FORMAT, quality=IMG_QUALITY)
            resized_snapshot.seek(0)

            self._log.debug("Raw snapshot: {0}, {1}, {2}".format(snapshot.format,
                                                                 snapshot.mode,
                                                                 snapshot.size))
            self._log.debug("Resized snapshot: {0}".format(IMG_SIZE))
        except Exception as err:
            err_msg = 'Failed to resize snapshot taken from {0}'.format(
                self.description)
            self._log.exception(err_msg)
            raise HomeCamResizeSnapshotError(err_msg) from err
        return resized_snapshot
