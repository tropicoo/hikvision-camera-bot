import asyncio
import logging
import signal
import time
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urlsplit

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
from hikcamerabot.enums import EventType, VideoGifType
from hikcamerabot.event_engine.events.outbound import (
    SendTextOutboundEvent,
    VideoOutboundEvent,
)
from hikcamerabot.event_engine.queue import get_result_queue
from hikcamerabot.utils.file import file_size
from hikcamerabot.utils.process import kill_proc
from hikcamerabot.utils.shared import (
    bold,
    format_ts,
    gen_random_str,
    get_srs_server_ip_address,
)

if TYPE_CHECKING:
    from pathlib import Path

    from hikcamerabot.camera import HikvisionCam


class RecordVideoGifTask:
    _PROCESS_TIMEOUT: int = 30

    _VIDEO_FILENAME_MAP: ClassVar[dict[VideoGifType, str]] = {
        VideoGifType.ON_ALERT: '{0}-alert-{1}-{2}.mp4',
        VideoGifType.ON_DEMAND: '{0}-{1}-{2}.mp4',
    }

    _VIDEO_TYPE_TO_EVENT: ClassVar[dict[VideoGifType, EventType]] = {
        VideoGifType.ON_ALERT: EventType.ALERT_VIDEO,
        VideoGifType.ON_DEMAND: EventType.RECORD_VIDEOGIF,
    }

    FILENAME_TIME_FORMAT: str = '%Y-%b-%d--%H-%M-%S'

    def __init__(
        self,
        rewind: bool,
        cam: 'HikvisionCam',
        video_type: VideoGifType,
        message: Message | None = None,
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam = cam
        self._video_type = video_type
        self._rewind = rewind
        self._gif_conf = self._cam.conf.video_gif.get_schema_by_type(
            type_=video_type.value
        )
        self._is_srs_enabled = self._cam.conf.livestream.srs.enabled

        self._tmp_storage_path = self._gif_conf.tmp_storage
        self._filename = self._get_filename()
        self._file_path: Path = self._tmp_storage_path / self._filename
        self._thumb_path: Path = self._tmp_storage_path / f'{self._filename}-thumb.jpg'

        self._thumb_created: bool = False

        self._rec_time = self._gif_conf.record_time
        if self._rewind:
            self._rec_time += self._gif_conf.rewind_time

        self._message = message
        self._event = self._VIDEO_TYPE_TO_EVENT[self._video_type]
        self._result_queue = get_result_queue()
        self._ffmpeg_cmd = self._build_ffmpeg_cmd()

        self._duration: int | None = None
        self._width: int | None = None
        self._height: int | None = None
        self._probe_ctx: dict | None = None

    async def run(self) -> None:
        await asyncio.gather(self._record(), self._send_confirmation_message())

    async def _record(self) -> None:
        """Start Ffmpeg subprocess and return file path and video type."""
        self._log.debug(
            'Recording "%s" video from "%s": "%s"',
            self._video_type.value,
            self._cam.conf.description,
            self._ffmpeg_cmd,
        )
        await self._start_ffmpeg_subprocess()
        if await self._validate_file():
            await self._post_process_successful_record()
        else:
            await self._post_process_failed_record()

    async def _post_process_successful_record(self) -> None:
        await asyncio.gather(self._get_probe_ctx(), self._make_thumbnail_frame())
        await self._send_result()

    async def _post_process_failed_record(self) -> None:
        self._post_err_cleanup()
        err_msg = f'Failed to record {self._file_path} on {self._cam.description}'
        self._log.error(err_msg)
        await self._result_queue.put(
            SendTextOutboundEvent(
                event=EventType.SEND_TEXT,
                text=f'{err_msg}.\nEventType type: {self._event.value}\nCheck logs.',
                message=self._message,
            )
        )

    async def _make_thumbnail_frame(self) -> None:
        # TODO: Refactor duplicate code. Move to mixin.
        self._thumb_created = await MakeThumbnailTask(
            thumbnail_path=self._thumb_path, file_path=self._file_path
        ).run()
        if not self._thumb_created:
            self._log.error('Error during making thumbnail of %s', self._file_path)

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

    def _post_err_cleanup(self) -> None:
        """Delete video file and thumb if they exist after exception."""
        for file_path in (self._file_path, self._thumb_path):
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as err:
                    self._log.warning('File path %s not deleted: %s', file_path, err)

    async def _start_ffmpeg_subprocess(self) -> None:
        proc_timeout = self._rec_time + self._PROCESS_TIMEOUT
        proc = await asyncio.create_subprocess_shell(self._ffmpeg_cmd)
        try:
            await asyncio.wait_for(proc.wait(), timeout=proc_timeout)
        except TimeoutError:
            self._log.error(
                'Failed to record "%s": FFMPEG process ran longer than '
                'expected (%ds) and was killed',
                self._file_path,
                proc_timeout,
            )
            await kill_proc(process=proc, signal_=signal.SIGINT, reraise=False)
            self._post_err_cleanup()

    async def _validate_file(self) -> bool:
        """Validate recorded file existence and size."""
        try:
            is_empty = self._file_path.stat().st_size == 0
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
                file_size=file_size(filepath=self._file_path),
                create_ts=int(datetime.now().timestamp()),
            )
        )

    async def _send_confirmation_message(self) -> None:
        if self._video_type is VideoGifType.ON_DEMAND:
            text = f'📹 Recording video for {self._rec_time} seconds'
            await self._result_queue.put(
                SendTextOutboundEvent(
                    event=EventType.SEND_TEXT,
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
                    ip_address=get_srs_server_ip_address(),
                    livestream_name=livestream_name,
                )
                return FFMPEG_CMD_HLS_VIDEO_GIF.format(
                    video_source=video_source,
                    rec_time=self._rec_time,
                    loglevel=self._gif_conf.loglevel,
                    filepath=self._file_path,
                )
            video_source = FFMPEG_SRS_RTMP_VIDEO_SRC.format(
                ip_address=get_srs_server_ip_address(),
                livestream_name=livestream_name,
            )
        else:
            video_source = FFMPEG_CAM_VIDEO_SRC.format(
                user=self._cam.conf.api.auth.user,
                pw=self._cam.conf.api.auth.password,
                host=urlsplit(self._cam.host).netloc,
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
