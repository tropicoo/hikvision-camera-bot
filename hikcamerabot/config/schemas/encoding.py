from typing import Literal

from hikcamerabot.config.schemas.abstract import StrictBaseModel
from hikcamerabot.config.schemas.types_ import (
    FfmpegLogLevel,
    IntMin1,
    IntMinus1,
)
from hikcamerabot.enums import RtspTransportType


class DirectSchema(StrictBaseModel):
    null_audio: bool
    loglevel: FfmpegLogLevel
    vcodec: str
    acodec: str
    asample_rate: IntMinus1
    format: str
    rtsp_transport_type: RtspTransportType


class X264ScaleSchema(StrictBaseModel):
    enabled: bool
    width: int
    height: int
    format: str


class X264Schema(StrictBaseModel):
    null_audio: bool
    loglevel: FfmpegLogLevel
    vcodec: str
    acodec: str
    asample_rate: IntMinus1
    format: str
    rtsp_transport_type: str
    pix_fmt: str
    pass_mode: IntMin1
    framerate: IntMin1
    preset: str
    average_bitrate: str
    maxrate: str
    bufsize: str
    tune: str
    scale: X264ScaleSchema


class Vp9ScaleSchema(StrictBaseModel):
    enabled: bool
    width: IntMin1
    height: int
    format: str


class Vp9Schema(StrictBaseModel):
    null_audio: bool
    loglevel: FfmpegLogLevel
    vcodec: str
    acodec: str
    asample_rate: IntMinus1
    format: str
    rtsp_transport_type: str
    pix_fmt: str
    pass_mode: IntMin1
    framerate: IntMin1
    average_bitrate: str
    maxrate: str
    bufsize: str
    deadline: str
    speed: IntMin1
    scale: Vp9ScaleSchema


class EncodingTemplatesSchema(StrictBaseModel):
    direct: dict[str, DirectSchema]
    x264: dict[str, X264Schema]
    vp9: dict[str, Vp9Schema]

    def get_by_template_name(
        self, name: Literal['direct', 'x264', 'vp9']
    ) -> dict[str, DirectSchema | X264Schema | Vp9Schema]:
        try:
            return getattr(self, name)
        except AttributeError:
            raise ValueError(f'Invalid template name: {name}') from None
