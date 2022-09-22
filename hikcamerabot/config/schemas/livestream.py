from typing import Optional, Type

from marshmallow import INCLUDE, Schema, fields as f, validates_schema

from hikcamerabot.config.schemas.validators import (
    int_min_0,
    int_min_1,
    int_min_minus_1,
    non_empty_str,
)


class BaseTemplate(Schema):
    _inner_validation_schema_cls: Optional[Type[Schema]] = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._inner_validation_schema = self._inner_validation_schema_cls()
        self._template_validator = f.String(required=True, validate=non_empty_str)

    @validates_schema
    def validate_all(self, data: dict, **kwargs) -> None:
        for tpl_name, tpl_conf in data.items():
            self._template_validator.validate(tpl_name)
            self._inner_validation_schema.load(tpl_conf)  # noqa

    class Meta:
        unknown = INCLUDE


class Youtube(BaseTemplate):
    class _Youtube(Schema):
        channel = f.Integer(required=True, validate=int_min_1)
        restart_period = f.Integer(required=True, validate=int_min_1)
        restart_pause = f.Integer(required=True, validate=int_min_0)
        url = f.String(required=True, validate=non_empty_str)
        key = f.String(required=True, validate=non_empty_str)

    _inner_validation_schema_cls = _Youtube


class Telegram(BaseTemplate):
    class _Telegram(Schema):
        channel = f.Integer(required=True, validate=int_min_1)
        restart_period = f.Integer(required=True, validate=int_min_1)
        restart_pause = f.Integer(required=True, validate=int_min_0)
        url = f.String(required=True, validate=non_empty_str)
        key = f.String(required=True, validate=non_empty_str)

    _inner_validation_schema_cls = _Telegram


class Srs(BaseTemplate):
    class _Srs(Schema):
        channel = f.Integer(required=True, validate=int_min_1)
        sub_channel = f.Integer(required=True, validate=int_min_1)
        restart_period = f.Integer(required=True, validate=int_min_minus_1)
        restart_pause = f.Integer(required=True, validate=int_min_0)
        url = f.String(required=True, validate=non_empty_str)

    _inner_validation_schema_cls = _Srs


class Dvr(BaseTemplate):
    class _Dvr(Schema):
        channel = f.Integer(required=True, validate=int_min_1)
        sub_channel = f.Integer(required=True, validate=int_min_1)
        restart_period = f.Integer(required=True, validate=int_min_minus_1)
        restart_pause = f.Integer(required=True, validate=int_min_0)
        segment_time = f.Integer(required=True, validate=int_min_1)

    _inner_validation_schema_cls = _Dvr


class Icecast(BaseTemplate):
    class _Icecast(Schema):
        class _IceStream(Schema):
            ice_genre = f.String(required=True, validate=non_empty_str)
            ice_name = f.String(required=True, validate=non_empty_str)
            ice_description = f.String(required=True, validate=non_empty_str)
            ice_public = f.Integer(required=True)
            url = f.String(required=True, validate=non_empty_str)
            password = f.String(required=True, validate=non_empty_str)
            content_type = f.String(required=True, validate=non_empty_str)

        channel = f.Integer(required=True, validate=int_min_1)
        restart_period = f.Integer(required=True, validate=int_min_1)
        restart_pause = f.Integer(required=True, validate=int_min_0)
        ice_stream = f.Nested(_IceStream(), required=True)

    _inner_validation_schema_cls = _Icecast


class Livestream(Schema):
    youtube = f.Nested(Youtube(), required=True)
    telegram = f.Nested(Telegram(), required=True)
    icecast = f.Nested(Icecast(), required=True)
    srs = f.Nested(Srs(), required=True)
    dvr = f.Nested(Dvr(), required=True)
