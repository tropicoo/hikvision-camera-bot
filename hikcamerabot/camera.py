"""Hikvision Camera Module."""

import logging
from datetime import datetime
from io import BytesIO

from hikcamerabot.core.clients.hikvision import HikvisionAPI
from hikcamerabot.exceptions import HikvisionCamError, APIError
from hikcamerabot.managers.service import ServiceManager
from hikcamerabot.managers.video import VideoGifManager
from hikcamerabot.processors.img import ImageProcessor
from hikcamerabot.services.alarm import AlarmService
from hikcamerabot.services.livestream import (YouTubeStreamService,
                                              IcecastStreamService)


class HikvisionCam:
    """Hikvision Camera Class."""

    def __init__(self, _id, conf):
        self._log = logging.getLogger(self.__class__.__name__)
        self.id = _id
        self.conf = conf
        self.description = conf.description
        self._log.debug('Initializing %s', self.description)
        self._api = HikvisionAPI(conf=conf.api)

        self._img = ImageProcessor()
        self.video_manager = VideoGifManager(conf)

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
        self.service_manager = ServiceManager()
        self.service_manager.register_services((self.alarm, self.stream_yt,
                                                self.stream_icecast))
        self.snapshots_taken = 0

    def __repr__(self):
        return f'<HikvisionCam desc="{self.description}">'

    def take_snapshot(self, resize=False):
        """Take and return full or resized snapshot from the camera."""
        self._log.debug('Taking snapshot from %s', self.description)
        try:
            res = self._api.take_snapshot()
        except APIError:
            err_msg = f'Failed to take snapshot from {self.description}'
            self._log.error(err_msg)
            raise HikvisionCamError(err_msg)

        snapshot_timestamp = int(datetime.now().timestamp())
        self.snapshots_taken += 1

        try:
            snapshot = self._img.resize(res.raw) if resize else BytesIO(
                res.raw.data)
        except Exception:
            err_msg = f'Failed to resize snapshot taken from {self.description}'
            self._log.exception(err_msg)
            raise HikvisionCamError(err_msg)
        return snapshot, snapshot_timestamp
