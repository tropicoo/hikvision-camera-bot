import time

from httpx import ConnectError
from tenacity import retry, retry_if_exception_type, wait_fixed

from hikcamerabot.enums import Detection, ServiceType
from hikcamerabot.exceptions import AlarmEventChunkDetectorError, ChunkLoopError
from hikcamerabot.services.abstract import AbstractServiceTask
from hikcamerabot.services.alarm.camera.chunk import AlarmEventChunkDetector
from hikcamerabot.services.alarm.camera.notifier import AlarmNotifier


class ServiceAlarmMonitoringTask(AbstractServiceTask):
    """Alarm Pusher Service Class."""

    type = ServiceType.ALARM

    RETRY_WAIT = 0.5

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._alert_notifier = AlarmNotifier(
            cam=self._cam,
            alert_count=self.service.alert_count,
        )

    @retry(retry=retry_if_exception_type(Exception), wait=wait_fixed(RETRY_WAIT))
    async def run(self) -> None:
        """Monitor and process alarm/alert chunks from Hikvision Camera."""
        self._log.info('[%s] Starting alert pusher task', self._cam.id)
        try:
            await self._process_chunks()
        except ChunkLoopError:
            self._log.error(
                '[%s] Unexpectedly exited from stream chunk processing loop. '
                'Retrying in %s seconds...',
                self._cam.id,
                self.RETRY_WAIT,
            )
            raise
        except ConnectError:
            self._log.error(
                '[%s] Failed to connect to Alert Stream. Retrying in %s seconds...',
                self._cam.id,
                self.RETRY_WAIT,
            )
            raise
        except Exception:
            self._log.exception(
                '[%s] Unknown exception in %s. Retrying in %s seconds...',
                self._cam.id,
                self.__class__.__name__,
                self.RETRY_WAIT,
            )
            raise

    async def _process_chunks(self) -> None:
        """Process chunks received from Hikvision camera alert stream."""
        wait_before = 0
        async for chunk in self.service.alert_stream():
            self._log.debug('Alert chunk for cam "%s": %s', self._cam.id, chunk)
            if not self.service.started:
                self._log.info('[%s] Exiting alert pusher task', self._cam.id)
                break

            if int(time.time()) < wait_before or not chunk:
                continue

            try:
                detection_type = AlarmEventChunkDetector.detect_chunk(chunk)
            except AlarmEventChunkDetectorError as err:
                self._log.error(err)
                continue

            if detection_type:
                self.service.increase_alert_count()
                self._send_alerts(detection_type)
                wait_before = int(time.time()) + self.service.alert_delay
        else:
            raise ChunkLoopError

    def _send_alerts(self, detection_type: Detection) -> None:
        self._log.info('[%s] Sending %s alerts', self._cam.id, detection_type)
        # TODO: Put to queue and await everything, don't schedule tasks.
        self._alert_notifier.notify(detection_type)
