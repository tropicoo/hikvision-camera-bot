from typing import Literal
from urllib.parse import urlsplit

from hikcamerabot.constants import (
    FFMPEG_CMD_NULL_AUDIO,
    FFMPEG_CMD_SRS,
    SRS_DOCKER_CONTAINER_NAME,
    SRS_LIVESTREAM_NAME_TPL,
)
from hikcamerabot.enums import StreamType, VideoEncoderType
from hikcamerabot.services.stream.abstract import AbstractStreamService
from hikcamerabot.services.tasks.livestream import ServiceStreamerTask
from hikcamerabot.utils.shared import get_srs_server_ip_address
from hikcamerabot.utils.task import create_task


class SrsStreamService(AbstractStreamService):
    NAME: Literal[StreamType.SRS] = StreamType.SRS
    _FFMPEG_CMD_TPL: str = FFMPEG_CMD_SRS

    def _format_ffmpeg_cmd_tpl(self) -> str:
        null_audio = (
            FFMPEG_CMD_NULL_AUDIO
            if self._enc_conf.null_audio
            else dict.fromkeys(FFMPEG_CMD_NULL_AUDIO, '')
        )
        return self._FFMPEG_CMD_TPL.format(
            abitrate=null_audio['bitrate'],
            asample_rate=f'-ar {self._enc_conf.asample_rate}'
            if self._enc_conf.asample_rate != -1
            else '',
            acodec=self._enc_conf.acodec,
            channel=self._stream_conf.channel,
            filter=null_audio['filter'],
            format=self._enc_conf.format,
            host=urlsplit(self._hik_host).netloc,
            rtsp_port=self.cam.conf.rtsp_port,
            loglevel=self._enc_conf.loglevel,
            map=null_audio['map'],
            pw=self._hik_password,
            rtsp_transport_type=self._enc_conf.rtsp_transport_type,
            user=self._hik_user,
            vcodec=self._enc_conf.vcodec,
        )

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
        livestream_name = SRS_LIVESTREAM_NAME_TPL.format(
            channel=self._stream_conf.channel,
            cam_id=self.cam.id,
        )
        url = self._stream_conf.url.replace(
            SRS_DOCKER_CONTAINER_NAME, get_srs_server_ip_address()
        )
        return f'{url}/{livestream_name}'
