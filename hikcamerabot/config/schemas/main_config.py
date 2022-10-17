"""Marshmallow (sorry, no Pydantic) validation config schemas."""

from marshmallow import (
    INCLUDE,
    Schema,
    fields as f,
    validate as v,
    validates_schema,
)

from hikcamerabot.config.schemas.validators import int_min_1, non_empty_str
from hikcamerabot.constants import (
    CMD_CAM_ID_REGEX,
    FFMPEG_LOG_LEVELS,
)
from hikcamerabot.enums import RtspTransportType


class LivestreamConf(Schema):
    enabled = f.Boolean(required=True)
    livestream_template = f.Str(required=True, validate=non_empty_str)
    encoding_template = f.Str(required=True, validate=non_empty_str)


class TelegramDvrUploadConf(Schema):
    enabled = f.Boolean(required=True)
    group_id = f.Int(required=True, allow_none=True)


class DvrUploadStorageConf(Schema):
    telegram = f.Nested(TelegramDvrUploadConf(), required=True)


class DvrUploadConf(Schema):
    delete_after_upload = f.Boolean(required=True)
    storage = f.Nested(DvrUploadStorageConf(), required=True)


class DvrLivestreamConf(LivestreamConf):
    local_storage_path = f.Str(required=True, validate=non_empty_str)
    upload = f.Nested(DvrUploadConf(), required=True)


class Livestream(Schema):
    srs = f.Nested(LivestreamConf(), required=True)
    dvr = f.Nested(DvrLivestreamConf(), required=True)
    youtube = f.Nested(LivestreamConf(), required=True)
    telegram = f.Nested(LivestreamConf(), required=True)
    icecast = f.Nested(LivestreamConf(), required=True)


class Detection(Schema):
    enabled = f.Boolean(required=True)
    sendpic = f.Boolean(required=True)
    fullpic = f.Boolean(required=True)
    send_videogif = f.Boolean(required=True)


class VideoGifOnDemand(Schema):
    channel = f.Int(required=True)
    record_time = f.Int(required=True, validate=int_min_1)
    rewind_time = f.Int(required=True, validate=int_min_1)
    tmp_storage = f.Str(required=True, validate=non_empty_str)
    loglevel = f.Str(required=True, validate=v.OneOf(FFMPEG_LOG_LEVELS))
    rtsp_transport_type = f.Str(
        required=True, validate=v.OneOf(RtspTransportType.choices())
    )


class VideoGifOnAlert(VideoGifOnDemand):
    rewind = f.Boolean(required=True)


class VideoGif(Schema):
    on_alert = f.Nested(VideoGifOnAlert(), required=True)
    on_demand = f.Nested(VideoGifOnDemand(), required=True)


class Alert(Schema):
    delay = f.Int(required=True, validate=v.Range(min=0))
    motion_detection = f.Nested(Detection(), required=True)
    line_crossing_detection = f.Nested(Detection(), required=True)
    intrusion_detection = f.Nested(Detection(), required=True)


class CamAPIAuth(Schema):
    user = f.Str(required=True, validate=non_empty_str)
    password = f.Str(required=True, validate=non_empty_str)


class CamAPI(Schema):
    host = f.Str(required=True, validate=non_empty_str)
    port = f.Int(required=True, validate=int_min_1)
    auth = f.Nested(CamAPIAuth(), required=True)
    stream_timeout = f.Int(required=True, validate=int_min_1)


class CmdSectionsVisibility(Schema):
    general = f.Boolean(required=True)
    infrared = f.Boolean(required=True)
    motion_detection = f.Boolean(required=True)
    line_detection = f.Boolean(required=True)
    intrusion_detection = f.Boolean(required=True)
    alert_service = f.Boolean(required=True)
    stream_youtube = f.Boolean(required=True)
    stream_telegram = f.Boolean(required=True)
    stream_icecast = f.Boolean(required=True)


class CameraListConfig(Schema):
    class _CameraListConfig(Schema):
        hidden = f.Boolean(required=True)
        description = f.Str(required=True, validate=non_empty_str)
        hashtag = f.Str(required=True, allow_none=True)
        group = f.Str(required=True, allow_none=True)
        api = f.Nested(CamAPI(), required=True)
        rtsp_port = f.Int(required=True)
        video_gif = f.Nested(VideoGif(), required=True)
        alert = f.Nested(Alert(), required=True)
        livestream = f.Nested(Livestream(), required=True)
        command_sections_visibility = f.Nested(CmdSectionsVisibility(), required=True)

        class Meta:
            ordered = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._inner_validation_schema = self._CameraListConfig()
        self._cam_id_validator = f.Str(
            required=True,
            validate=v.Regexp(
                CMD_CAM_ID_REGEX,
                error='Check main config. Bad camera ID syntax, example: "cam_1"',
            ),
        )

    @validates_schema
    def validate_all(self, data: dict[str, dict], **kwargs) -> None:
        for cam_id, cam_conf in data.items():
            self._cam_id_validator.validate(cam_id)
            self._inner_validation_schema.load(cam_conf)

    class Meta:
        unknown = INCLUDE
        ordered = True


class Telegram(Schema):
    api_id = f.Int(required=True, validate=int_min_1)
    api_hash = f.Str(required=True, validate=non_empty_str)
    lang_code = f.Str(required=True, validate=non_empty_str)
    token = f.Str(required=True, validate=non_empty_str)
    chat_users = f.List(f.Int(required=True), required=True, validate=non_empty_str)
    alert_users = f.List(f.Int(required=True), required=True, validate=non_empty_str)
    startup_message_users = f.List(f.Int(required=True), required=True)


class MainConfig(Schema):
    _APP_LOG_LEVELS = {'DEBUG', 'WARNING', 'INFO', 'ERROR', 'CRITICAL'}

    telegram = f.Nested(Telegram(), required=True)
    log_level = f.Str(required=True, validate=v.OneOf(_APP_LOG_LEVELS))
    camera_list = f.Nested(CameraListConfig(), required=True)

    class Meta:
        ordered = True
