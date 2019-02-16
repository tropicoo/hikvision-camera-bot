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

        alert_enabled = cam_data['motion_detection']['alert']['enabled']
        if alert_enabled:
            self.alert_on.set()
        self._alert_delay = cam_data['motion_detection']['alert']['delay']
        self.alert_fullpic = cam_data['motion_detection']['alert']['fullpic']
        self.alert_count = 0

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
                                             'enabled.</b>')
        elif not enable and not self.alert_on.is_set():
            raise HomeCamAlertAlreadyOffError('<b>Alert Mode already '
                                              'disabled.</b>')

        resqueue = Queue()
        if not enable:
            self.alert_on.clear()
        else:
            self.alert_on.set()
            thread = Thread(target=self._alert_listener, args=(resqueue,))
            thread.start()
        return resqueue

    def _alert_listener(self, resqueue):
        while self.alert_on.is_set():
            wait_before = 0
            stream = self._api.get_alert_stream()
            for chunk in stream.iter_lines(chunk_size=1024):
                if not self.alert_on.is_set():
                    break
                while wait_before > int(time.time()):
                    continue
                if chunk and chunk.startswith(b'<eventType>VMD<'):
                    pic, ts = self.take_snapshot(resize=False if
                                                 self.alert_fullpic else True)
                    resqueue.put((pic, ts))
                    self.alert_count += 1
                    wait_before = int(time.time()) + self._alert_delay

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
