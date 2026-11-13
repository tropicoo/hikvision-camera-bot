import os
import sys

import pytest

os.environ.setdefault('TZ', 'UTC')


def _is_config_available() -> bool:
    """Modules importing `hikcamerabot.config.config` need valid configs."""
    try:
        import hikcamerabot.config.config  # noqa: F401
    except (Exception, SystemExit):
        return False
    return True


requires_config = pytest.mark.skipif(
    not _is_config_available(),
    reason='configs/*.json are required (copy them from templates)',
)
requires_linux = pytest.mark.skipif(
    not sys.platform.startswith('linux'), reason='Linux only'
)
