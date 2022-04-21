import abc
import asyncio
import os
import signal
import time
from typing import Callable, Optional, TYPE_CHECKING
from urllib.parse import urlsplit

from addict import Dict

from hikcamerabot.config.config import (
    get_encoding_tpl_config,
    get_livestream_tpl_config,
)
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
    ServiceType,
    Stream,
    VideoEncoder,
)
from hikcamerabot.exceptions import ServiceConfigError, ServiceRuntimeError
from hikcamerabot.services.abstract import AbstractService
from hikcamerabot.services.tasks.livestream import (
    FfmpegStdoutReaderTask,
    ServiceStreamerTask,
)
from hikcamerabot.utils.task import create_task, wrap
from hikcamerabot.utils.utils import shallow_sleep_async

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam


class AbstractStreamService(AbstractService, metaclass=abc.ABCMeta):
    """livestream Service Base Class."""

    name: Optional[Stream] = None
    type = ServiceType.STREAM

    _FFMPEG_CMD_TPL: Optional[str] = None
    _IGNORE_RESTART_CHECK = -1

    def __init__(
        self,
        conf: Dict,
        hik_user: str,
        hik_password: str,
        hik_host: str,
        cam: 'HikvisionCam',
    ):
        super().__init__(cam)

        self._cmd_gen_dispatcher: dict[VideoEncoder, Callable[[], str]] = {
            VideoEncoder.X264: self._generate_x264_cmd,
            VideoEncoder.VP9: self._generate_vp9_cmd,
        }

        self._conf = conf
        self._hik_user = hik_user
        self._hik_password = hik_password
        self._hik_host = hik_host

        self._proc: Optional[asyncio.subprocess.Process] = None
        self._start_ts: Optional[int] = None
        self._stream_conf: Optional[Dict] = None
        self._enc_conf: Optional[Dict] = None
        self._cmd: Optional[str] = None
        self._generate_cmd()

        self._started = asyncio.Event()
        self._killpg = wrap(os.killpg)

    async def start(self, skip_check: bool = False) -> None:
        """Start the stream."""
        if not skip_check and self.started:
            msg = f'{self._cls_name} stream already started'
            self._log.warning(msg)
            raise ServiceRuntimeError(msg)

        await self._start_ffmpeg_process()
        self._start_reader_task()
        if not skip_check:
            self._start_stream_task()

    @property
    def _srs_enabled(self) -> bool:
        """If SRS Stream enabled in conf, it will used as input video source."""
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
            exception_message='Task %s raised an exception',
            exception_message_args=(FfmpegStdoutReaderTask.__name__,),
        )

    def _start_stream_task(self) -> None:
        create_task(
            ServiceStreamerTask(service=self).run(),
            task_name=ServiceStreamerTask.__name__,
            logger=self._log,
            exception_message='Task %s raised an exception',
            exception_message_args=(ServiceStreamerTask.__name__,),
        )

    async def _start_ffmpeg_process(self) -> None:
        self._log.debug('%s ffmpeg command: %s', self._cls_name, self._cmd)
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
            warn_msg = f'{self._cls_name} already stopped'
            self._log.warning(warn_msg)
            raise ServiceRuntimeError(warn_msg)
        try:
            self._log.info('Killing proc')
            await self._killpg(os.getpgid(self._proc.pid), signal.SIGINT)
        except ProcessLookupError as err:
            self._log.error('Failed to kill process: %s', err)
        except Exception:
            err_msg = f'Failed to kill/disable {self.name.value.capitalize()} stream'
            self._log.exception(err_msg)
            raise ServiceRuntimeError(err_msg)

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
        self._log.debug('Sleeping for %ss', self._stream_conf.restart_pause)
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
            tpl_name_ls: str = self._conf.livestream_template
            enc_codec_name, tpl_name_enc = self._conf.encoding_template.split('.')
        except ValueError:
            err_msg = f'Failed to load {self._cls_name} templates'
            self._log.error(err_msg)
            raise ServiceConfigError(err_msg)

        self._stream_conf = get_livestream_tpl_config()[self.name.value][tpl_name_ls]
        self._enc_conf = get_encoding_tpl_config()[enc_codec_name][tpl_name_enc]

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
            cmd_tpl, cmd_transcode, VideoEncoder(enc_codec_name)
        )

    @abc.abstractmethod
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
        return FFMPEG_CMD_TRANSCODE[VideoEncoder.X264].format(
            preset=self._enc_conf.preset, tune=self._enc_conf.tune
        )

    def _generate_vp9_cmd(self) -> str:
        return FFMPEG_CMD_TRANSCODE[VideoEncoder.VP9].format(
            deadline=self._enc_conf.deadline, speed=self._enc_conf.speed
        )

    @abc.abstractmethod
    def _generate_transcode_cmd(
        self, cmd_tpl, cmd_transcode, enc_codec_name: VideoEncoder
    ) -> str:
        # Example: self._cmd = cmd_tpl.format(...)
        pass


class AbstractExternalLivestreamService(AbstractStreamService):
    _FFMPEG_CMD_TPL = FFMPEG_CMD_LIVESTREAM

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
