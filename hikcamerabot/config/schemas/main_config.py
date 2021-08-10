from marshmallow import (
    INCLUDE, Schema, fields as f, validate as v, validates_schema,
)

from hikcamerabot.config.schemas.validators import int_min_1, non_empty_str
from hikcamerabot.constants import (
    CMD_CAM_ID_REGEX, Detection as DetectionMode,
    FFMPEG_LOG_LEVELS, RTSP_DEFAULT_PORT, RTSP_TRANSPORT_TYPES,
)


class LivestreamConf(Schema):
    enabled = f.Boolean(required=True)
    livestream_template = f.Str(required=True, validate=non_empty_str)
    encoding_template = f.Str(required=True, validate=non_empty_str)


class Livestream(Schema):
    youtube = f.Nested(LivestreamConf, required=True)
    icecast = f.Nested(LivestreamConf, required=True)
    twitch = f.Nested(LivestreamConf, required=False)


class Detection(Schema):
    enabled = f.Boolean(required=True)
    sendpic = f.Boolean(required=False, load_default=True)
    fullpic = f.Boolean(required=True)


class VideoGif(Schema):
    enabled = f.Boolean(required=True)
    channel = f.Int(required=True)
    record_time = f.Int(required=True, validate=int_min_1)
    tmp_storage = f.Str(required=True, validate=non_empty_str)
    loglevel = f.Str(required=True, validate=v.OneOf(FFMPEG_LOG_LEVELS))
    rtsp_transport_type = f.Str(required=True, validate=v.OneOf(RTSP_TRANSPORT_TYPES))


class Alert(Schema):
    delay = f.Int(required=True, validate=v.Range(min=0))
    video_gif = f.Nested(VideoGif, required=True)
    motion_detection = f.Nested(Detection, required=True)
    line_crossing_detection = f.Nested(Detection, required=True)
    intrusion_detection = f.Nested(Detection, required=True)


class CamAPIAuth(Schema):
    user = f.Str(required=True, validate=non_empty_str)
    password = f.Str(required=True, validate=non_empty_str)


class CamAPI(Schema):
    host = f.Str(required=True, validate=non_empty_str)
    auth = f.Nested(CamAPIAuth, required=True)
    stream_timeout = f.Int(required=True, validate=int_min_1)


class CamConfig(Schema):
    class _CamConfig(Schema):
        description = f.Str(required=True, validate=non_empty_str)
        hashtag = f.Str(required=False, allow_none=False, load_default='')
        api = f.Nested(CamAPI, required=True)
        rtsp_port = f.Int(required=True)
        alert = f.Nested(Alert, required=True)
        livestream = f.Nested(Livestream, required=True)

        class Meta:
            ordered = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._inner_validation_schema = self._CamConfig()
        self._cam_id_validator = f.Str(required=True, validate=v.Regexp(
            CMD_CAM_ID_REGEX,
            error=f'Check main config. Bad camera ID, example name: "cam_1"'))

    @validates_schema
    def validate_all(self, data: dict, **kwargs) -> None:
        for cam_id, cam_conf in data.items():
            self.__modify_cam_conf(cam_conf)
            self._cam_id_validator.validate(cam_id)
            self._inner_validation_schema.load(cam_conf)

    def __modify_cam_conf(self, cam_conf: dict):
        """Nasty hack with modification in-place. Is done since we won't the old
        users to get an error with new fields.
        """
        cam_conf['rtsp_port'] = cam_conf.get('rtsp_port', RTSP_DEFAULT_PORT)
        cam_conf['hashtag'] = cam_conf.get('hashtag', '')

        alert = cam_conf['alert']
        alert['video_gif']['rtsp_transport_type'] = alert['video_gif'].get('rtsp_transport_type', 'tcp')

        for detection in DetectionMode.choices():
            alert[detection]['sendpic'] = alert[detection].get('sendpic', True)

    class Meta:
        unknown = INCLUDE
        ordered = True


class Watchdog(Schema):
    enabled = f.Boolean(required=True)
    directory = f.Str(required=True, validate=v.Length(min=0))


class Telegram(Schema):
    token = f.Str(required=True, validate=non_empty_str)
    allowed_user_ids = f.List(f.Int(required=True), required=True,
                              validate=non_empty_str)


class MainConfig(Schema):
    APP_LOG_LEVELS = {'DEBUG', 'WARNING', 'INFO', 'ERROR', 'CRITICAL'}

    telegram = f.Nested(Telegram, required=True)
    watchdog = f.Nested(Watchdog, required=True)
    log_level = f.Str(required=True, validate=v.OneOf(APP_LOG_LEVELS))
    camera_list = f.Nested(CamConfig, required=True)

    class Meta:
        ordered = True
