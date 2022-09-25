import logging
from dataclasses import dataclass

from httpx import AsyncClient

from hikcamerabot.version import __version__


@dataclass
class BotVersion:
    """Bot version DTO class."""

    current: str
    latest: str

    def has_new_version(self) -> bool:
        _current = [int(x) for x in self.current.split('.')]
        _latest = [int(x) for x in self.latest.split('.')]
        return _latest > _current


class HikCameraBotVersionChecker:
    LATEST_TAG_URL = 'https://github.com/tropicoo/hikvision-camera-bot/releases/latest'

    def __init__(self) -> None:
        self._log = logging.getLogger(self.__class__.__name__)

    def get_current_version(self) -> str:
        return __version__

    async def get_latest_version(self) -> str:
        """Get latest version number from latest GitHub tag URL."""
        self._log.info('Get latest hikvision-camera-bot version number')
        client: AsyncClient
        async with AsyncClient() as client:
            response = await client.head(self.LATEST_TAG_URL)
            version: str = response.headers.get('location').split('/')[-1]
            self._log.info('Latest hikvision-camera-bot version number: %s', version)
            return version

    async def get_version(self) -> BotVersion:
        return BotVersion(
            current=self.get_current_version(), latest=await self.get_latest_version()
        )
