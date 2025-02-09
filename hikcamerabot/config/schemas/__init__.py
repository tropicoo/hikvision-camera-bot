from typing import Final

from pydantic import BaseModel

from hikcamerabot.config.schemas.encoding import EncodingTemplatesSchema
from hikcamerabot.config.schemas.livestream import LivestreamTemplatesSchema
from hikcamerabot.config.schemas.main_config import MainConfigSchema
from hikcamerabot.enums import ConfigFile

CONFIG_SCHEMA_MAPPING: Final[dict[ConfigFile, type[BaseModel]]] = {
    ConfigFile.MAIN: MainConfigSchema,
    ConfigFile.LIVESTREAM: LivestreamTemplatesSchema,
    ConfigFile.ENCODING: EncodingTemplatesSchema,
}

__all__ = [
    'CONFIG_SCHEMA_MAPPING',
]
