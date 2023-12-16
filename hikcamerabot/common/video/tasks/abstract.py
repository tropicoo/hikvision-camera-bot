import abc
import asyncio
import logging
import signal

from hikcamerabot.utils.process import kill_proc


class AbstractFfBinaryTask(metaclass=abc.ABCMeta):
    _CMD: str | None = None
    _CMD_TIMEOUT = 60

    def __init__(self, file_path: str) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._file_path = file_path

    async def _run_proc(self, cmd: str) -> asyncio.subprocess.Process | None:
        proc = await asyncio.create_subprocess_shell(
            cmd=cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=self._CMD_TIMEOUT)
            return proc
        except asyncio.TimeoutError:
            self._log.error(
                'Failed to execute %s: process ran longer than '
                'expected and was killed',
                cmd,
            )
            await kill_proc(process=proc, signal_=signal.SIGINT, reraise=False)
            return None

    @abc.abstractmethod
    async def run(self) -> None:
        """Main entry point."""
        pass
