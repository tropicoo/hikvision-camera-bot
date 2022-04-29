import asyncio
import logging
import os
import signal

from hikcamerabot.utils.task import wrap


class FileLockCheckTask:
    _PROCESS_TIMEOUT = 5
    _LOCKED_FILES_CMD = r"lsof|awk '/ffmpeg.*\.mp4/'"

    def __init__(self, files: list[str]) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._files = files
        self._killpg = wrap(os.killpg)

    async def run(self) -> list[str]:
        self._log.debug(
            'Running %s task for files %s', self.__class__.__name__, self._files
        )
        return await self._get_unlocked_files()

    async def _get_unlocked_files(self) -> list[str]:
        proc = await asyncio.create_subprocess_shell(
            self._LOCKED_FILES_CMD,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=self._PROCESS_TIMEOUT)
        except asyncio.TimeoutError:
            self._log.error(
                'Failed to execute %s: process ran longer than '
                'expected and was killed',
                self._LOCKED_FILES_CMD,
            )
            await self._killpg(os.getpgid(proc.pid), signal.SIGINT)
            return []

        stdout, stderr = await self._get_stdout_stderr(proc)
        self._log.debug(
            'Process %s returncode: %d, stdout: %s, stderr: %s',
            self._LOCKED_FILES_CMD,
            proc.returncode,
            stdout,
            stderr,
        )
        unlocked_files = [f for f in self._files if f not in stdout]
        unlocked_files.sort()
        return unlocked_files

    @staticmethod
    async def _get_stdout_stderr(proc: asyncio.subprocess.Process) -> tuple[str, str]:
        stdout, stderr = await proc.stdout.read(), await proc.stderr.read()
        return stdout.decode().strip(), stderr.decode().strip()
