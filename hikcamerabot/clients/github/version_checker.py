import logging
import re
from dataclasses import dataclass
from typing import Final

from httpx import AsyncClient

from hikcamerabot.version import __version__

_VERSION_REGEX: Final[re.Pattern[str]] = re.compile(
    r"__version__\s*=\s*['\"](\d+(?:\.\d+)*)['\"]"
)
_TIMEOUT: Final[float] = 10.0


def _parse_version(version: str) -> tuple[int, ...]:
    return tuple(int(x) for x in version.split('.'))


@dataclass
class BotVersion:
    """Bot version DTO class."""

    current: str
    latest: str

    def has_new_version(self) -> bool:
        return _parse_version(self.latest) > _parse_version(self.current)


class HikCameraBotVersionChecker:
    """Compare running version with the one in this fork's `master` branch.

    The bot is updated with `update.sh` (git pull), so the version file of the
    default branch is what the user gets after an update.
    """

    LATEST_VERSION_URL: str = (
        'https://raw.githubusercontent.com/SA1D77/hikvision-camera-bot/'
        'master/hikcamerabot/version.py'
    )

    def __init__(self) -> None:
        self._log = logging.getLogger(self.__class__.__name__)

    def get_current_version(self) -> str:
        return __version__

    async def get_latest_version(self) -> str:
        """Get latest version number. Raise an exception if it's unavailable."""
        self._log.info('Get latest hikvision-camera-bot version number')
        client: AsyncClient
        async with AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(self.LATEST_VERSION_URL)
        response.raise_for_status()
        match = _VERSION_REGEX.search(response.text)
        if match is None:
            raise ValueError(f'No version found at {self.LATEST_VERSION_URL}')
        version = match.group(1)
        self._log.info('Latest hikvision-camera-bot version number: %s', version)
        return version

    async def get_version(self) -> BotVersion:
        return BotVersion(
            current=self.get_current_version(), latest=await self.get_latest_version()
        )
