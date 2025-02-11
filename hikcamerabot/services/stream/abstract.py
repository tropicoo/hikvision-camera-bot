import asyncio
import os
import signal
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlsplit

from hikcamerabot.config.config import encoding_conf, livestream_conf
from hikcamerabot.config.schemas.main_config import LivestreamConfSchema
from hikcamerabot.constants import (
    FFMPEG_CAM_VIDEO_SRC,
    FFMPEG_CMD_LIVESTREAM,
    FFMPEG_CMD_NULL_AUDIO,
    FFMPEG_CMD_SCALE_FILTER,
    FFMPEG_CMD_TRANSCODE,
    FFMPEG_CMD_TRANSCODE_GENERAL,
    FFMPEG_SRS_RTMP_VIDEO_SRC,
    RTSP_TRANSPORT_TPL,
    SRS_LIVESTREAM_NAME_TPL,
)
from hikcamerabot.enums import ServiceType, StreamType, VideoEncoderType
from hikcamerabot.exceptions import ServiceConfigError, ServiceRuntimeError
from hikcamerabot.services.abstract import AbstractService
from hikcamerabot.services.tasks.livestream import (
    FfmpegStdoutReaderTask,
    ServiceStreamerTask,
)
from hikcamerabot.utils.process import kill_proc
from hikcamerabot.utils.shared import shallow_sleep_async
from hikcamerabot.utils.task import create_task

if TYPE_CHECKING:
    from collections.abc import Callable

    from hikcamerabot.camera import HikvisionCam


