"""Hikvision camera module."""

import asyncio
import logging
from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING

from pyrogram.types import Message

from hikcamerabot.clients.hikvision import HikvisionAPI, HikvisionAPIClient
from hikcamerabot.clients.hikvision.enums import IrcutFilterType
from hikcamerabot.common.video.videogif_recorder import VideoGifRecorder
from hikcamerabot.config.schemas.main_config import CameraConfigSchema
from hikcamerabot.enums import VideoGifType
from hikcamerabot.exceptions import HikvisionAPIError, HikvisionCamError
from hikcamerabot.services.abstract import AbstractService
from hikcamerabot.services.alarm import AlarmService
from hikcamerabot.services.manager import ServiceManager
from hikcamerabot.services.stream import (
    DvrStreamService,
    IcecastStreamService,
    SrsStreamService,
    TelegramStreamService,
    YouTubeStreamService,
)
from hikcamerabot.services.timelapse.timelapse import TimelapseService
from hikcamerabot.utils.image import ImageProcessor

if TYPE_CHECKING:
    from hikcamerabot.camerabot import CameraBot


class ServiceContainer:
    """Container class for all services."""

    def __init__(
        self,
        conf: CameraConfigSchema,
        api: HikvisionAPI,
        cam: 'HikvisionCam',
        bot: 'CameraBot',
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
        self.timelapse = TimelapseService(
            conf=conf.timelapse,
            cam=cam,
            api=api,
            bot=bot,
        )

    def get_all(self) -> tuple[AbstractService, ...]:
        """Return tuple with all services."""
        return (
            self.alarm,
            self.dvr_stream,
            self.srs_stream,
            self.stream_icecast,
            self.stream_tg,
            self.stream_yt,
            self.timelapse,
        )


class HikvisionCam:
    """Hikvision Camera Class."""

    _DEFAULT_GROUP_NAME: str = 'Default group'

    def __init__(self, id_: str, conf: CameraConfigSchema, bot: 'CameraBot') -> None:
        self._log = logging.getLogger(self.__class__.__name__)

        self.id = id_
        self.conf = conf
        self.bot = bot

        self.description = conf.description
        self.host = conf.api.host
        self.hashtag: str = f'#{conf.hashtag.lower() if conf.hashtag else self.id}'
        self.group = conf.group or self._DEFAULT_GROUP_NAME
        self.is_behind_nvr = conf.nvr.is_behind
        self.nvr_channel_name = conf.nvr.channel_name

        self._api = HikvisionAPI(api_client=HikvisionAPIClient(conf=conf.api))
        self._img_processor = ImageProcessor()

        self.services = ServiceContainer(
            conf=conf,
            api=self._api,
            cam=self,
            bot=self.bot,
        )
        self.service_manager = ServiceManager()
        self.service_manager.register(self.services.get_all())

        self.snapshots_taken: int = 0
        self._videogif = VideoGifRecorder(cam=self)

        self._log.debug('[%s] Initializing camera "%s"', self.id, self.description)

    def __repr__(self) -> str:
        return f'<HikvisionCam id="{self.id}" desc="{self.description}">'

    async def start_videogif_record(
        self,
        video_type: VideoGifType = VideoGifType.ON_DEMAND,
        rewind: bool = False,
        message: Message | None = None,
    ) -> None:
        self._videogif.start_rec(video_type=video_type, rewind=rewind, message=message)

    async def set_ircut_filter(self, filter_type: IrcutFilterType) -> None:
        await self._api.set_ircut_filter(filter_type)

    async def take_snapshot(
        self, channel: int, resize: bool = False
    ) -> tuple[BytesIO, int]:
        """Take and return full or resized snapshot from the camera."""
        self._log.debug('[%s] Taking snapshot', self.id)
        try:
            image_obj = await self._api.take_snapshot(channel=channel)
        except HikvisionAPIError as err:
            err_msg = f'[{self.id}] Failed to take snapshot from "{self.description}"'
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
            err_msg = (
                f'[{self.id}] Failed to resize snapshot taken from {self.description}'
            )
            self._log.exception(err_msg)
            raise HikvisionCamError(err_msg) from err

    def _increase_snapshot_count(self) -> None:
        self.snapshots_taken += 1
