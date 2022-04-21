import logging
import os
from typing import TYPE_CHECKING

from addict import Dict

from hikcamerabot.services.stream.dvr.tasks.file_lock_check import FileLockCheckTask
from hikcamerabot.utils.utils import shallow_sleep_async

if TYPE_CHECKING:
    from hikcamerabot.services.stream.dvr.upload.engine import DvrUploadEngine


class DvrFileMonitoringTask:
    _TASK_SLEEP = 30

    def __init__(self, engine: 'DvrUploadEngine', conf: Dict) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._engine = engine
        self._conf = conf
        self._storage_path: str = self._conf.livestream.dvr.local_storage_path

    async def run(self) -> None:
        await self._monitor_dvr_files()

    async def _monitor_dvr_files(self) -> None:
        while True:
            self._log.debug('Running %s task', self.__class__.__name__)
            try:
                await self._engine.upload_files(await self._get_unlocked_files())
            except Exception:
                self._log.exception(
                    '%s encountered an exception', self.__class__.__name__
                )
            await shallow_sleep_async(self._TASK_SLEEP)

    async def _get_unlocked_files(self) -> list[str]:
        files = [f for f in os.listdir(self._storage_path) if f.endswith('.mp4')]
        if not files:
            self._log.debug('No DVR files in storage %s', self._storage_path)
            return []

        self._log.debug(
            'Found %d files in %s: %s', len(files), self._storage_path, files
        )
        unlocked_files = await FileLockCheckTask(files).run()
        if not unlocked_files:
            self._log.debug('No unlocked files to process')
        return unlocked_files
