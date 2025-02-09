import logging
import os
from typing import TYPE_CHECKING

from hikcamerabot.config.schemas.main_config import CameraConfigSchema
from hikcamerabot.services.stream.dvr.tasks.file_lock_check import FileLockCheckTask
from hikcamerabot.utils.shared import shallow_sleep_async

if TYPE_CHECKING:
    from hikcamerabot.services.stream.dvr.upload.engine import DvrUploadEngine


class DvrFileMonitoringTask:
    _TASK_SLEEP: int = 30

    def __init__(
        self, engine: 'DvrUploadEngine', conf: CameraConfigSchema, cam_id: str
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._engine = engine
        self._conf = conf
        self._storage_path = self._conf.livestream.dvr.local_storage_path
        self._cam_id = cam_id

    async def run(self) -> None:
        await self._monitor_dvr_files()

    async def _monitor_dvr_files(self) -> None:
        while True:
            self._log.debug(
                '[%s] Running %s task', self._cam_id, self.__class__.__name__
            )
            try:
                await self._engine.upload_files(await self._get_unlocked_files())
            except Exception:
                self._log.exception(
                    '[%s] %s encountered an exception',
                    self._cam_id,
                    self.__class__.__name__,
                )
            await shallow_sleep_async(self._TASK_SLEEP)

    async def _get_unlocked_files(self) -> list[str]:
        files = [
            f
            for f in os.listdir(self._storage_path)
            if f.startswith(f'{self._cam_id}_') and f.endswith('.mp4')
        ]
        if not files:
            self._log.debug(
                '[%s] No DVR files in storage %s', self._cam_id, self._storage_path
            )
            return []

        self._log.debug(
            '[%s] Found %d files in %s: %s',
            self._cam_id,
            len(files),
            self._storage_path,
            files,
        )
        unlocked_files = await FileLockCheckTask(files).run()
        if not unlocked_files:
            self._log.debug('[%s] No unlocked files to process', self._cam_id)
        return unlocked_files
