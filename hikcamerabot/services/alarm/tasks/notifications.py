import abc
import logging
from typing import TYPE_CHECKING

from hikcamerabot.config.config import get_result_queue
from hikcamerabot.constants import Detection, Event, VideoGifType
from hikcamerabot.event_engine.events.outbound import (
    AlertSnapshotOutboundEvent,
    SendTextOutboundEvent,
)

if TYPE_CHECKING:
    from hikcamerabot.services.alarm import AlarmService


class AbstractAlertNotificationTask(metaclass=abc.ABCMeta):
    def __init__(self, service: 'AlarmService', detection_type: Detection) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._service = service
        self._detection_type = detection_type
        self._cam = service.cam
        self._result_queue = get_result_queue()

    async def run(self) -> None:
        self._log.info('Starting %s', self.__class__.__name__)
        await self._run()

    @abc.abstractmethod
    async def _run(self) -> None:
        pass


class AlarmTextMessageNotificationTask(AbstractAlertNotificationTask):
    async def _run(self) -> None:
        await self._result_queue.put(
            SendTextOutboundEvent(
                event=Event.SEND_TEXT,
                text=f'[Alert - {self._cam.id}] Detected {self._detection_type.value}',
            )
        )


class AlarmVideoGifNotificationTask(AbstractAlertNotificationTask):
    async def _run(self) -> None:
        if self._cam.conf.alert[self._detection_type.value].send_videogif:
            await self._cam.start_videogif_record(
                video_type=VideoGifType.ON_ALERT,
                rewind=self._cam.conf.video_gif[VideoGifType.ON_ALERT.value].rewind,
            )


class AlarmPicNotificationTask(AbstractAlertNotificationTask):
    async def _run(self) -> None:
        if self._cam.conf.alert[self._detection_type.value].sendpic:
            await self._send_pic()

    async def _send_pic(self) -> None:
        resize = not self._cam.conf.alert[self._detection_type.value].fullpic
        photo, ts = await self._cam.take_snapshot(resize=resize)
        await self._result_queue.put(
            AlertSnapshotOutboundEvent(
                cam=self._cam,
                event=Event.ALERT_SNAPSHOT,
                img=photo,
                ts=ts,
                resized=resize,
                detection_type=self._detection_type,
                alert_count=self._service.alert_count,
                message=None,
            )
        )
