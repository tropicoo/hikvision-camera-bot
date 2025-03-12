import logging
from zoneinfo import available_timezones

from hikcamerabot.constants import FFMPEG_LOG_LEVELS


def int_min_0(value: int) -> int:
    if value < 0:
        raise ValueError('Must be >= 0')
    return value


def int_min_1(value: int) -> int:
    if value < 1:
        raise ValueError('Must be >= 1')
    return value


def int_min_minus_1(value: int) -> int:
    if value < -1:
        raise ValueError('Must be >= -1')
    return value


def validate_ffmpeg_loglevel(value: str) -> str:
    if value not in FFMPEG_LOG_LEVELS:
        raise ValueError(f'Invalid ffmpeg log level: {value}')
    return value


def validate_python_log_level(value: str) -> str:
    allowed_values = logging.getLevelNamesMapping().keys()
    if value not in allowed_values:
        raise ValueError(f'Invalid log level: {value}. Allowed: {list(allowed_values)}')
    return value


def validate_timezone(value: str) -> str:
    if value not in available_timezones():
        raise ValueError(f'Invalid timezone: {value}')
    return value
