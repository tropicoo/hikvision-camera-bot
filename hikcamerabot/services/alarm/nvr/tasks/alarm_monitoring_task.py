import logging
import time

from httpx import TransportError

from hikcamerabot.camera import HikvisionCam
from hikcamerabot.enums import DetectionType
from hikcamerabot.exceptions import (
    AlarmEventChunkDetectorError,
    ChunkLoopError,
    HikvisionAPIError,
)
from hikcamerabot.services.alarm.camera.chunk import (
    AlarmEventChunkDetector,
    CameraNvrChannelNameDetector,
)
from hikcamerabot.services.alarm.camera.notifier import AlarmNotifier
from hikcamerabot.services.alarm.link import CameraLinkNotifier
from hikcamerabot.utils.task import retry_forever


class NvrAlarmMonitoringTask:
    """NVR Alarm Pusher Class."""

    ALERT_DELAY: int = 15

    def __init__(
        self,
        host: str,
        cameras: list[HikvisionCam],
        run_forever: bool = True,
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._host = host
        self._cameras = cameras

        _channel_name_to_cam_map: dict[str, HikvisionCam] = {}
        _cam_delays: dict[HikvisionCam, int] = {}
        for cam in cameras:
            _channel_name_to_cam_map[cam.nvr_channel_name] = cam
            _cam_delays[cam] = 0

        self._channel_name_to_cam_map = _channel_name_to_cam_map
        self._cam_delays = _cam_delays

        # Each camera connects to the same NVR with the same credentials.
        # We need Hikvision API instance just to get the NVR Alert Stream.
        self._api = cameras[0]._api  # noqa: SLF001

        self._run_forever = run_forever
        self._cls_name = self.__class__.__name__
        self._link = CameraLinkNotifier(
            bot=cameras[0].bot, title=f'видеорегистратор {host}'
        )

    async def run(self) -> None:
        """Monitor NVR alarm chunks, reconnecting with backoff on errors."""
        await retry_forever(
            self._run, logger=self._log, name=f'NVR "{self._host}" alarm task'
        )

    async def _run(self) -> None:
        """Monitor and process alarm/alert chunks from NVR Alarm Stream."""
        self._log.info('Starting NVR Alarm Monitoring Task')
        try:
            await self._process_chunks()
        except Exception as err:
            self._log_failure(err)
            await self._link.on_failure(err)
            raise

    def _log_failure(self, err: Exception) -> None:
        if isinstance(err, ChunkLoopError):
            self._log.error(
                'Unexpectedly exited from NVR "%s" Alert Stream chunk processing loop',
                self._host,
            )
        elif isinstance(err, TransportError | HikvisionAPIError):
            # NVR is offline or rejects us: one line, no traceback.
            self._log.error(
                'NVR "%s" Alert Stream connection failed: %s: %s',
                self._host,
                err.__class__.__name__,
                err,
            )
        else:
            self._log.exception(
                'Unknown exception in "%s" for "%s"',
                self.__class__.__name__,
                self._host,
            )

    async def _process_chunks(self) -> None:
        """Process chunks received from NVR Alert Stream."""
        async for chunk in self._api.alert_stream():
            self._log.debug('Alert chunk from NVR "%s": %s', self._host, chunk)
            await self._link.on_success()
            if not chunk:
                continue
            try:
                detection_type = AlarmEventChunkDetector.detect_chunk(chunk)
            except AlarmEventChunkDetectorError as err:
                self._log.error(err)
                continue

            if detection_type:
                cam = self._parse_cam(chunk)
                if cam is None or int(time.time()) < self._cam_delays[cam]:
                    continue
                self._send_alerts(cam=cam, detection_type=detection_type)
                self._cam_delays[cam] = int(time.time()) + self.ALERT_DELAY
        raise ChunkLoopError

    def _parse_cam(self, chunk: str) -> HikvisionCam | None:
        """Return camera for the alert chunk or None if it isn't configured.

        Alerts from NVR channels which are not in the config (or hidden) are
        skipped instead of breaking and reconnecting the whole NVR alert stream.
        """
        channel_name = CameraNvrChannelNameDetector.detect_channel_name(chunk)
        if not channel_name:
            self._log.warning(
                'Could not find NVR channel name in chunk from "%s": "%s"',
                self._host,
                chunk,
            )
            return None
        cam = self._channel_name_to_cam_map.get(channel_name)
        if cam is None:
            self._log.debug(
                'Skip alert from NVR "%s" channel "%s": camera is not configured',
                self._host,
                channel_name,
            )
        return cam

    def _send_alerts(self, cam: HikvisionCam, detection_type: DetectionType) -> None:
        self._log.info(
            '[%s - %s] Sending "%s" alerts', cam.id, cam.description, detection_type
        )
        # TODO: Put to queue and await everything, don't schedule tasks.
        AlarmNotifier(cam=cam, alert_count=0).notify(detection_type)
