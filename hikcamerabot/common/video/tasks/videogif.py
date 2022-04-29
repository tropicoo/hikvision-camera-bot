import asyncio
import logging
import os
import signal
import socket
import time
from typing import Optional, TYPE_CHECKING
from urllib.parse import urlsplit

from addict import Dict
from pyrogram.types import Message

from hikcamerabot.common.video.tasks.ffprobe_context import GetFfprobeContextTask
from hikcamerabot.common.video.tasks.thumbnail import MakeThumbnailTask
from hikcamerabot.constants import (
    FFMPEG_CAM_VIDEO_SRC,
    FFMPEG_CMD_HLS_VIDEO_GIF,
    FFMPEG_CMD_VIDEO_GIF,
    FFMPEG_SRS_HLS_VIDEO_SRC,
    FFMPEG_SRS_RTMP_VIDEO_SRC,
    RTSP_TRANSPORT_TPL,
    SRS_LIVESTREAM_NAME_TPL,
)
from hikcamerabot.enums import Event, VideoGifType
from hikcamerabot.event_engine.events.outbound import (
    SendTextOutboundEvent,
    VideoOutboundEvent,
)
from hikcamerabot.event_engine.queue import get_result_queue
from hikcamerabot.utils.task import wrap
from hikcamerabot.utils.utils import format_ts, gen_random_str, bold

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam


