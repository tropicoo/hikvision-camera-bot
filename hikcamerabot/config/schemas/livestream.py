from hikcamerabot.config.schemas._types import IntMin0, IntMin1, IntMinus1
from hikcamerabot.config.schemas.abstract import StrictBaseModel
from hikcamerabot.enums import StreamType


class YoutubeSchema(StrictBaseModel):
    channel: IntMin1
    restart_period: IntMin1
    restart_pause: IntMin0
    url: str
    key: str


class TelegramSchema(StrictBaseModel):
    channel: IntMin1
    restart_period: IntMin1
    restart_pause: IntMin0
    url: str
    key: str


class SrsSchema(StrictBaseModel):
    channel: IntMin1
    sub_channel: IntMin1
    restart_period: IntMinus1
    restart_pause: IntMin0
    url: str


class DvrSchema(StrictBaseModel):
    channel: IntMin1
    sub_channel: IntMin1
    restart_period: IntMinus1
    restart_pause: IntMin0
    segment_time: IntMin1


class IceStreamSchema(StrictBaseModel):
    ice_genre: str
    ice_name: str
    ice_description: str
    ice_public: int
    url: str
    password: str
    content_type: str


class IcecastSchema(StrictBaseModel):
    channel: IntMin1
    restart_period: IntMin1
    restart_pause: IntMin0
    ice_stream: IceStreamSchema


type LiveStreamTplType = dict[
    str, YoutubeSchema | TelegramSchema | IcecastSchema | SrsSchema | DvrSchema
]


class LivestreamTemplatesSchema(StrictBaseModel):
    youtube: dict[str, YoutubeSchema]
    telegram: dict[str, TelegramSchema]
    icecast: dict[str, IcecastSchema]
    srs: dict[str, SrsSchema]
    dvr: dict[str, DvrSchema]

    def get_tpl_by_name(self, name: StreamType) -> LiveStreamTplType:
        try:
            return getattr(self, name.value.lower())
        except AttributeError:
            raise ValueError(f'No template with name {name}') from None
