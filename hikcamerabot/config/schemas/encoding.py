from marshmallow import (
    fields as f,
    INCLUDE,
    Schema,
    validate as v,
    validates_schema,
)

from hikcamerabot.config.schemas.validators import (
    int_min_1, int_min_minus_1,
    non_empty_str,
)
from hikcamerabot.constants import FFMPEG_LOG_LEVELS, RtspTransportType


class BaseTemplate(Schema):
    _inner_validation_schema_cls = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._inner_validation_schema = self._inner_validation_schema_cls()
        self._template_validator = f.String(
            required=True,
            validate=non_empty_str)

    @validates_schema
    def validate_all(self, data: dict, **kwargs) -> None:
        for tpl_name, tpl_conf in data.items():
            self._template_validator.validate(tpl_name)
            self._inner_validation_schema.load(tpl_conf)  # noqa

    class Meta:
        unknown = INCLUDE


class Direct(BaseTemplate):
    class _Direct(Schema):
        null_audio = f.Boolean(required=True)
        loglevel = f.String(required=True, validate=v.OneOf(FFMPEG_LOG_LEVELS))
        vcodec = f.String(required=True, validate=non_empty_str)
        acodec = f.String(required=True, validate=non_empty_str)
        asample_rate = f.Integer(required=True, validate=int_min_minus_1)
        format = f.String(required=True, validate=non_empty_str)
        rtsp_transport_type = f.String(required=True, validate=v.OneOf(RtspTransportType.choices()))

    _inner_validation_schema_cls = _Direct


class X264(BaseTemplate):
    class _X264(Schema):
        class _Scale(Schema):
            enabled = f.Boolean(required=True)
            width = f.Integer(required=True)
            height = f.Integer(required=True)
            format = f.String(required=True, validate=non_empty_str)

        null_audio = f.Boolean(required=True)
        loglevel = f.String(required=True, validate=v.OneOf(FFMPEG_LOG_LEVELS))
        vcodec = f.String(required=True, validate=non_empty_str)
        acodec = f.String(required=True, validate=non_empty_str)
        asample_rate = f.Integer(required=True, validate=int_min_minus_1)
        format = f.String(required=True, validate=non_empty_str)
        rtsp_transport_type = f.String(required=True, validate=non_empty_str)
        pix_fmt = f.String(required=True, validate=non_empty_str)
        pass_mode = f.Integer(required=True, validate=int_min_1)
        framerate = f.Integer(required=True, validate=int_min_1)
        preset = f.String(required=True, validate=non_empty_str)
        average_bitrate = f.String(required=True, validate=non_empty_str)
        maxrate = f.String(required=True, validate=non_empty_str)
        bufsize = f.String(required=True, validate=non_empty_str)
        tune = f.String(required=True, validate=non_empty_str)
        scale = f.Nested(_Scale, required=True)

    _inner_validation_schema_cls = _X264


class Vp9(BaseTemplate):
    class _Vp9(Schema):
        class _Scale(Schema):
            enabled = f.Boolean(required=True)
            width = f.Integer(required=True, validate=int_min_1)
            height = f.Integer(required=True)
            format = f.String(required=True, validate=non_empty_str)

        null_audio = f.Boolean(required=True)
        loglevel = f.String(required=True, validate=v.OneOf(FFMPEG_LOG_LEVELS))
        vcodec = f.String(required=True, validate=non_empty_str)
        acodec = f.String(required=True, validate=non_empty_str)
        asample_rate = f.Integer(required=True, validate=int_min_minus_1)
        format = f.String(required=True, validate=non_empty_str)
        rtsp_transport_type = f.String(required=True, validate=non_empty_str)
        pix_fmt = f.String(required=True, validate=non_empty_str)
        pass_mode = f.Integer(required=True, validate=int_min_1)
        framerate = f.Integer(required=True, validate=int_min_1)
        average_bitrate = f.String(required=True, validate=non_empty_str)
        maxrate = f.String(required=True, validate=non_empty_str)
        bufsize = f.String(required=True, validate=non_empty_str)
        deadline = f.String(required=True, validate=non_empty_str)
        speed = f.Integer(required=True, validate=int_min_1)
        scale = f.Nested(_Scale, required=True)

    _inner_validation_schema_cls = _Vp9


class Encoding(Schema):
    direct = f.Nested(Direct, required=True)
    x264 = f.Nested(X264, required=True)
    vp9 = f.Nested(Vp9, required=True)
