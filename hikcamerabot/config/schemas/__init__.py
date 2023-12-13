from marshmallow import Schema

from hikcamerabot.config.schemas.encoding import Encoding
from hikcamerabot.config.schemas.livestream import Livestream
from hikcamerabot.config.schemas.main_config import MainConfig
from hikcamerabot.enums import ConfigFile

CONFIG_SCHEMA_MAPPING: dict[ConfigFile, type[Schema]] = {
    ConfigFile.MAIN: MainConfig,
    ConfigFile.LIVESTREAM: Livestream,
    ConfigFile.ENCODING: Encoding,
}

__all__ = [
    'CONFIG_SCHEMA_MAPPING',
]
