import logging
from dataclasses import dataclass

import httpx

from hikcamerabot.version import __version__ as current_version


@dataclass
class VersionContext:
    current: str
    latest: str
    has_new_version: bool


class HikCameraBotVersionChecker:
    LATEST_TAG_URL = 'https://github.com/tropicoo/hikvision-camera-bot/releases/latest'

    def __init__(self) -> None:
        self._log = logging.getLogger(self.__class__.__name__)

    def get_current_version(self) -> str:
        return current_version

    async def get_latest_version(self) -> str:
        self._log.info('Get latest hikvision-camera-bot version number')
        async with httpx.AsyncClient() as client:
            response = await client.get(self.LATEST_TAG_URL, follow_redirects=True)
            version = response.url.path.split('/')[-1]
            self._log.info(
                'Latest hikvision-camera-bot version number: %s', version
            )
            return version

    async def get_context(self) -> VersionContext:
        current = self.get_current_version()
        latest = await self.get_latest_version()
        _current = [int(x) for x in current.split('.')]
        _latest = [int(x) for x in latest.split('.')]
        return VersionContext(
            current=current,
            latest=latest,
            has_new_version=_latest > _current,
        )
