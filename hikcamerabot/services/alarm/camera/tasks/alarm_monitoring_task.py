import time
from typing import Literal

from httpx import TransportError

from hikcamerabot.enums import DetectionType, ServiceType
from hikcamerabot.exceptions import (
    AlarmEventChunkDetectorError,
    ChunkLoopError,
    HikvisionAPIError,
)
from hikcamerabot.services.abstract import AbstractServiceTask
from hikcamerabot.services.alarm.camera.chunk import AlarmEventChunkDetector
from hikcamerabot.services.alarm.camera.notifier import AlarmNotifier
from hikcamerabot.services.alarm.link import CameraLinkNotifier
from hikcamerabot.utils.task import retry_forever


class ServiceAlarmMonitoringTask(AbstractServiceTask):
    """Alarm Pusher Service Class."""

    TYPE: Literal[ServiceType.ALARM] = ServiceType.ALARM

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._alert_notifier = AlarmNotifier(
            cam=self._cam,
            alert_count=self.service.alert_count,
        )
        self._link = CameraLinkNotifier(
            bot=self._bot, title=f'{self._cam.description} ({self._cam.id})'
        )

    async def run(self) -> None:
        """Monitor alarm/alert chunks, reconnecting with backoff on errors."""
        await retry_forever(
            self._run, logger=self._log, name=f'{self._cam.id} alert pusher task'
        )

    async def _run(self) -> None:
        """Monitor and process alarm/alert chunks from Hikvision Camera."""
        self._log.info('[%s] Starting alert pusher task', self._cam.id)
        try:
            await self._process_chunks()
        except Exception as err:
            self._log_failure(err)
            await self._link.on_failure(err)
            raise

    def _log_failure(self, err: Exception) -> None:
        if isinstance(err, ChunkLoopError):
            self._log.error(
                '[%s] Unexpectedly exited from stream chunk processing loop',
                self._cam.id,
            )
        elif isinstance(err, TransportError | HikvisionAPIError):
            # Camera is offline or rejects us: one line, no traceback.
            self._log.error(
                '[%s] Alert Stream connection failed: %s: %s',
                self._cam.id,
                err.__class__.__name__,
                err,
            )
        else:
            self._log.exception(
                '[%s] Unknown exception in %s', self._cam.id, self.__class__.__name__
            )

    async def _process_chunks(self) -> None:
        """Process chunks received from Hikvision camera alert stream."""
        wait_before = 0
        async for chunk in self.service.alert_stream():
            self._log.debug('Alert chunk for cam "%s": %s', self._cam.id, chunk)
            if not self.service.started:
                self._log.info('[%s] Exiting alert pusher task', self._cam.id)
                break
            await self._link.on_success()

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

    def _send_alerts(self, detection_type: DetectionType) -> None:
        self._log.info('[%s] Sending %s alerts', self._cam.id, detection_type)
        # TODO: Put to queue and await everything, don't schedule tasks.
        self._alert_notifier.notify(detection_type)
