import time

from httpx import ConnectError
from tenacity import retry, retry_if_exception_type, wait_fixed

from hikcamerabot.enums import Detection, ServiceType
from hikcamerabot.exceptions import ChunkDetectorError, ChunkLoopError
from hikcamerabot.services.abstract import AbstractServiceTask
from hikcamerabot.services.alarm.chunk import ChunkDetector
from hikcamerabot.services.alarm.notifier import AlertNotifier


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
        self._log.info(
            'Starting alert pusher task for camera: "%s"', self._cam.description
        )
        try:
            await self._process_chunks()
        except ChunkLoopError:
            err_msg = (
                'Unexpectedly exited from stream chunk processing loop for '
                f'{self._cam.id}. Retrying in {self.RETRY_WAIT} seconds...'
            )
            self._log.error(err_msg)
            raise
        except ConnectError:
            self._log.error(
                'Failed to connect to %s alert stream. Retrying in %s seconds...',
                self._cam.id,
                self.RETRY_WAIT,
            )
            raise
        except Exception:
            self._log.exception(
                f'Unknown exception in {self.__class__.__name__} for {self._cam.id}. '
                f'Retrying in {self.RETRY_WAIT} seconds...'
            )
            raise

    async def _process_chunks(self) -> None:
        """Process chunks received from Hikvision camera alert stream."""
        wait_before = 0
        async for chunk in self.service.alert_stream():
            if not self.service.started:
                self._log.info(
                    'Exiting alert pusher task for %s', self._cam.description
                )
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
