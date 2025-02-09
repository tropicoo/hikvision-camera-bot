"""Telegram Livestream module."""

from typing import Literal

from hikcamerabot.enums import StreamType, VideoEncoderType
from hikcamerabot.services.stream.abstract import (
    AbstractExternalLivestreamService,
)


class TelegramStreamService(AbstractExternalLivestreamService):
    """Telegram Livestream Service Class."""

    NAME: Literal[StreamType.TELEGRAM] = StreamType.TELEGRAM

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
        # urljoin does not support rtmp protocol
        return f'{self._stream_conf.url}/{self._stream_conf.key}'
