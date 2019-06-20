"""Home Camera Module."""

import logging
from datetime import datetime
from io import BytesIO

from PIL import Image

from camerabot.alarm import Alarm
from camerabot.api import API
from camerabot.constants import IMG_SIZE, IMG_FORMAT, IMG_QUALITY, SWITCH_MAP
from camerabot.exceptions import HomeCamError, APIError
from camerabot.livestream import YouTubeStream


class HomeCam:

    """Camera class."""

    def __init__(self, conf):
        self._log = logging.getLogger(self.__class__.__name__)
        self.conf = conf
        self.description = conf.description
        self._log.debug('Initializing {0}'.format(self.description))
        self._api = API(conf=conf.api)
        self.snapshots_taken = 0
        self.alarm = Alarm(conf=conf.alert)
        self.stream_yt = YouTubeStream(conf=conf.live_stream.youtube,
                                       api_conf=conf.api)

    def __repr__(self):
        return '<HomeCam desc="{0}">'.format(self.description)

    def take_snapshot(self, resize=False):
        """Take and return full or resized snapshot from the camera."""
        self._log.debug('Taking snapshot from {0}'.format(self.description))
        try:
            res = self._api.take_snapshot()
            snapshot_timestamp = int(datetime.now().timestamp())
            self.snapshots_taken += 1
        except APIError:
            err_msg = 'Failed to take snapshot from {0}'.format(self.description)
            self._log.error(err_msg)
            raise HomeCamError(err_msg)

        try:
            snapshot = self._resize_snapshot(res.raw) if resize else res.raw
        except Exception:
            err_msg = 'Failed to resize snapshot taken from {0}'.format(
                self.description)
            self._log.exception(err_msg)
            raise HomeCamError(err_msg)
        return snapshot, snapshot_timestamp

    def get_alert_stream(self):
        try:
            return self._api.get_alert_stream()
        except APIError:
            err_msg = 'Failed to get Alert Stream'
            self._log.error(err_msg)
            raise HomeCamError(err_msg)

    def trigger_switch(self, enable, _type):
        """Trigger switch."""
        name = SWITCH_MAP[_type]['name']
        self._log.debug('{0} {1}'.format(
            'Enabling' if enable else 'Disabling', name))
        try:
            msg = self._api.switch(enable=enable, _type=_type)
        except APIError:
            err_msg = '{0} Switch encountered an error'.format(name)
            self._log.error(err_msg)
            raise HomeCamError(err_msg)
        return msg

    def _resize_snapshot(self, raw_snapshot):
        """Return resized JPEG snapshot."""
        snapshot = Image.open(raw_snapshot)
        resized_snapshot = BytesIO()

        snapshot.resize(IMG_SIZE, Image.ANTIALIAS)
        snapshot.save(resized_snapshot, IMG_FORMAT, quality=IMG_QUALITY)
        resized_snapshot.seek(0)

        self._log.debug("Raw snapshot: {0}, {1}, {2}".format(snapshot.format,
                                                             snapshot.mode,
                                                             snapshot.size))
        self._log.debug("Resized snapshot: {0}".format(IMG_SIZE))
        return resized_snapshot
