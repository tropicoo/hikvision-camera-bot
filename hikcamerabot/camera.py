"""Hikvision camera module."""
import asyncio
import logging
from datetime import datetime
from io import BytesIO

from addict import Addict

from hikcamerabot.clients.hikvision import HikvisionAPI
from hikcamerabot.exceptions import HikvisionAPIError, HikvisionCamError
from hikcamerabot.managers.service import ServiceManager
from hikcamerabot.managers.video import VideoGifManager
from hikcamerabot.services.alarm import AlarmService
from hikcamerabot.services.livestream import IcecastStreamService, YouTubeStreamService
from hikcamerabot.utils.image import ImageProcessor


class HikvisionCam:
    """Hikvision Camera Class."""

    def __init__(self, id: str, conf: Addict, bot):
        self._log = logging.getLogger(self.__class__.__name__)
        self.id = id
        self.conf = conf
        self.description: str = conf.description
        self.hashtag: str = f'#{conf.hashtag.lower()}' if conf.hashtag else ''
        self.bot = bot
        self._log.debug('Initializing %s', self.description)
        self._api = HikvisionAPI(conf=conf.api)

        self._img = ImageProcessor()

        self.alarm = AlarmService(conf=conf.alert, api=self._api, cam=self, bot=bot)
        self.stream_yt = YouTubeStreamService(
            conf=conf.livestream.youtube,
            hik_user=conf.api.auth.user,
            hik_password=conf.api.auth.password,
            hik_host=conf.api.host,
            cam=self,
        )
        self.stream_icecast = IcecastStreamService(
            conf=conf.livestream.icecast,
            hik_user=conf.api.auth.user,
            hik_password=conf.api.auth.password,
            hik_host=conf.api.host,
            cam=self,
        )
        self.service_manager = ServiceManager()
        self.service_manager.register((self.alarm, self.stream_yt,
                                       self.stream_icecast))
        self.snapshots_taken = 0
        self.video_manager = VideoGifManager(cam=self, conf=conf)

    def __repr__(self) -> str:
        return f'<HikvisionCam desc="{self.description}">'

    async def take_snapshot(self, resize: bool = False) -> tuple[BytesIO, int]:
        """Take and return full or resized snapshot from the camera."""
        self._log.debug('Taking snapshot from %s', self.description)
        try:
            image_obj = await self._api.take_snapshot()
        except HikvisionAPIError:
            err_msg = f'Failed to take snapshot from {self.description}'
            self._log.error(err_msg)
            raise HikvisionCamError(err_msg)

        taken_at = int(datetime.now().timestamp())
        self._increase_snapshot_count()

        try:
            return (
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: self._img.resize(image_obj)
                ) if resize else image_obj, taken_at,
            )
        except Exception:
            err_msg = f'Failed to resize snapshot taken from {self.description}'
            self._log.exception(err_msg)
            raise HikvisionCamError(err_msg)

    def _increase_snapshot_count(self) -> None:
        self.snapshots_taken += 1
