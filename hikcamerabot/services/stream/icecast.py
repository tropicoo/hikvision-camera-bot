"""Icecast Livestream module."""

from hikcamerabot.constants import (
    FFMPEG_CMD_TRANSCODE_ICECAST,
)
from hikcamerabot.enums import Stream, VideoEncoder
from hikcamerabot.exceptions import ServiceConfigError
from hikcamerabot.services.stream.abstract import (
    AbstractExternalLivestreamService,
)


class IcecastStreamService(AbstractExternalLivestreamService):
    """Icecast livestream Class."""

    name = Stream.ICECAST

    def _generate_transcode_cmd(
        self, cmd_tpl: str, cmd_transcode: str, enc_codec_name: VideoEncoder
    ) -> None:
        try:
            inner_args = self._cmd_gen_dispatcher[enc_codec_name]()
        except KeyError:
            raise ServiceConfigError(
                f'{self._cls_name} does not support {enc_codec_name} streaming,'
                f' change template type'
            )
        icecast_args = FFMPEG_CMD_TRANSCODE_ICECAST.format(
            ice_genre=self._stream_conf.ice_stream.ice_genre,
            ice_name=self._stream_conf.ice_stream.ice_name,
            ice_description=self._stream_conf.ice_stream.ice_description,
            ice_public=self._stream_conf.ice_stream.ice_public,
            content_type=self._stream_conf.ice_stream.content_type,
            password=self._stream_conf.ice_stream.password,
        )
        self._cmd = cmd_tpl.format(
            output=self._stream_conf.ice_stream.url,
            inner_args=' '.join(
                [cmd_transcode.format(inner_args=inner_args), icecast_args]
            ),
        )
