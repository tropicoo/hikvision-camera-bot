import os

_UNIT_SIZE_NAMES = ('', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi')
_BASE = 1024.0


def format_bytes(num: int, suffix: str = 'B') -> str:
    """Format bytes to human-readable size."""
    for unit in _UNIT_SIZE_NAMES:
        if abs(num) < _BASE:
            return f'{num:3.1f}{unit}{suffix}'
        num /= _BASE
    return f'{num:.1f}Yi{suffix}'


def file_size(filepath: str) -> int:
    """Return file size in bytes."""
    return os.path.getsize(filepath)
