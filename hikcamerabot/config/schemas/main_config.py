from marshmallow import (
    INCLUDE, Schema, fields as f, validate as v,
    validates_schema,
)

from hikcamerabot.constants import (
    CMD_CAM_ID_REGEX, FFMPEG_LOG_LEVELS,
    RTSP_TRANSPORT_TYPES,
)


class LivestreamConf(Schema):
    enabled = f.Boolean(required=True)
    livestream_template = f.String(required=True, validate=v.Length(min=1))
    encoding_template = f.String(required=True, validate=v.Length(min=1))


class Livestream(Schema):
    youtube = f.Nested(LivestreamConf, required=True)
    icecast = f.Nested(LivestreamConf, required=True)
    twitch = f.Nested(LivestreamConf, required=False)


class Detection(Schema):
    enabled = f.Boolean(required=True)
    fullpic = f.Boolean(required=True)


class VideoGif(Schema):
    enabled = f.Boolean(required=True)
    channel = f.Integer(required=True)
    record_time = f.Integer(required=True, validate=v.Range(min=1))
    tmp_storage = f.String(required=True, validate=v.Length(min=1))
    loglevel = f.String(required=True, validate=v.OneOf(FFMPEG_LOG_LEVELS))
    rtsp_transport_type = f.String(required=False, validate=v.OneOf(RTSP_TRANSPORT_TYPES))


class Alert(Schema):
    delay = f.Integer(required=True, validate=v.Range(min=0))
    video_gif = f.Nested(VideoGif, required=True)
    motion_detection = f.Nested(Detection, required=True)
    line_crossing_detection = f.Nested(Detection, required=True)
    intrusion_detection = f.Nested(Detection, required=True)


class CamAPIAuth(Schema):
    user = f.String(required=True, validate=v.Length(min=1))
    password = f.String(required=True, validate=v.Length(min=1))


class CamAPI(Schema):
    host = f.String(required=True, validate=v.Length(min=1))
    auth = f.Nested(CamAPIAuth, required=True)
    stream_timeout = f.Integer(required=True, validate=v.Range(min=1))


class CamConfig(Schema):
    class _CamConfig(Schema):
        description = f.String(required=True, validate=v.Length(min=1))
        api = f.Nested(CamAPI, required=True)
        alert = f.Nested(Alert, required=True)
        livestream = f.Nested(Livestream, required=True)

        class Meta:
            ordered = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._inner_validation_schema = self._CamConfig()
        self._cam_id_validator = f.String(required=True, validate=v.Regexp(
            CMD_CAM_ID_REGEX,
            error=f'Check main config. Bad camera ID, example name: "cam_1"'))

    @validates_schema
    def validate_all(self, data: dict, **kwargs) -> None:
        for cam_id, cam_conf in data.items():
            self._cam_id_validator.validate(cam_id)
            self._inner_validation_schema.load(cam_conf)

    class Meta:
        unknown = INCLUDE
        ordered = True


class Watchdog(Schema):
    enabled = f.Boolean(required=True)
    directory = f.String(required=True, validate=v.Length(min=0))


class Telegram(Schema):
    token = f.String(required=True, validate=v.Length(min=1))
    allowed_user_ids = f.List(f.Integer(required=True), required=True,
                              validate=v.Length(min=1))


class MainConfig(Schema):
    APP_LOG_LEVELS = {'DEBUG', 'WARNING', 'INFO', 'ERROR', 'CRITICAL'}

    telegram = f.Nested(Telegram, required=True)
    watchdog = f.Nested(Watchdog, required=True)
    log_level = f.String(required=True, validate=v.OneOf(APP_LOG_LEVELS))
    camera_list = f.Nested(CamConfig, required=True)

    class Meta:
        ordered = True
