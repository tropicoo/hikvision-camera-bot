"""Config module."""
import json
import logging
import re
import sys
from pathlib import Path

from addict import Dict
from marshmallow import ValidationError

from hikcamerabot.config.schemas import CONFIG_SCHEMA_MAPPING
from hikcamerabot.enums import ConfigFile
from hikcamerabot.exceptions import ConfigError


class ConfigLoader:

    _CONFIGS_DIR = 'configs'

    def __init__(self) -> None:
        self._log = logging.getLogger(self.__class__.__name__)

    def load_configs(self) -> list[Dict]:
        configs, errors = self._load_configs()
        if errors:
            self._process_errors_and_exit(errors)
        return configs

    def _load_configs(self) -> tuple[list[Dict], dict]:
        """Loads telegram and camera configuration from config file."""
        config_data = []
        errors = {}
        dir_path = Path(__file__).parent.parent.parent / self._CONFIGS_DIR
        for conf_file, schema in CONFIG_SCHEMA_MAPPING.items():
            conf_file_path = dir_path / conf_file.value
            self._check_path_existence(conf_file_path)

            self._log.info('Reading config file %s', conf_file_path)
            with open(conf_file_path, 'r') as fd_in:
                try:
                    config = schema().load(json.load(fd_in))
                except ValidationError as err:
                    errors[conf_file.value] = err.messages
                    continue

                if conf_file is ConfigFile.MAIN:
                    config = self._fix_camera_list_key_ordering(config)
                config_data.append(Dict(config))

        return config_data, errors

    def _check_path_existence(self, conf_file_path: Path) -> None:
        if not conf_file_path.is_file():
            err_msg = f'Cannot find {conf_file_path} configuration file'
            self._log.error(err_msg)
            raise ConfigError(err_msg)

    def _fix_camera_list_key_ordering(self, config: dict) -> dict:
        """Fix ordering since something randomly affects marshmallow ordering."""

        def sort_int(cam_id: str) -> list[int]:
            return [int(id_) for id_ in re.findall(r'\d+', cam_id)]

        cam_list_fixed = {}
        for k in sorted(config['camera_list'].keys(), key=sort_int):
            cam_list_fixed[k] = config['camera_list'][k]
        config['camera_list'] = cam_list_fixed
        return config

    def _process_errors_and_exit(self, errors: dict) -> None:
        for config_filename, error_messages in errors.items():
            self._log.error(
                'Config validation error - "%s": %s', config_filename, error_messages
            )
        sys.exit('Fix config files and try again.')


_CONF_MAIN, _CONF_LIVESTREAM_TPL, _CONF_ENCODING_TPL = ConfigLoader().load_configs()


def get_main_config() -> Dict:
    return _CONF_MAIN


def get_livestream_tpl_config() -> Dict:
    return _CONF_LIVESTREAM_TPL


def get_encoding_tpl_config() -> Dict:
    return _CONF_ENCODING_TPL
