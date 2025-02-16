import asyncio
import logging
import signal

from hikcamerabot.constants import FFMPEG_BIN
from hikcamerabot.utils.process import get_stdout_stderr, kill_proc


class FileLockCheckTask:
    _PROCESS_TIMEOUT: int = 5
    _LOCKED_FILES_CMD: str = rf"lsof|awk '/{FFMPEG_BIN}.*\.mp4/'"

    def __init__(self, files: list[str]) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._files = files

    async def run(self) -> list[str]:
        self._log.debug(
            'Running %s task for files %s', self.__class__.__name__, self._files
        )
        return await self._get_unlocked_files()

    async def _get_unlocked_files(self) -> list[str]:
        """Return list with absolute file paths that are not locked by ffmpeg process during write operation."""
        proc = await asyncio.create_subprocess_shell(
            self._LOCKED_FILES_CMD,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=self._PROCESS_TIMEOUT)
        except TimeoutError:
            self._log.error(
                'Failed to execute %s: process ran longer than '
                'expected (%ds) and was killed',
                self._LOCKED_FILES_CMD,
                self._PROCESS_TIMEOUT,
            )
            await kill_proc(process=proc, signal_=signal.SIGINT, reraise=False)
            return []

        stdout, stderr = await get_stdout_stderr(proc)
        self._log.debug(
            'Process "%s" returncode: %d, stdout: %s, stderr: %s',
            self._LOCKED_FILES_CMD,
            proc.returncode,
            stdout,
            stderr,
        )
        unlocked_files = [f for f in self._files if f not in stdout]
        unlocked_files.sort()
        return unlocked_files
