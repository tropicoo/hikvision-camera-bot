import asyncio
import logging
import os
from typing import TYPE_CHECKING

from hikcamerabot.utils.shared import shallow_sleep_async

if TYPE_CHECKING:
    from hikcamerabot.services.stream.dvr.file_wrapper import DvrFile


class DvrFileDeleteTask:
    _QUEUE_SLEEP = 30

    def __init__(self, queue: asyncio.Queue['DvrFile']) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._queue = queue

    async def run(self) -> None:
        """Main entry point."""
        await self._process_queue()

    async def _process_queue(self) -> None:
        while True:
            self._log.debug('Running %s task', self.__class__.__name__)
            locked_files = []
            while not self._queue.empty():
                file_ = await self._queue.get()
                if file_.is_locked:
                    self._log.debug(
                        'File %s cannot be deleted right now: %d locks left',
                        file_,
                        file_.lock_count,
                    )
                    locked_files.append(file_)
                else:
                    self._perform_file_cleanup(file_)
            for file_ in locked_files:
                await self._queue.put(file_)
            await shallow_sleep_async(self._QUEUE_SLEEP)

    def _perform_file_cleanup(self, file_: 'DvrFile') -> None:
        self._delete_thumbnail(file_)
        self._delete_file(file_)

    def _delete_file(self, file_: 'DvrFile') -> None:
        self._log.debug('Deleting DVR file %s', file_.full_path)
        try:
            os.remove(file_.full_path)
        except Exception:
            self._log.exception('Failed to delete DVR file %s', file_.full_path)

    def _delete_thumbnail(self, file_: 'DvrFile') -> None:
        thumb = file_.thumbnail
        if not thumb:
            self._log.debug('No thumbnail to delete for %s', file_.full_path)
            return

        self._log.debug('Deleting DVR file thumbnail %s', thumb)
        try:
            os.remove(thumb)
        except Exception:
            self._log.exception('Failed to delete thumbnail %s', thumb)
