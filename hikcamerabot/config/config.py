"""Config module."""

import logging
import sys
from pathlib import Path
from typing import Final, cast

from pydantic import BaseModel, ValidationError

from hikcamerabot.config.schemas import CONFIG_SCHEMA_MAPPING
from hikcamerabot.config.schemas.encoding import EncodingTemplatesSchema
from hikcamerabot.config.schemas.livestream import LivestreamTemplatesSchema
from hikcamerabot.config.schemas.main_config import MainConfigSchema
from hikcamerabot.enums import ConfigFile
from hikcamerabot.exceptions import ConfigError

type ConfigsType = tuple[
    MainConfigSchema, LivestreamTemplatesSchema, EncodingTemplatesSchema
]
type ConfigErrorsType = dict[ConfigFile, str]


class ConfigLoader:
    _CONFIGS_DIR: Final[Path] = Path('configs')

    def __init__(self) -> None:
        self._log = logging.getLogger(self.__class__.__name__)

    def load_configs(self) -> ConfigsType:
        configs, errors = self._load_configs()
        if errors:
            self._process_errors_and_exit_app(errors)
        return configs

    def _load_configs(self) -> tuple[ConfigsType, ConfigErrorsType]:
        """Load telegram and camera configuration from config file."""
        config_data: list[BaseModel] = []
        errors: ConfigErrorsType = {}
        dir_path = Path(__file__).parent.parent.parent / self._CONFIGS_DIR
        for conf_file, schema in CONFIG_SCHEMA_MAPPING.items():
            conf_file_path = dir_path / conf_file
            self._check_path_existence(conf_file_path)

            self._log.info('Reading config file "%s"', conf_file_path)
            with conf_file_path.open() as fd_in:
                try:
                    config = schema.model_validate_json(fd_in.read())
                except ValidationError as err:
                    err: ValidationError
                    errors[conf_file] = str(err)
                    continue

                config_data.append(config)

        return cast(ConfigsType, tuple(config_data)), errors

    def _check_path_existence(self, conf_file_path: Path) -> None:
        if not conf_file_path.is_file():
            err_msg = f'Cannot find {conf_file_path} configuration file'
            self._log.error(err_msg)
            raise ConfigError(err_msg)

    def _process_errors_and_exit_app(self, errors: ConfigErrorsType) -> None:
        for config_filename, error_messages in errors.items():
            self._log.error(
                'Config validation error - "%s": %s', config_filename, error_messages
            )
        sys.exit('Fix config files and try again.')


main_conf, livestream_conf, encoding_conf = ConfigLoader().load_configs()