class AbstractStreamService(AbstractService, ABC):
    """livestream Service Base Class."""

    NAME: StreamType | None = None
    TYPE: Literal[ServiceType.STREAM] = ServiceType.STREAM

    _FFMPEG_CMD_TPL: str | None = None
    _IGNORE_RESTART_CHECK: int = -1

    def __init__(
        self,
        conf: LivestreamConfSchema,
        hik_user: str,
        hik_password: str,
        hik_host: str,
        cam: 'HikvisionCam',
    ) -> None:
        super().__init__(cam)

        self._cmd_gen_dispatcher: dict[VideoEncoderType, Callable[[], str]] = {
            VideoEncoderType.X264: self._generate_x264_cmd,
            VideoEncoderType.VP9: self._generate_vp9_cmd,
        }

        self._conf = conf
        self._hik_user = hik_user
        self._hik_password = hik_password
        self._hik_host = hik_host

        self._proc: asyncio.subprocess.Process | None = None
        self._start_ts: int | None = None

        # TODO: Set type hints.
        self._stream_conf: None = None
        self._enc_conf: None = None

        self._cmd: str | None = None
        self._generate_cmd()

        self._started = asyncio.Event()

    async def start(self, skip_check: bool = False) -> None:
        """Start the stream."""
        if not skip_check and self.started:
            warn_msg = f'{self._get_cap_service_name()} stream already started'
            self._log.warning(warn_msg)
            raise ServiceRuntimeError(warn_msg)

        await self._start_ffmpeg_process()
        self._start_reader_task()
        if not skip_check:
            self._start_stream_task()

    def _get_cap_service_name(self) -> str:
        """Get capitalized service name, e.g. "TELEGRAM" -> "Telegram"."""
        return self.NAME.value.capitalize()

    @property
    def _srs_enabled(self) -> bool:
        """If SRS StreamType enabled in conf, it will be used as input video source."""
        return self.cam.conf.livestream.srs.enabled

    def _generate_video_source(self) -> str:
        """From direct cam video source or SRS."""
        if self._srs_enabled:
            return FFMPEG_SRS_RTMP_VIDEO_SRC.format(
                livestream_name=SRS_LIVESTREAM_NAME_TPL.format(
                    channel=self._stream_conf.channel,
                    cam_id=self.cam.id,
                )
            )
        return FFMPEG_CAM_VIDEO_SRC.format(
            user=self._hik_user,
            pw=self._hik_password,
            host=urlsplit(self._hik_host).netloc,
            rtsp_port=self.cam.conf.rtsp_port,
            channel=self._stream_conf.channel,
        )

    def _start_reader_task(self) -> None:
        create_task(
            FfmpegStdoutReaderTask(self._proc, self._cmd).run(),
            task_name=FfmpegStdoutReaderTask.__name__,
            logger=self._log,
            exception_message='Task "%s" raised an exception',
            exception_message_args=(FfmpegStdoutReaderTask.__name__,),
        )

    def _start_stream_task(self) -> None:
        create_task(
            ServiceStreamerTask(service=self).run(),
            task_name=ServiceStreamerTask.__name__,
            logger=self._log,
            exception_message='Task "%s" raised an exception',
            exception_message_args=(ServiceStreamerTask.__name__,),
        )

    async def _start_ffmpeg_process(self) -> None:
        self._log.debug('%s ffmpeg command: "%s"', self._cls_name, self._cmd)
        try:
            self._proc = await asyncio.create_subprocess_shell(
                self._cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                preexec_fn=os.setsid,
            )
        except Exception as err:
            err_msg = f'{self._cls_name} failed to start'
            self._log.exception(err_msg)
            raise ServiceRuntimeError(err_msg) from err
        self._start_ts = int(time.time())
        self._started.set()

    async def stop(self, disable: bool = True) -> None:
        """Stop the stream."""
        if not self.started:
            warn_msg = f'{self._get_cap_service_name()} stream already stopped'
            self._log.warning(warn_msg)
            raise ServiceRuntimeError(warn_msg)
        try:
            self._log.info('Killing proc')
            await kill_proc(process=self._proc, signal_=signal.SIGINT, reraise=True)
        except ProcessLookupError as err:
            self._log.error('Failed to kill process: %s', err)
        except Exception as err:
            err_msg = f'Failed to kill/disable {self.NAME.value} stream'
            self._log.exception(err_msg)
            raise ServiceRuntimeError(err_msg) from err

        if disable:
            self._started.clear()

    @property
    def need_restart(self) -> bool:
        """Check if the stream needs to be restarted."""
        if self._stream_conf.restart_period == self._IGNORE_RESTART_CHECK:
            return False
        return int(time.time()) > self._start_ts + self._stream_conf.restart_period

    async def restart(self) -> None:
        """Restart the stream."""
        if self.started:
            await self.stop(disable=False)
        self._log.debug(
            '[%s] Restarting service %s. Sleeping for %ss',
            self.cam.id,
            self._cls_name,
            self._stream_conf.restart_pause,
        )
        await shallow_sleep_async(self._stream_conf.restart_pause)
        await self.start(skip_check=True)

    @property
    def enabled_in_conf(self) -> bool:
        """Check if stream is enabled in configuration."""
        return self._conf.enabled

    @property
    def started(self) -> bool:
        """Check if stream is started."""
        return self._started.is_set()

    @property
    def alive(self) -> bool:
        """Check whether the stream (ffmpeg process) is still running."""
        return self._proc.returncode is None

    def _generate_cmd(self) -> None:
        try:
            tpl_name_ls = self._conf.livestream_template
            enc_codec_name, tpl_name_enc = self._conf.encoding_template.split('.')
        except ValueError as err:
            err_msg = f'Failed to load {self._cls_name} templates'
            self._log.error(err_msg)
            raise ServiceConfigError(err_msg) from err

        self._stream_conf = livestream_conf.get_tpl_by_name(name=self.NAME)[tpl_name_ls]
        self._enc_conf = encoding_conf.get_by_template_name(name=enc_codec_name)[
            tpl_name_enc
        ]

        cmd_tpl = self._format_ffmpeg_cmd_tpl()

        cmd_transcode = ''
        if enc_codec_name in FFMPEG_CMD_TRANSCODE:
            cmd_transcode = FFMPEG_CMD_TRANSCODE_GENERAL.format(
                average_bitrate=self._enc_conf.average_bitrate,
                bufsize=self._enc_conf.bufsize,
                framerate=self._enc_conf.framerate,
                maxrate=self._enc_conf.maxrate,
                pass_mode=self._enc_conf.pass_mode,
                pix_fmt=self._enc_conf.pix_fmt,
                scale=self._generate_scale_cmd(),
            )

        self._generate_transcode_cmd(
            cmd_tpl=cmd_tpl,
            cmd_transcode=cmd_transcode,
            enc_codec_name=VideoEncoderType(enc_codec_name),
        )

    @abstractmethod
    def _format_ffmpeg_cmd_tpl(self) -> str:
        pass

    def _generate_scale_cmd(self) -> str:
        return (
            FFMPEG_CMD_SCALE_FILTER.format(
                width=self._enc_conf.scale.width,
                height=self._enc_conf.scale.height,
                format=self._enc_conf.scale.format,
            )
            if self._enc_conf.scale.enabled
            else ''
        )

    def _generate_x264_cmd(self) -> str:
        return FFMPEG_CMD_TRANSCODE[VideoEncoderType.X264].format(
            preset=self._enc_conf.preset, tune=self._enc_conf.tune
        )

    def _generate_vp9_cmd(self) -> str:
        return FFMPEG_CMD_TRANSCODE[VideoEncoderType.VP9].format(
            deadline=self._enc_conf.deadline, speed=self._enc_conf.speed
        )

    @abstractmethod
    def _generate_transcode_cmd(
        self, cmd_tpl: str, cmd_transcode: str, enc_codec_name: VideoEncoderType
    ) -> str:
        # Example: self._cmd = cmd_tpl.format(...)
        pass


class AbstractExternalLivestreamService(AbstractStreamService, ABC):
    _FFMPEG_CMD_TPL: str = FFMPEG_CMD_LIVESTREAM

    def _format_ffmpeg_cmd_tpl(self) -> str:
        null_audio = (
            FFMPEG_CMD_NULL_AUDIO
            if self._enc_conf.null_audio
            else {k: '' for k in FFMPEG_CMD_NULL_AUDIO}
        )
        return self._FFMPEG_CMD_TPL.format(
            abitrate=null_audio['bitrate'],
            asample_rate=f'-ar {self._enc_conf.asample_rate}'
            if self._enc_conf.asample_rate != -1
            else '',
            acodec=self._enc_conf.acodec,
            rtsp_transport=RTSP_TRANSPORT_TPL.format(
                rtsp_transport_type=self._enc_conf.rtsp_transport_type
            )
            if not self._srs_enabled
            else '',
            video_source=self._generate_video_source(),
            filter=null_audio['filter'],
            format=self._enc_conf.format,
            loglevel=self._enc_conf.loglevel,
            map=null_audio['map'],
            vcodec=self._enc_conf.vcodec,
        )
