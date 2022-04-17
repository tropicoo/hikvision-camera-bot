import abc
import logging
import time
from typing import TYPE_CHECKING

from httpx import ConnectError
from tenacity import retry, retry_if_exception_type, wait_fixed

from hikcamerabot.config.config import get_result_queue
from hikcamerabot.constants import Detection, Event, ServiceType, VideoGifType
from hikcamerabot.exceptions import ChunkDetectorError, ChunkLoopError
from hikcamerabot.services.tasks.abstract import AbstractServiceTask
from hikcamerabot.utils.chunk import ChunkDetector
from hikcamerabot.utils.task import create_task

if TYPE_CHECKING:
    from hikcamerabot.services.alarm import AlarmService


class ServiceAlarmMonitoringTask(AbstractServiceTask):
    """Alarm Pusher Service Class."""

    type = ServiceType.ALARM

    RETRY_WAIT = 0.5

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._alert_notifier = AlertNotifier(service=self.service)

    @retry(retry=retry_if_exception_type(Exception), wait=wait_fixed(RETRY_WAIT))
    async def run(self) -> None:
        """Monitor and process alarm/alert chunks from Hikvision Camera."""
        self._log.info('Starting alert pusher task for camera: "%s"',
                       self._cam.description)
        try:
            await self._process_chunks()
        except ChunkLoopError:
            err_msg = 'Unexpectedly exited from stream chunk processing loop for ' \
                      f'{self._cam.id}. Retrying in {self.RETRY_WAIT} seconds...'
            self._log.error(err_msg)
            raise
        except ConnectError:
            self._log.error('Failed to connect to %s alert stream. Retrying '
                            'in %s seconds...', self._cam.id, self.RETRY_WAIT)
            raise
        except Exception:
            self._log.exception(
                f'Unknown exception in {self.__class__.__name__} for {self._cam.id}. '
                f'Retrying in {self.RETRY_WAIT} seconds...')
            raise

    async def _process_chunks(self) -> None:
        """Process chunks received from Hikvision camera alert stream."""
        wait_before = 0
        async for chunk in self.service.alert_stream():
            if not self.service.started:
                self._log.info('Exiting alert pusher task for %s',
                               self._cam.description)
                break

            if int(time.time()) < wait_before or not chunk:
                continue

            try:
                detection_type = ChunkDetector.detect_chunk(chunk)
            except ChunkDetectorError as err:
                self._log.error(err)
                continue

            if detection_type:
                self.service.increase_alert_count()
                self._send_alerts(detection_type)
                wait_before = int(time.time()) + self.service.alert_delay
        else:
            raise ChunkLoopError

    def _send_alerts(self, detection_type: Detection) -> None:
        self._log.info('Sending alerts for %s', detection_type)
        # TODO: Put to queue and await everything, don't schedule tasks.
        self._alert_notifier.notify(detection_type)


class AbstractAlertNotificationTask(metaclass=abc.ABCMeta):

    def __init__(self, service: 'AlarmService',
                 detection_type: Detection) -> None:
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
        await self._result_queue.put({
            'event': Event.SEND_TEXT,
            'text': f'[Alert - {self._cam.id}] Detected {self._detection_type.value}',
        })


class AlarmVideoGifNotificationTask(AbstractAlertNotificationTask):

    async def _run(self) -> None:
        if self._cam.conf.alert.video_gif.enabled:
            await self._cam.start_videogif_record(video_type=VideoGifType.ALERT)


class AlarmPicNotificationTask(AbstractAlertNotificationTask):

    async def _run(self) -> None:
        if self._cam.conf.alert[self._detection_type.value].sendpic:
            await self._send_pic()

    async def _send_pic(self) -> None:
        resize = not self._cam.conf.alert[self._detection_type.value].fullpic
        photo, ts = await self._cam.take_snapshot(resize=resize)
        await self._result_queue.put({
            'event': Event.ALERT_SNAPSHOT,
            'cam': self._cam,
            'img': photo,
            'ts': ts,
            'resized': resize,
            'detection_type': self._detection_type,
            'alert_count': self._service.alert_count,
        })


class AlertNotifier:
    ALARM_NOTIFICATION_TASKS = (
        AlarmTextMessageNotificationTask,
        AlarmVideoGifNotificationTask,
        AlarmPicNotificationTask,
    )

    def __init__(self, service: 'AlarmService') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._service = service

    def notify(self, detection_type: Detection) -> None:
        for task_cls in self.ALARM_NOTIFICATION_TASKS:
            task = task_cls(service=self._service, detection_type=detection_type)
            create_task(
                task.run(),
                task_name=task_cls.__name__,
                logger=self._log,
                exception_message='Task %s raised an exception',
                exception_message_args=(task_cls.__name__,),
            )
