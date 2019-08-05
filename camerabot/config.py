"""Config module."""

import json
import logging
from pathlib import Path

from camerabot.exceptions import ConfigError

_CONFIG_FILE_MAIN = 'config.json'
_CONFIG_FILE_LIVESTREAM = 'livestream_templates.json'
_CONFIG_FILE_ENCODING = 'encoding_templates.json'
_CONFIG_FILES = (_CONFIG_FILE_MAIN,
                 _CONFIG_FILE_LIVESTREAM,
                 _CONFIG_FILE_ENCODING)

_LOG = logging.getLogger(__name__)


class Config:
    """Dot notation for JSON config file."""

    def __init__(self, conf_data):
        self.__conf_data = conf_data

    def __iter__(self):
        return self.__conf_data

    def __repr__(self):
        return repr(self.__conf_data)

    def __getitem__(self, item):
        return self.__conf_data[item]

    def items(self):
        return self.__conf_data.items()

    def pop(self, key):
        return self.__conf_data.pop(key)

    def get(self, key, default=None):
        return self.__conf_data.get(key, default)

    @classmethod
    def from_dict(cls, conf_data):
        """Make dot-mapped object."""
        conf_dict = cls._conf_raise_on_duplicates(conf_data)
        obj = cls(conf_dict)
        obj.__dict__.update(conf_data)
        return obj

    @classmethod
    def _conf_raise_on_duplicates(cls, conf_data):
        """Raise ConfigError on duplicate keys."""
        conf_dict = {}
        for key, value in conf_data:
            if key in conf_dict:
                err_msg = 'Malformed configuration file, ' \
                          'duplicate key: {0}'.format(key)
                raise ConfigError(err_msg)
            else:
                conf_dict[key] = value
        return conf_dict


def _load_configs():
    """Loads telegram and camera configuration from config file
    and returns json object.
    """
    config_data = []
    path = Path(__file__).parent.parent
    for conf_file in _CONFIG_FILES:
        conf_file = path / conf_file
        if not conf_file.is_file():
            err_msg = 'Can\'t find {0} configuration file'.format(conf_file)
            _LOG.error(err_msg)
            raise ConfigError(err_msg)

        _LOG.info('Reading config file %s', conf_file)
        with open(conf_file, 'r') as fd:
            config = fd.read()
        try:
            config = json.loads(config, object_pairs_hook=Config.from_dict)
        except json.decoder.JSONDecodeError:
            err_msg = 'Malformed JSON in {0} ' \
                      'configuration file'.format(conf_file)
            raise ConfigError(err_msg)
        config_data.append(config)

    return config_data


_CONF_MAIN, _CONF_LIVESTREAM_TPL, _CONF_ENCODING_TPL = _load_configs()


def get_main_config():
    return _CONF_MAIN


def get_livestream_tpl_config():
    return _CONF_LIVESTREAM_TPL


def get_encoding_tpl_config():
    return _CONF_ENCODING_TPL
