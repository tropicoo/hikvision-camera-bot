import asyncio
import logging

from tenacity import retry, retry_if_exception_type, wait_fixed

from hikcamerabot.enums import ServiceType
from hikcamerabot.exceptions import HikvisionCamError
from hikcamerabot.services.abstract import AbstractServiceTask
from hikcamerabot.utils.utils import shallow_sleep_async


class FfmpegStdoutReaderTask:
    """Log async ffmpeg stdout."""

    def __init__(self, proc: asyncio.subprocess.Process, cmd: str) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._cmd = cmd
        self._proc = proc

    async def run(self) -> None:
        self._log.info('Starting %s', self.__class__.__name__)
        while self._proc.returncode is None:
            self._log.debug('Reading stdout from "%s"', self._cmd)
            self._log.info((await self._proc.stdout.read(50)).decode())
            await asyncio.sleep(0.2)
        self._log.info('Exiting %s', self.__class__.__name__)


class ServiceStreamerTask(AbstractServiceTask):
    type = ServiceType.STREAM

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._exit_msg = (
            f'Exiting {self.service.name.value} stream task '
            f'for "{self._cam.description}"'
        )

    @retry(retry=retry_if_exception_type(Exception), wait=wait_fixed(0.1))
    async def run(self) -> None:
        self._log.debug(
            'Starting %s stream task for "%s"',
            self.service.name.value,
            self._cam.description,
        )
        try:
            while self.service.started or self._run_forever:
                while not self.service.need_restart and self.service.alive:
                    if not self._run_forever and self._should_exit():
                        break
                    await shallow_sleep_async(1)
                else:
                    if not self._run_forever and self._should_exit():
                        break
                    self._log.info('Restarting %s stream', self.service.name.value)
                    await self.service.restart()
                await shallow_sleep_async(1)
        except HikvisionCamError as err:
            self._log.error(err)
            raise
        except Exception:
            err_msg = f'Unknown error in {self.service.name.value} stream task'
            self._log.exception(err_msg)
            raise
        self._log.info(self._exit_msg)

    def _should_exit(self) -> bool:
        return not self.service.started
