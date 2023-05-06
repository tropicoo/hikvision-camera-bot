import logging
import time

from httpx import ConnectError
from tenacity import retry, retry_if_exception_type, wait_fixed

from hikcamerabot.camera import HikvisionCam
from hikcamerabot.enums import Detection
from hikcamerabot.exceptions import AlarmEventChunkDetectorError, ChunkLoopError
from hikcamerabot.services.alarm.camera.chunk import (
    AlarmEventChunkDetector,
    CameraNvrChannelNameDetector,
)
from hikcamerabot.services.alarm.camera.notifier import AlarmNotifier


class NvrAlarmMonitoringTask:
    """NVR Alarm Pusher Class."""

    RETRY_WAIT = 0.5

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
        self._api = cameras[0]._api

        self._run_forever = run_forever
        self._cls_name = self.__class__.__name__

    @retry(retry=retry_if_exception_type(Exception), wait=wait_fixed(RETRY_WAIT))
    async def run(self) -> None:
        """Monitor and process alarm/alert chunks from NVR Alarm Stream."""
        self._log.info('Starting NVR Alarm Monitoring Task')
        try:
            await self._process_chunks()
        except ChunkLoopError:
            self._log.error(
                'Unexpectedly exited from NVR "%s" Alert Stream chunk processing loop. '
                'Retrying in %s seconds...',
                self._host,
                self.RETRY_WAIT,
            )
            raise
        except ConnectError:
            self._log.error(
                'Failed to connect to NVR "%s" Alert Stream. Retrying in %s seconds...',
                self._host,
                self.RETRY_WAIT,
            )
            raise
        except Exception:
            self._log.exception(
                'Unknown exception in "%s" for "%s". Retrying in %s seconds...',
                self.__class__.__name__,
                self._host,
                self.RETRY_WAIT,
            )
            raise

    async def _process_chunks(self) -> None:
        """Process chunks received from NVR Alert Stream."""
        async for chunk in self._api.alert_stream():
            self._log.debug('Alert chunk from NVR "%s": %s', self._host, chunk)
            if not chunk:
                continue
            try:
                detection_type = AlarmEventChunkDetector.detect_chunk(chunk)
            except AlarmEventChunkDetectorError as err:
                self._log.error(err)
                continue

            if detection_type:
                cam = self._parse_cam(chunk)
                if int(time.time()) < self._cam_delays[cam]:
                    continue
                self._send_alerts(cam=cam, detection_type=detection_type)
                self._cam_delays[cam] = int(time.time()) + 15
        else:
            raise ChunkLoopError

    def _parse_cam(self, chunk: str) -> HikvisionCam:
        channel_name = CameraNvrChannelNameDetector.detect_channel_name(chunk)
        if not channel_name:
            raise RuntimeError(f'Could not find NVR channel name in chunk: "{chunk}"')
        return self._channel_name_to_cam_map[channel_name]

    def _send_alerts(self, cam: HikvisionCam, detection_type: Detection) -> None:
        self._log.info(
            '[%s - %s] Sending "%s" alerts', cam.id, cam.description, detection_type
        )
        # TODO: Put to queue and await everything, don't schedule tasks.
        AlarmNotifier(cam=cam, alert_count=0).notify(detection_type)
