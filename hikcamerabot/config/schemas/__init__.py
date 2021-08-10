from hikcamerabot.config.schemas.encoding import Encoding
from hikcamerabot.config.schemas.livestream import Livestream
from hikcamerabot.config.schemas.main_config import MainConfig
from hikcamerabot.constants import ConfigFile

config_schema_mapping = {
    ConfigFile.MAIN.value: MainConfig,
    ConfigFile.LIVESTREAM.value: Livestream,
    ConfigFile.ENCODING.value: Encoding,
}

__all__ = [
    'config_schema_mapping',
]
