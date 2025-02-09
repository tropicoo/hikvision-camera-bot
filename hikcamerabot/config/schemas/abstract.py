from abc import ABC

from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel, ABC):
    model_config = ConfigDict(
        strict=True, frozen=True, str_strip_whitespace=True, str_min_length=1
    )
