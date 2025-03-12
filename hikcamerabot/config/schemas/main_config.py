from abc import ABC
from collections.abc import Generator
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import DirectoryPath, Field, field_validator, model_validator

from hikcamerabot.clients.hikvision.enums import AuthType
from hikcamerabot.config.schemas.abstract import StrictBaseModel
from hikcamerabot.config.schemas.types_ import (
    DvrStorageType,
    FfmpegLogLevel,
    IntMin0,
    IntMin1,
    PythonLogLevel,
    TimezoneType,
)
from hikcamerabot.constants import CMD_CAM_ID_REGEX, DAY_HOURS_RANGE
from hikcamerabot.enums import FfmpegPixFmt, FfmpegVideoCodecType, RtspTransportType


class LivestreamConfSchema(StrictBaseModel):
    enabled: bool
    livestream_template: str
    encoding_template: str


class BaseDVRStorageUploadConfSchema(StrictBaseModel, ABC):
    enabled: bool
    group_id: int | None

    @model_validator(mode='after')
    def validate_group_id(self) -> Self:
        if self.enabled and self.group_id is None:
            raise ValueError('Group ID must be set when storage is enabled')
        return self


class TelegramDvrUploadConfSchema(BaseDVRStorageUploadConfSchema):
    pass


class DvrUploadStorageConfSchema(StrictBaseModel):
    telegram: TelegramDvrUploadConfSchema

    def is_any_upload_storage_enabled(self) -> bool:
        return any(
            getattr(self, storage_name).enabled
            for storage_name in self.model_fields_set
        )

    def get_storage_items(
        self,
    ) -> Generator[tuple[DvrStorageType, BaseDVRStorageUploadConfSchema]]:
        storage_name: DvrStorageType
        for storage_name in self.model_fields_set:
            yield storage_name, getattr(self, storage_name)

    def get_storage_conf_by_type(
        self, type_: DvrStorageType
    ) -> BaseDVRStorageUploadConfSchema:
        try:
            return getattr(self, type_)
        except AttributeError as err:
            raise ValueError(f'Invalid storage type: {type_}') from err


class DvrUploadConfSchema(StrictBaseModel):
    delete_after_upload: bool
    storage: DvrUploadStorageConfSchema


class DvrLivestreamConfSchema(LivestreamConfSchema):
    local_storage_path: Path
    upload: DvrUploadConfSchema


class LivestreamSchema(StrictBaseModel):
    srs: LivestreamConfSchema
    dvr: DvrLivestreamConfSchema
    youtube: LivestreamConfSchema
    telegram: LivestreamConfSchema
    icecast: LivestreamConfSchema


class VideoGifOnDemandSchema(StrictBaseModel):
    channel: int
    record_time: IntMin1
    rewind_time: IntMin1
    tmp_storage: Path
    loglevel: FfmpegLogLevel
    rtsp_transport_type: RtspTransportType


class VideoGifOnAlertSchema(VideoGifOnDemandSchema):
    rewind: bool


class VideoGifSchema(StrictBaseModel):
    on_alert: VideoGifOnAlertSchema
    on_demand: VideoGifOnDemandSchema

    def get_schema_by_type(
        self, type_: Literal['on_alert', 'on_demand']
    ) -> VideoGifOnDemandSchema | VideoGifOnAlertSchema:
        try:
            return getattr(self, type_)
        except AttributeError as err:
            raise ValueError(f'Invalid VideoGifType: {type_}') from err


class PictureOnAlertSchema(StrictBaseModel):
    channel: int


class PictureOnDemandSchema(PictureOnAlertSchema):
    pass


class PictureSchema(StrictBaseModel):
    on_alert: PictureOnAlertSchema
    on_demand: PictureOnDemandSchema


class DetectionSchema(StrictBaseModel):
    enabled: bool
    sendpic: bool
    fullpic: bool
    send_videogif: bool
    send_text: bool


class AlertSchema(StrictBaseModel):
    delay: IntMin0
    motion_detection: DetectionSchema
    line_crossing_detection: DetectionSchema
    intrusion_detection: DetectionSchema

    def get_detection_schema_by_type(
        self,
        type_: Literal[
            'motion_detection', 'line_crossing_detection', 'intrusion_detection'
        ],
    ) -> DetectionSchema:
        try:
            return getattr(self, type_)
        except AttributeError:
            raise ValueError(f'Invalid Detection: {type_}') from None


class CamAPIAuthSchema(StrictBaseModel):
    user: str
    password: str
    type: AuthType


class CamAPISchema(StrictBaseModel):
    host: str
    port: IntMin1
    auth: CamAPIAuthSchema
    stream_timeout: IntMin1


class CmdSectionsVisibilitySchema(StrictBaseModel):
    general: bool
    infrared: bool
    motion_detection: bool
    line_detection: bool
    intrusion_detection: bool
    alert_service: bool
    stream_youtube: bool
    stream_telegram: bool
    stream_icecast: bool


class NvrSchema(StrictBaseModel):
    is_behind: bool
    channel_name: str | None

    @model_validator(mode='after')
    def validate_nvr(self) -> Self:
        if self.is_behind and self.channel_name is None:
            raise ValueError('When camera is behind NVR, channel name must be set')
        return self


class TimelapseSchema(StrictBaseModel):
    enabled: bool
    name: str
    start_hour: IntMin0
    end_hour: IntMin0
    snapshot_period: IntMin1
    video_length: IntMin1
    video_framerate: IntMin1
    channel: IntMin1
    timezone: TimezoneType
    tmp_storage: DirectoryPath
    storage: DirectoryPath
    keep_stills: bool
    ffmpeg_log_level: FfmpegLogLevel
    image_quality: IntMin0
    video_codec: FfmpegVideoCodecType
    pix_fmt: FfmpegPixFmt
    custom_ffmpeg_args: str | None
    nice_value: int | None
    threads: IntMin1 | None

    @field_validator('start_hour', 'end_hour')
    @classmethod
    def validate_start_end_hour(cls, value: int) -> int:
        if value not in DAY_HOURS_RANGE:
            raise ValueError(f'Invalid hour: {value}')
        return value

    @field_validator('custom_ffmpeg_args')
    @classmethod
    def validate_custom_ffmpeg_args(cls, value: str | None) -> str:
        if value is None:
            return ''
        return value


class CameraConfigSchema(StrictBaseModel):
    hidden: bool
    description: str
    hashtag: str | None
    group: str | None
    api: CamAPISchema
    rtsp_port: int
    nvr: NvrSchema
    timelapse: list[TimelapseSchema]
    picture: PictureSchema
    video_gif: VideoGifSchema
    alert: AlertSchema
    livestream: LivestreamSchema
    command_sections_visibility: CmdSectionsVisibilitySchema


class TelegramSchema(StrictBaseModel):
    api_id: IntMin1
    api_hash: str
    lang_code: str
    token: str
    chat_users: list[int]
    alert_users: list[int]
    startup_message_users: list[int]


class MainConfigSchema(StrictBaseModel):
    telegram: TelegramSchema
    log_level: PythonLogLevel
    camera_list: dict[
        Annotated[str, Field(pattern=CMD_CAM_ID_REGEX)], CameraConfigSchema
    ]
