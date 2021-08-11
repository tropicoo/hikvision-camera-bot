import logging
import time

from httpx import ConnectError
from tenacity import retry, retry_if_exception_type, wait_fixed

from hikcamerabot.config.config import get_result_queue
from hikcamerabot.constants import Alarm, Event
from hikcamerabot.exceptions import ChunkDetectorError, ChunkLoopError
from hikcamerabot.services.tasks.abstract import AbstractServiceTask
from hikcamerabot.utils.chunk import ChunkDetector
from hikcamerabot.utils.task import create_task

RETRY_WAIT: int = 5


class ServiceAlarmPusherTask(AbstractServiceTask):
    """Alarm Pusher Service Class."""

    type = Alarm.SERVICE_TYPE

    @retry(retry=retry_if_exception_type(Exception), wait=wait_fixed(RETRY_WAIT))
    async def run(self):
        """Main service task run."""
        self._log.debug('Starting alert pusher task for camera: "%s"',
                        self._cam.description)
        try:
            await self._process_chunks()
        except ChunkLoopError:
            err_msg = 'Unexpectedly exited from stream chunk processing loop for ' \
                      f'{self._cam.id}. Retrying in {RETRY_WAIT} seconds...'
            self._log.error(err_msg)
            raise
        except ConnectError:
            self._log.error('Failed to connect to %s alert stream. Retrying '
                            'in %s seconds...', self._cam.id, RETRY_WAIT)
            raise
        except Exception:
            self._log.exception(
                f'Unknown exception in {self.__class__.__name__} for {self._cam.id}. '
                f'Retrying in {RETRY_WAIT} seconds...')
            raise

    async def _process_chunks(self):
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
                detection_key = ChunkDetector.detect_chunk(chunk)
            except ChunkDetectorError as err:
                self._log.error(err)
                continue

            if detection_key:
                self.service.increase_alert_count()
                await self._send_alerts(detection_key)
                wait_before = int(time.time()) + self.service.alert_delay
        else:
            raise ChunkLoopError

    async def _send_alerts(self, detection_key: str) -> None:
        if self._cam.conf.alert.video_gif.enabled:
            self._cam.video_manager.start_alert_rec()
        if self._cam.conf.alert[detection_key].sendpic:
            await self._send_alert_snapshot(detection_key)

    async def _send_alert_snapshot(self, detection_key: str) -> None:
        """Send alert to the user."""
        rec_task = TakeAlarmPicTask(
            service=self.service,
            detection_key=detection_key
        )
        create_task(
            rec_task.run(),
            task_name=TakeAlarmPicTask.__name__,
            logger=self._log,
            exception_message='Task %s raised an exception',
            exception_message_args=(TakeAlarmPicTask.__name__,),
        )


class TakeAlarmPicTask:

    def __init__(self, service, detection_key: str):
        self._log = logging.getLogger(self.__class__.__name__)
        self._service = service
        self._cam = service.cam
        self._bot = self._cam.bot
        self._detection_key = detection_key

    async def run(self):
        await self._take_pic()

    async def _take_pic(self):
        resize = not self._cam.conf.alert[self._detection_key].fullpic
        photo, ts = await self._cam.take_snapshot(resize=resize)
        await get_result_queue().put({
            'event': Event.ALERT_SNAPSHOT,
            'cam': self._cam,
            'img': photo,
            'ts': ts,
            'resized': resize,
            'detection_key': self._detection_key,
            'alert_count': self._service.alert_count,
        })
