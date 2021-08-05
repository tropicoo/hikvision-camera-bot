import logging
import time

from httpx import ConnectError
from tenacity import retry, retry_if_exception_type, wait_fixed

from hikcamerabot.constants import Alarm, Event
from hikcamerabot.exceptions import ChunkDetectorError, ChunkLoopError
from hikcamerabot.services.tasks.abstract import AbstractServiceTask
from hikcamerabot.utils.chunk import ChunkDetector
from hikcamerabot.utils.utils import shallow_sleep_async

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
                self.service.alert_count += 1
                self._cam.video_manager.start_rec()
                try:
                    await self._send_alert(detection_key)
                except Exception as err:
                    self._log.exception('Exception in task %s: %s',
                                        self._cls_name, err)
                wait_before = int(time.time()) + self.service.alert_delay
        else:
            raise ChunkLoopError

    async def _send_alert(self, detection_key):
        """Send alert to the user."""
        resize = not self._cam.conf.alert[detection_key].fullpic
        photo, ts = await self._cam.take_snapshot(resize=resize)
        await self._bot.result_dispatcher.dispatch({
            'event': Event.ALERT_SNAPSHOT,
            'cam': self._cam,
            'img': photo,
            'ts': ts,
            'resized': resize,
            'detection_key': detection_key,
            'alert_count': self.service.alert_count,
        })


class SendRecVideoTask:

    def __init__(self, cam):
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam = cam
        self._bot = cam.bot

    async def run(self) -> None:
        # TODO: Replace with asyncio.Event.
        while True:
            recorded_videos = self._cam.video_manager.get_recorded_videos()
            await self._process_videos(recorded_videos)
            await shallow_sleep_async(0.5)

    async def _process_videos(self, recorded_videos: list[str]) -> None:
        if not recorded_videos:
            return
        try:
            await self._bot.result_dispatcher.dispatch({
                'event': Event.ALERT_VIDEO,
                'cam': self._cam,
                'videos': recorded_videos,
            })
        except Exception:
            task_name = f'{self.__class__.__name__} {self._cam.id}'
            self._log.exception('Exception in %s', task_name)
