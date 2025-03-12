import asyncio
from typing import Literal

from hikcamerabot.config.schemas.main_config import DvrLivestreamConfSchema
from hikcamerabot.constants import (
    FFMPEG_CMD_DVR,
    FFMPEG_CMD_NULL_AUDIO,
    RTSP_TRANSPORT_TPL,
)
from hikcamerabot.enums import StreamType, VideoEncoderType
from hikcamerabot.services.stream.abstract import AbstractStreamService
from hikcamerabot.services.stream.dvr.upload.engine import DvrUploadEngine
from hikcamerabot.services.tasks.livestream import ServiceStreamerTask
from hikcamerabot.utils.task import create_task


class DvrStreamService(AbstractStreamService):
    NAME: Literal[StreamType.DVR] = StreamType.DVR
    _FFMPEG_CMD_TPL = FFMPEG_CMD_DVR
    _DVR_FILENAME_TPL: str = (
        '{storage_path}/{cam_id}_{channel}_{segment_time}_%Y-%m-%d_%H-%M-%S.mp4'
    )
    _conf: DvrLivestreamConfSchema

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._upload_engine = DvrUploadEngine(
            conf=self.cam.conf.livestream.dvr, cam=self.cam
        )
        self._upload_engine_started = False

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
            loglevel=self._enc_conf.loglevel,
            map=null_audio['map'],
            vcodec=self._enc_conf.vcodec,
            segment_time=self._stream_conf.segment_time,
        )

    async def start(self, *args, **kwargs) -> None:
        coros = [super().start(*args, **kwargs)]
        if not self._upload_engine_started:
            coros.append(self._start_upload_engine())
            self._upload_engine_started = True

        await asyncio.gather(*coros)

    async def _start_upload_engine(self) -> None:
        """Start Upload Engine only if at least one storage is enabled."""
        # TODO: Right now upload engine will start only if DVR records are set
        # TODO: to be deleted since there is no tracking for uploaded files.
        if (
            self._conf.upload.storage.is_any_upload_storage_enabled()
            and self.cam.conf.livestream.dvr.upload.delete_after_upload
        ):
            self._log.info(
                '[%s] Starting DVR Upload Engine for "%s"',
                self.cam.id,
                self.cam.description,
            )
            await self._upload_engine.start()
            return
        self._log.info('[%s] DVR Upload Engine not started', self.cam.id)

    def _start_stream_task(self) -> None:
        create_task(
            ServiceStreamerTask(service=self, run_forever=True).run(),
            task_name=ServiceStreamerTask.__name__,
            logger=self._log,
            exception_message='Task "%s" raised an exception',
            exception_message_args=(ServiceStreamerTask.__name__,),
        )

    def _generate_transcode_cmd(
        self, cmd_tpl: str, cmd_transcode: str, enc_codec_name: VideoEncoderType
    ) -> None:
        try:
            inner_args = self._cmd_gen_dispatcher[enc_codec_name]()
        except KeyError:
            inner_args = ''
        inner_args = cmd_transcode.format(inner_args=inner_args)
        self._cmd = cmd_tpl.format(
            output=self._generate_output(), inner_args=inner_args
        )

    def _generate_output(self) -> str:
        return self._DVR_FILENAME_TPL.format(
            storage_path=self.cam.conf.livestream.dvr.local_storage_path,
            cam_id=self.cam.id,
            channel=self._stream_conf.channel,
            segment_time=self._stream_conf.segment_time,
        )
