import asyncio
import logging
import os
import signal
from pathlib import Path
from typing import Final

from hikcamerabot.constants import FFMPEG_BIN
from hikcamerabot.utils.process import get_stdout_stderr, kill_proc

_PROC_PATH: Final[Path] = Path('/proc')


def get_files_open_by_process(
    process_name: str, proc_path: Path = _PROC_PATH
) -> set[str] | None:
    """Return paths of files opened by processes named `process_name`.

    Reads `/proc` directly, which is much lighter than running `lsof` for the
    whole system (noticeable on Raspberry Pi). Return `None` if `/proc` is not
    available so the caller can fall back to `lsof`.
    """
    if not proc_path.is_dir():
        return None

    open_files: set[str] = set()
    for pid_dir in proc_path.iterdir():
        if not pid_dir.name.isdigit():
            continue
        try:
            if (pid_dir / 'comm').read_text().strip() != process_name:
                continue
            for fd in (pid_dir / 'fd').iterdir():
                try:
                    open_files.add(str(fd.readlink()))
                except OSError:
                    continue
        except OSError:
            # Process exited or access denied.
            continue
    return open_files


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
        open_files = await asyncio.to_thread(get_files_open_by_process, FFMPEG_BIN)
        if open_files is not None:
            unlocked_files = [
                f
                for f in self._files
                if f not in open_files and os.path.realpath(f) not in open_files
            ]
        else:
            locked_output = await self._get_lsof_output()
            if locked_output is None:
                return []
            unlocked_files = [f for f in self._files if f not in locked_output]
        unlocked_files.sort()
        return unlocked_files

    async def _get_lsof_output(self) -> str | None:
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
            return None

        stdout, stderr = await get_stdout_stderr(proc)
        self._log.debug(
            'Process "%s" returncode: %d, stdout: %s, stderr: %s',
            self._LOCKED_FILES_CMD,
            proc.returncode,
            stdout,
            stderr,
        )
        return stdout
