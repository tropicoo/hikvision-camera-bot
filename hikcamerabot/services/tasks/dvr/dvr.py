import asyncio
import logging
import os
import signal
from typing import TYPE_CHECKING

from addict import Dict

from hikcamerabot.config.config import get_livestream_tpl_config
from hikcamerabot.utils.task import wrap
from hikcamerabot.utils.utils import shallow_sleep_async

if TYPE_CHECKING:
    from hikcamerabot.services.stream.dvr.file_wrapper import DvrFile
    from hikcamerabot.services.stream.dvr.upload_engine import DvrUploadEngine


class DvrFileMonitoringTask:
    _TASK_SLEEP = 30

    def __init__(self, engine: 'DvrUploadEngine', conf: Dict) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._engine = engine
        self._conf = conf

        tpl_name_ls: str = self._conf.livestream.dvr.livestream_template
        self._storage_path: str = self._conf.livestream.dvr.local_storage_path

    async def run(self) -> None:
        await self._monitor_dvr_files()

    async def _monitor_dvr_files(self) -> None:
        while True:
            self._log.debug('Running %s task', self.__class__.__name__)
            try:
                await self._engine.upload_files(await self._get_unlocked_files())
            except Exception:
                self._log.exception('%s encountered an exception',
                                    self.__class__.__name__)
            await shallow_sleep_async(self._TASK_SLEEP)

    async def _get_unlocked_files(self) -> list[str]:
        files = [f for f in os.listdir(self._storage_path) if f.endswith('.mp4')]
        if not files:
            self._log.debug('No DVR files in storage %s', self._storage_path)
            return []

        self._log.debug('Found %d files in %s: %s', len(files),
                        self._storage_path, files)
        unlocked_files = await FileLockCheckTask(files).run()
        if not unlocked_files:
            self._log.debug('No unlocked files to process')
        return unlocked_files


class FileLockCheckTask:
    _PROCESS_TIMEOUT = 5
    _LOCKED_FILES_CMD = r"lsof|awk '/ffmpeg.*\.mp4/'"

    def __init__(self, files: list[str]) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._files = files
        self._killpg = wrap(os.killpg)

    async def run(self) -> list[str]:
        self._log.debug('Running %s task for files %s',
                        self.__class__.__name__, self._files)
        return await self._get_unlocked_files()

    async def _get_unlocked_files(self) -> list[str]:
        proc = await asyncio.create_subprocess_shell(
            self._LOCKED_FILES_CMD,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=self._PROCESS_TIMEOUT)
        except asyncio.TimeoutError:
            self._log.error('Failed to execute %s: process ran longer than '
                            'expected and was killed', self._LOCKED_FILES_CMD)
            await self._killpg(os.getpgid(proc.pid), signal.SIGINT)
            return []

        stdout, stderr = await self._get_stdout_stderr(proc)
        self._log.debug('Process %s returncode: %d, stdout: %s, stderr: %s',
                        self._LOCKED_FILES_CMD, proc.returncode, stdout, stderr)
        unlocked_files = [f for f in self._files if f not in stdout]
        unlocked_files.sort()
        return unlocked_files

    @staticmethod
    async def _get_stdout_stderr(proc: asyncio.subprocess.Process) -> tuple[
        str, str]:
        stdout, stderr = await proc.stdout.read(), await proc.stderr.read()
        return stdout.decode().strip(), stderr.decode().strip()


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
                    self._log.debug('File %s cannot be deleted right now: '
                                    '%d locks left', file_, file_.lock_count)
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