class RecordVideoGifTask:
    _PROCESS_TIMEOUT = 30

    _VIDEO_FILENAME_MAP: dict[VideoGifType, str] = {
        VideoGifType.ON_ALERT: '{0}-alert-{1}-{2}.mp4',
        VideoGifType.ON_DEMAND: '{0}-{1}-{2}.mp4',
    }

    _VIDEO_TYPE_TO_EVENT: dict[VideoGifType, Event] = {
        VideoGifType.ON_ALERT: Event.ALERT_VIDEO,
        VideoGifType.ON_DEMAND: Event.RECORD_VIDEOGIF,
    }

    FILENAME_TIME_FORMAT = '%Y-%b-%d--%H-%M-%S'

    def __init__(
        self,
        rewind: bool,
        cam: 'HikvisionCam',
        video_type: VideoGifType,
        context: Message = None,
    ):
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam = cam
        self._video_type = video_type
        self._rewind = rewind
        self._gif_conf: Dict = self._cam.conf.video_gif[self._video_type.value]
        self._is_srs_enabled: bool = self._cam.conf.livestream.srs.enabled

        self._tmp_storage_path: str = self._gif_conf.tmp_storage
        self._filename = self._get_filename()
        self._file_path: str = os.path.join(self._tmp_storage_path, self._filename)
        self._thumb_path: str = os.path.join(
            self._tmp_storage_path, f'{self._filename}.jpg'
        )
        self._thumb_created = False

        self._rec_time: int = self._gif_conf.record_time
        if self._rewind:
            self._rec_time += self._gif_conf.rewind_time

        self._message = context
        self._event = self._VIDEO_TYPE_TO_EVENT[self._video_type]
        self._result_queue = get_result_queue()
        self._killpg = wrap(os.killpg)
        self._ffmpeg_cmd = self._build_ffmpeg_cmd()

        self._duration: Optional[int] = None
        self._width: Optional[int] = None
        self._height: Optional[int] = None
        self._probe_ctx: Optional[dict] = None

    async def run(self) -> None:
        await asyncio.gather(self._record(), self._send_confirmation_message())

    async def _record(self) -> None:
        """Start Ffmpeg subprocess and return file path and video type."""
        self._log.debug(
            'Recording %s video gif from %s: %s',
            self._video_type.value,
            self._cam.conf.description,
            self._ffmpeg_cmd,
        )
        await self._start_ffmpeg_subprocess()
        is_validated = await self._validate_file()
        if not is_validated:
            err_msg = f'Failed to record {self._file_path} on {self._cam.description}'
            self._log.error(err_msg)
            await self._result_queue.put(
                SendTextOutboundEvent(
                    event=Event.SEND_TEXT,
                    text=f'{err_msg}.\nEvent type: {self._event.value}\nCheck logs.',
                    message=self._message,
                )
            )
        if is_validated:
            await asyncio.gather(self._get_probe_ctx(), self._make_thumbnail_frame())
            await self._send_result()

    async def _make_thumbnail_frame(self) -> None:
        # TODO: Refactor duplicate code. Move to mixin.
        if not await MakeThumbnailTask(self._thumb_path, self._file_path).run():
            self._log.error(
                'Error during making thumbnail context of %s', self._file_path
            )
            return
        self._thumb_created = True

    async def _get_probe_ctx(self) -> None:
        # TODO: Refactor duplicate code. Move to mixin.
        self._probe_ctx = await GetFfprobeContextTask(self._file_path).run()
        if not self._probe_ctx:
            return
        video_streams = [
            stream
            for stream in self._probe_ctx['streams']
            if stream['codec_type'] == 'video'
        ]
        self._duration = int(float(self._probe_ctx['format']['duration']))
        self._height = video_streams[0]['height']
        self._width = video_streams[0]['width']

    def _post_err_cleanup(self):
        """Delete video file and thumb if they exist after exception."""
        for file_path in (self._file_path, self._thumb_path):
            try:
                os.remove(file_path)
            except Exception as err:
                self._log.warning('File path %s not deleted: %s', file_path, err)

    async def _start_ffmpeg_subprocess(self) -> None:
        proc_timeout = (
            self._cam.conf.alert.video_gif.record_time + self._PROCESS_TIMEOUT
        )
        proc = await asyncio.create_subprocess_shell(self._ffmpeg_cmd)
        try:
            await asyncio.wait_for(proc.wait(), timeout=proc_timeout)
        except asyncio.TimeoutError:
            self._log.error(
                'Failed to record %s: FFMPEG process ran longer than '
                'expected and was killed',
                self._file_path,
            )
            await self._killpg(os.getpgid(proc.pid), signal.SIGINT)
            self._post_err_cleanup()

    async def _validate_file(self) -> bool:
        """Validate recorded file existence and size."""
        try:
            is_empty = os.path.getsize(self._file_path) == 0
        except FileNotFoundError:
            self._log.error(
                'Failed to validate %s: File does not exist', self._file_path
            )
            return False
        except Exception:
            self._log.exception('Failed to validate %s', self._file_path)
            return False

        if is_empty:
            self._log.error('Failed to validate %s: File is empty', self._file_path)
            self._post_err_cleanup()
        return not is_empty

    async def _send_result(self) -> None:
        await self._result_queue.put(
            VideoOutboundEvent(
                event=self._event,
                video_path=self._file_path,
                video_duration=self._duration or 0,
                video_height=self._height or 0,
                video_width=self._width or 0,
                thumb_path=self._thumb_path if self._thumb_created else None,
                cam=self._cam,
                message=self._message,
            )
        )

    async def _send_confirmation_message(self) -> None:
        if self._video_type is VideoGifType.ON_DEMAND:
            text = f'Recording video gif for {self._rec_time} seconds'
            await self._result_queue.put(
                SendTextOutboundEvent(
                    event=Event.SEND_TEXT,
                    message=self._message,
                    text=bold(text),
                )
            )

    def _get_filename(self) -> str:
        return self._VIDEO_FILENAME_MAP[self._video_type].format(
            self._cam.id,
            format_ts(time.time(), time_format=self.FILENAME_TIME_FORMAT),
            gen_random_str(),
        )

    def _build_ffmpeg_cmd(self) -> str:
        if self._is_srs_enabled:
            livestream_name = SRS_LIVESTREAM_NAME_TPL.format(
                channel=self._gif_conf.channel, cam_id=self._cam.id
            )
            if self._rewind:
                video_source = FFMPEG_SRS_HLS_VIDEO_SRC.format(
                    ip_address=socket.gethostbyname('hikvision_srs_server'),
                    livestream_name=livestream_name,
                )
                return FFMPEG_CMD_HLS_VIDEO_GIF.format(
                    video_source=video_source,
                    rec_time=self._rec_time,
                    loglevel=self._gif_conf.loglevel,
                    filepath=self._file_path,
                )
            else:
                video_source = FFMPEG_SRS_RTMP_VIDEO_SRC.format(
                    livestream_name=livestream_name
                )
        else:
            video_source = FFMPEG_CAM_VIDEO_SRC.format(
                user=self._cam.conf.api.auth.user,
                pw=self._cam.conf.api.auth.password,
                host=urlsplit(self._cam.conf.api.host).netloc,
                rtsp_port=self._cam.conf.rtsp_port,
                channel=self._gif_conf.channel,
            )
        return FFMPEG_CMD_VIDEO_GIF.format(
            rtsp_transport=RTSP_TRANSPORT_TPL.format(
                rtsp_transport_type=self._gif_conf.rtsp_transport_type
            )
            if not self._is_srs_enabled
            else '',
            video_source=video_source,
            rec_time=self._rec_time,
            loglevel=self._gif_conf.loglevel,
            filepath=self._file_path,
        )
