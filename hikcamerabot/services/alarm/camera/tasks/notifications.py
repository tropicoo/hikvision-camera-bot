import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from emoji import emojize
from pyrogram.enums import ParseMode

from hikcamerabot.constants import DETECTION_SWITCH_MAP
from hikcamerabot.enums import DetectionType, EventType, VideoGifType
from hikcamerabot.event_engine.events.outbound import (
    AlertSnapshotOutboundEvent,
    SendTextOutboundEvent,
)
from hikcamerabot.event_engine.queue import get_result_queue

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam


class AbstractAlertNotificationTask(ABC):
    def __init__(
        self, detection_type: DetectionType, cam: 'HikvisionCam', alert_count: int
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._detection_type = detection_type
        self._cam = cam
        self._alert_count = alert_count
        self._result_queue = get_result_queue()

    async def run(self) -> None:
        self._log.info('Starting %s', self.__class__.__name__)
        await self._run()

    @abstractmethod
    async def _run(self) -> None:
        pass


class AlarmTextMessageNotificationTask(AbstractAlertNotificationTask):
    async def _run(self) -> None:
        if self._cam.conf.alert.get_detection_schema_by_type(
            type_=self._detection_type.value
        ).send_text:
            await self._send_alert_text()

    async def _send_alert_text(self) -> None:
        detection_name = DETECTION_SWITCH_MAP[self._detection_type]['name']
        await self._result_queue.put(
            SendTextOutboundEvent(
                event=EventType.SEND_TEXT,
                text=emojize(
                    f':rotating_light: <b>Alert on "{self._cam.id} - '
                    f'{self._cam.description}": {detection_name}</b>',
                    language='alias',
                ),
                parse_mode=ParseMode.HTML,
            )
        )


class AlarmVideoGifNotificationTask(AbstractAlertNotificationTask):
    async def _run(self) -> None:
        if self._cam.conf.alert.get_detection_schema_by_type(
            type_=self._detection_type.value
        ).send_videogif:
            await self._start_videogif_record()

    async def _start_videogif_record(self) -> None:
        await self._cam.start_videogif_record(
            video_type=VideoGifType.ON_ALERT,
            rewind=self._cam.conf.video_gif.get_schema_by_type(
                type_=VideoGifType.ON_ALERT.value
            ).rewind,
        )


class AlarmPicNotificationTask(AbstractAlertNotificationTask):
    async def _run(self) -> None:
        if self._cam.conf.alert.get_detection_schema_by_type(
            type_=self._detection_type.value
        ).sendpic:
            await self._send_pic()

    async def _send_pic(self) -> None:
        channel: int = self._cam.conf.picture.on_alert.channel
        resize = not self._cam.conf.alert.get_detection_schema_by_type(
            type_=self._detection_type.value
        ).fullpic
        photo, ts = await self._cam.take_snapshot(channel=channel, resize=resize)
        await self._result_queue.put(
            AlertSnapshotOutboundEvent(
                cam=self._cam,
                event=EventType.ALERT_SNAPSHOT,
                img=photo,
                ts=ts,
                resized=resize,
                detection_type=self._detection_type,
                alert_count=self._alert_count,
                message=None,
                file_size=photo.getbuffer().nbytes,
            )
        )
