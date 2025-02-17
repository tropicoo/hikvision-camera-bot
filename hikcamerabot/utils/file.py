import os
import shutil
from pathlib import Path
from typing import Final

from hikcamerabot.utils.task import wrap

_UNIT_SIZE_NAMES: Final[tuple[str, ...]] = (
    '',
    'Ki',
    'Mi',
    'Gi',
    'Ti',
    'Pi',
    'Ei',
    'Zi',
)
_BASE: Final[float] = 1024.0


def format_bytes(num: int, suffix: str = 'B') -> str:
    """Format bytes to human-readable size."""
    for unit in _UNIT_SIZE_NAMES:
        if abs(num) < _BASE:
            return f'{num:3.1f}{unit}{suffix}'
        num /= _BASE
    return f'{num:.1f}Yi{suffix}'


def file_size(filepath: Path) -> int:
    """Return file size in bytes."""
    return filepath.stat().st_size


awaitable_shutil_move = wrap(shutil.move)
awaitable_shutil_copyfileobj = wrap(shutil.copyfileobj)
awaitable_os_killpg = wrap(os.killpg)
