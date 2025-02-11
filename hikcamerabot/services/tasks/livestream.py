import asyncio
import logging
from typing import Literal

from tenacity import retry, retry_if_exception_type, wait_fixed

from hikcamerabot.enums import ServiceType
from hikcamerabot.exceptions import HikvisionCamError
from hikcamerabot.services.abstract import AbstractServiceTask
from hikcamerabot.utils.shared import shallow_sleep_async


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
    TYPE: Literal[ServiceType.STREAM] = ServiceType.STREAM

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._exit_msg = (
            f'[{self._cam.id}] Exiting {self.service.NAME.value} stream task '
            f'for "{self._cam.description}"'
        )

    @retry(retry=retry_if_exception_type(Exception), wait=wait_fixed(0.1))
    async def run(self) -> None:
        self._log.debug(
            '[%s] Starting %s stream task for "%s"',
            self._cam.id,
            self.service.NAME,
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
                    self._log.info(
                        '[%s] Restarting %s stream [need restart: %s] [is alive: %s]',
                        self._cam.id,
                        self.service.NAME,
                        self.service.need_restart,
                        self.service.alive,
                    )
                    await self.service.restart()
                await shallow_sleep_async(1)
        except HikvisionCamError as err:
            self._log.error(err)
            raise
        except Exception:
            self._log.exception(
                '[%s] Unknown error in %s stream task',
                self._cam.id,
                self.service.NAME,
            )
            raise
        self._log.info(self._exit_msg)

    def _should_exit(self) -> bool:
        return not self.service.started
