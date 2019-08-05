"""Home Camera Module."""

import logging
from datetime import datetime
from io import BytesIO

from PIL import Image

from camerabot.alarm import AlarmService
from camerabot.api import HikVisionAPI
from camerabot.constants import IMG
from camerabot.exceptions import HomeCamError, APIError
from camerabot.livestream import YouTubeStreamService, IcecastStreamService
from camerabot.service import ServiceController


class CameraPoolController:
    """Pool class for containing all camera instances."""

    def __init__(self):
        self._instances = {}

    def __repr__(self):
        return '<{0} id={1}>: {2}'.format(self.__class__.__name__, id(self),
                                          repr(self._instances))

    def __str__(self):
        return str(self._instances)

    def add(self, cam_id, commands, instance):
        self._instances[cam_id] = {'instance': instance,
                                   'commands': commands}

    def get_instance(self, cam_id):
        return self._instances[cam_id]['instance']

    def get_commands(self, cam_id):
        return self._instances[cam_id]['commands']

    def get_all(self):
        return self._instances

    def get_count(self):
        return len(self._instances)


class HomeCam:
    """Camera class."""

    def __init__(self, conf):
        self._log = logging.getLogger(self.__class__.__name__)
        self.conf = conf
        self.description = conf.description
        self._log.debug('Initializing %s', self.description)
        self._api = HikVisionAPI(conf=conf.api)
        self.snapshots_taken = 0

        self.alarm = AlarmService(conf=conf.alert, api=self._api)
        self.stream_yt = YouTubeStreamService(
            conf=conf.livestream.youtube,
            hik_user=conf.api.auth.user,
            hik_password=conf.api.auth.password,
            hik_host=conf.api.host)
        self.stream_icecast = IcecastStreamService(
            conf=conf.livestream.icecast,
            hik_user=conf.api.auth.user,
            hik_password=conf.api.auth.password,
            hik_host=conf.api.host)
        self.service_controller = ServiceController()
        self.service_controller.register_services((self.alarm, self.stream_yt,
                                                   self.stream_icecast))
        self._log.debug(self.service_controller)

    def __repr__(self):
        return '<HomeCam desc="{0}">'.format(self.description)

    def take_snapshot(self, resize=False):
        """Take and return full or resized snapshot from the camera."""
        self._log.debug('Taking snapshot from %s', self.description)
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

    def _resize_snapshot(self, raw_snapshot):
        """Return resized JPEG snapshot."""
        snapshot = Image.open(raw_snapshot)
        resized_snapshot = BytesIO()

        snapshot.resize(IMG.SIZE, Image.ANTIALIAS)
        snapshot.save(resized_snapshot, IMG.FORMAT, quality=IMG.QUALITY)
        resized_snapshot.seek(0)

        self._log.debug('Raw snapshot: %s, %s, %s', snapshot.format,
                        snapshot.mode,
                        snapshot.size)
        self._log.debug('Resized snapshot: %s', IMG.SIZE)
        return resized_snapshot
