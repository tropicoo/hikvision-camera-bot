"""Hikvision camera module."""
import asyncio
import logging
from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING

from addict import Dict
from pyrogram.types import Message

from hikcamerabot.clients.hikvision import HikvisionAPI, HikvisionAPIClient
from hikcamerabot.clients.hikvision.enums import IrcutFilterType
from hikcamerabot.enums import VideoGifType
from hikcamerabot.exceptions import HikvisionAPIError, HikvisionCamError
from hikcamerabot.services.manager import ServiceManager
from hikcamerabot.common.video.videogif_recorder import VideoGifRecorder
from hikcamerabot.services.alarm import AlarmService
from hikcamerabot.services.stream import (
    DvrStreamService,
    IcecastStreamService,
    SrsStreamService,
    TelegramStreamService,
    YouTubeStreamService,
)
from hikcamerabot.utils.image import ImageProcessor


if TYPE_CHECKING:
    from hikcamerabot.camerabot import CameraBot


class ServiceContainer:
    def __init__(
        self, conf: Dict, api: HikvisionAPI, cam: 'HikvisionCam', bot: 'CameraBot'
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self.alarm = AlarmService(
            conf=conf.alert,
            api=api,
            cam=cam,
            bot=bot,
        )
        self.stream_yt = YouTubeStreamService(
            conf=conf.livestream.youtube,
            hik_user=conf.api.auth.user,
            hik_password=conf.api.auth.password,
            hik_host=conf.api.host,
            cam=cam,
        )
        self.stream_tg = TelegramStreamService(
            conf=conf.livestream.telegram,
            hik_user=conf.api.auth.user,
            hik_password=conf.api.auth.password,
            hik_host=conf.api.host,
            cam=cam,
        )
        self.stream_icecast = IcecastStreamService(
            conf=conf.livestream.icecast,
            hik_user=conf.api.auth.user,
            hik_password=conf.api.auth.password,
            hik_host=conf.api.host,
            cam=cam,
        )
        self.srs_stream = SrsStreamService(
            conf=conf.livestream.srs,
            hik_user=conf.api.auth.user,
            hik_password=conf.api.auth.password,
            hik_host=conf.api.host,
            cam=cam,
        )
        self.dvr_stream = DvrStreamService(
            conf=conf.livestream.dvr,
            hik_user=conf.api.auth.user,
            hik_password=conf.api.auth.password,
            hik_host=conf.api.host,
            cam=cam,
        )


class HikvisionCam:
    """Hikvision Camera Class."""

    def __init__(self, id: str, conf: Dict, bot: 'CameraBot') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self.id = id
        self.conf = conf
        self.description: str = conf.description
        self.hashtag = f'#{conf.hashtag.lower()}' if conf.hashtag else self.id
        self.group = conf.group or 'Default group'
        self.bot = bot
        self._log.debug('Initializing %s', self.description)
        self._api = HikvisionAPI(api_client=HikvisionAPIClient(conf=conf.api))
        self._img_processor = ImageProcessor()

        self.services = ServiceContainer(
            conf=conf,
            api=self._api,
            cam=self,
            bot=self.bot,
        )
        self.service_manager = ServiceManager()
        self.service_manager.register(
            [
                self.services.alarm,
                self.services.stream_yt,
                self.services.stream_icecast,
                self.services.srs_stream,
                self.services.dvr_stream,
                self.services.stream_tg,
            ]
        )

        self.snapshots_taken = 0
        self._videogif = VideoGifRecorder(cam=self)

    def __repr__(self) -> str:
        return f'<HikvisionCam desc="{self.description}">'

    async def start_videogif_record(
        self,
        video_type: VideoGifType = VideoGifType.ON_DEMAND,
        rewind: bool = False,
        context: Message = None,
    ) -> None:
        self._videogif.start_rec(video_type=video_type, rewind=rewind, context=context)

    async def set_ircut_filter(self, filter_type: IrcutFilterType) -> None:
        await self._api.set_ircut_filter(filter_type)

    async def take_snapshot(self, resize: bool = False) -> tuple[BytesIO, int]:
        """Take and return full or resized snapshot from the camera."""
        self._log.debug('Taking snapshot from %s', self.description)
        try:
            image_obj = await self._api.take_snapshot()
        except HikvisionAPIError as err:
            err_msg = f'Failed to take snapshot from {self.description}'
            self._log.error(err_msg)
            raise HikvisionCamError(err_msg) from err

        taken_at = int(datetime.now().timestamp())
        self._increase_snapshot_count()

        try:
            return (
                await asyncio.get_running_loop().run_in_executor(
                    None, lambda: self._img_processor.resize(image_obj)
                )
                if resize
                else image_obj,
                taken_at,
            )
        except Exception as err:
            err_msg = f'Failed to resize snapshot taken from {self.description}'
            self._log.exception(err_msg)
            raise HikvisionCamError(err_msg) from err

    def _increase_snapshot_count(self) -> None:
        self.snapshots_taken += 1
