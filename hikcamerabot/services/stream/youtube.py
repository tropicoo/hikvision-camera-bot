"""YouTube Livestream module."""

from hikcamerabot.enums import Stream, VideoEncoder
from hikcamerabot.services.stream.abstract import (
    AbstractExternalLivestreamService,
)


class YouTubeStreamService(AbstractExternalLivestreamService):
    """YouTube Livestream Service Class."""

    name = Stream.YOUTUBE

    def _generate_transcode_cmd(
        self, cmd_tpl: str, cmd_transcode: str, enc_codec_name: VideoEncoder
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
        # urljoin does not support rtmp protocol
        return f'{self._stream_conf.url}/{self._stream_conf.key}'
