from marshmallow import (
    INCLUDE, Schema, fields as f, validate as v,
    validates_schema,
)

from hikcamerabot.constants import FFMPEG_LOG_LEVELS, RTSP_TRANSPORT_TYPES


class BaseTemplate(Schema):
    _inner_validation_schema_cls = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._inner_validation_schema = self._inner_validation_schema_cls()
        self._template_validator = f.String(
            required=True,
            validate=v.Length(min=1))

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
        vcodec = f.String(required=True, validate=v.Length(min=1))
        acodec = f.String(required=True, validate=v.Length(min=1))
        format = f.String(required=True, validate=v.Length(min=1))
        rtsp_transport_type = f.String(required=True,
                                       validate=v.OneOf(RTSP_TRANSPORT_TYPES))

    _inner_validation_schema_cls = _Direct


class X264(BaseTemplate):
    class _X264(Schema):
        class _Scale(Schema):
            enabled = f.Boolean(required=True)
            width = f.Integer(required=True)
            height = f.Integer(required=True)
            format = f.String(required=True, validate=v.Length(min=1))

        null_audio = f.Boolean(required=True)
        loglevel = f.String(required=True, validate=v.OneOf(FFMPEG_LOG_LEVELS))
        vcodec = f.String(required=True, validate=v.Length(min=1))
        acodec = f.String(required=True, validate=v.Length(min=1))
        format = f.String(required=True, validate=v.Length(min=1))
        rtsp_transport_type = f.String(required=True, validate=v.Length(min=1))
        pix_fmt = f.String(required=True, validate=v.Length(min=1))
        pass_mode = f.Integer(required=True, validate=v.Range(min=1))
        framerate = f.Integer(required=True, validate=v.Range(min=1))
        preset = f.String(required=True, validate=v.Length(min=1))
        average_bitrate = f.String(required=True, validate=v.Length(min=1))
        maxrate = f.String(required=True, validate=v.Length(min=1))
        bufsize = f.String(required=True, validate=v.Length(min=1))
        tune = f.String(required=True, validate=v.Length(min=1))
        scale = f.Nested(_Scale, required=True)

    _inner_validation_schema_cls = _X264


class Vp9(BaseTemplate):
    class _Vp9(Schema):
        class _Scale(Schema):
            enabled = f.Boolean(required=True)
            width = f.Integer(required=True, validate=v.Range(min=1))
            height = f.Integer(required=True)
            format = f.String(required=True, validate=v.Length(min=1))

        null_audio = f.Boolean(required=True)
        loglevel = f.String(required=True, validate=v.OneOf(FFMPEG_LOG_LEVELS))
        vcodec = f.String(required=True, validate=v.Length(min=1))
        acodec = f.String(required=True, validate=v.Length(min=1))
        format = f.String(required=True, validate=v.Length(min=1))
        rtsp_transport_type = f.String(required=True, validate=v.Length(min=1))
        pix_fmt = f.String(required=True, validate=v.Length(min=1))
        pass_mode = f.Integer(required=True, validate=v.Range(min=1))
        framerate = f.Integer(required=True, validate=v.Range(min=1))
        average_bitrate = f.String(required=True, validate=v.Length(min=1))
        maxrate = f.String(required=True, validate=v.Length(min=1))
        bufsize = f.String(required=True, validate=v.Length(min=1))
        deadline = f.String(required=True, validate=v.Length(min=1))
        speed = f.Integer(required=True, validate=v.Range(min=1))
        scale = f.Nested(_Scale, required=True)

    _inner_validation_schema_cls = _Vp9


class Encoding(Schema):
    direct = f.Nested(Direct, required=True)
    x264 = f.Nested(X264, required=True)
    vp9 = f.Nested(Vp9, required=True)
