from marshmallow import (
    INCLUDE, Schema, fields as f, validate as v, validates_schema,
)

from hikcamerabot.config.schemas.validators import int_min_1, non_empty_str
from hikcamerabot.constants import (
    CMD_CAM_ID_REGEX,
    Detection as DetectionMode,
    FFMPEG_LOG_LEVELS,
    RTSP_DEFAULT_PORT,
    RtspTransportType,
)


class LivestreamConf(Schema):
    enabled = f.Boolean(required=True)
    livestream_template = f.Str(required=True, validate=non_empty_str)
    encoding_template = f.Str(required=True, validate=non_empty_str)


class TelegramDvrUploadConf(Schema):
    enabled = f.Boolean(required=True)
    group_id = f.Int(required=True, allow_none=True)


class DvrUploadStorageConf(Schema):
    telegram = f.Nested(TelegramDvrUploadConf, required=True)


class DvrUploadConf(Schema):
    delete_after_upload = f.Boolean(required=True)
    storage = f.Nested(DvrUploadStorageConf, required=True)


class DvrLivestreamConf(LivestreamConf):
    local_storage_path = f.Str(required=True, validate=non_empty_str)
    upload = f.Nested(DvrUploadConf, required=True)


class Livestream(Schema):
    srs = f.Nested(LivestreamConf, required=True)
    dvr = f.Nested(DvrLivestreamConf, required=True)
    youtube = f.Nested(LivestreamConf, required=True)
    telegram = f.Nested(LivestreamConf, required=False)
    icecast = f.Nested(LivestreamConf, required=True)


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
    rtsp_transport_type = f.Str(required=True,
                                validate=v.OneOf(RtspTransportType.choices()))


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


class CamConfig(Schema):
    class _CamConfig(Schema):
        hidden = f.Boolean(required=True)
        description = f.Str(required=True, validate=non_empty_str)
        hashtag = f.Str(required=False, allow_none=False, load_default='')
        api = f.Nested(CamAPI, required=True)
        rtsp_port = f.Int(required=True)
        alert = f.Nested(Alert, required=True)
        livestream = f.Nested(Livestream, required=True)
        command_sections_visibility = f.Nested(CmdSectionsVisibility, required=True)

        class Meta:
            ordered = True

    def __init__(self, *args, **kwargs) -> None:
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

    def __modify_cam_conf(self, cam_conf: dict) -> None:
        """Nasty hack with modification in-place. Is done since we won't the old
        users to get an error with new fields.
        """
        cam_conf['rtsp_port'] = cam_conf.get('rtsp_port', RTSP_DEFAULT_PORT)
        cam_conf['hashtag'] = cam_conf.get('hashtag', '')

        alert = cam_conf['alert']
        alert['video_gif']['rtsp_transport_type'] = alert['video_gif'].get(
            'rtsp_transport_type', 'tcp')

        for detection in DetectionMode.choices():
            alert[detection]['sendpic'] = alert[detection].get('sendpic', True)

    class Meta:
        unknown = INCLUDE
        ordered = True


class Telegram(Schema):
    api_id = f.Int(required=True, validate=int_min_1)
    api_hash = f.Str(required=True, validate=non_empty_str)
    lang_code = f.Str(required=True, validate=non_empty_str)
    token = f.Str(required=True, validate=non_empty_str)
    allowed_user_ids = f.List(f.Int(required=True), required=True,
                              validate=non_empty_str)


class MainConfig(Schema):
    _APP_LOG_LEVELS = {'DEBUG', 'WARNING', 'INFO', 'ERROR', 'CRITICAL'}

    telegram = f.Nested(Telegram, required=True)
    log_level = f.Str(required=True, validate=v.OneOf(_APP_LOG_LEVELS))
    camera_list = f.Nested(CamConfig, required=True)

    class Meta:
        ordered = True
