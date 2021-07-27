"""Config module."""

import json
import logging
from asyncio import Queue
from pathlib import Path

from addict import Addict

from hikcamerabot.config.schemas import Encoding, Livestream, MainConfig
from hikcamerabot.exceptions import ConfigError

log = logging.getLogger(__name__)

_CONFIG_FILE_MAIN = 'config.json'
_CONFIG_FILE_LIVESTREAM = 'livestream_templates.json'
_CONFIG_FILE_ENCODING = 'encoding_templates.json'
_CONFIG_FILES = {
    _CONFIG_FILE_MAIN: MainConfig,
    _CONFIG_FILE_LIVESTREAM: Livestream,
    _CONFIG_FILE_ENCODING: Encoding,
}


def _fix_camera_list_key_ordering(data: dict) -> dict:
    """Fix ordering since something randomly affects marshmallow ordering."""
    cam_list_fixed = {}
    for k in sorted(data['camera_list'].keys()):
        cam_list_fixed[k] = data['camera_list'][k]
    data['camera_list'] = cam_list_fixed
    return data


def _load_configs() -> list[Addict, ...]:
    """Loads telegram and camera configuration from config file."""
    config_data = []
    dir_path = Path(__file__).parent.parent.parent
    for conf_filename, schema in _CONFIG_FILES.items():
        conf_file_path = dir_path / conf_filename

        if not conf_file_path.is_file():
            err_msg = f'Cannot find {conf_file_path} configuration file'
            log.error(err_msg)
            raise ConfigError(err_msg)

        log.info('Reading config file %s', conf_file_path)
        with open(conf_file_path, 'r') as fd:
            data = schema().load(json.load(fd))
            if conf_filename == _CONFIG_FILE_MAIN:
                data = _fix_camera_list_key_ordering(data)
            config_data.append(Addict(data))
    return config_data


_RESULT_QUEUE = Queue()


def get_result_queue() -> Queue:
    return _RESULT_QUEUE


_CONF_MAIN, _CONF_LIVESTREAM_TPL, _CONF_ENCODING_TPL = _load_configs()


def get_main_config() -> Addict:
    return _CONF_MAIN


def get_livestream_tpl_config() -> Addict:
    return _CONF_LIVESTREAM_TPL


def get_encoding_tpl_config() -> Addict:
    return _CONF_ENCODING_TPL
