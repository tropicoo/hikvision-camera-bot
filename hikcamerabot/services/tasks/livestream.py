import asyncio
import logging

from hikcamerabot.constants import Stream
from hikcamerabot.exceptions import HikvisionCamError
from hikcamerabot.services.tasks.abstract import AbstractServiceTask
from hikcamerabot.utils.utils import shallow_sleep_async


class FfmpegStdoutReaderTask:
    """Log async ffmpeg stdout."""

    def __init__(self, proc: asyncio.subprocess.Process):
        self._log = logging.getLogger(self.__class__.__name__)
        self._proc = proc

    async def run(self) -> None:
        while self._proc.returncode is None:
            line = await self._proc.stdout.readline()
            self._log.info(line.decode())
        self._log.info('Exiting %s', self.__class__.__name__)


class ServiceStreamerTask(AbstractServiceTask):
    type = Stream.SERVICE_TYPE

    def __init__(self, service):
        super().__init__(service)
        self._exit_msg = f'Exiting {self.service.name} stream task ' \
                         f'for "{self._cam.description}"'

    async def run(self) -> None:
        self._log.debug('Starting %s stream task for "%s"',
                        self.service.name, self._cam.description)
        try:
            while self.service.started:
                while not self.service.need_restart and self.service.alive:
                    if self._should_exit():
                        break
                    await shallow_sleep_async(1)
                else:
                    if self._should_exit():
                        break
                    self._log.info('Restarting %s stream', self.service.name)
                    await self.service.restart()
                await shallow_sleep_async(1)
        except HikvisionCamError as err:
            self._log.error(err)
        except Exception:
            err_msg = f'Unknown error in {self.service.name} stream task'
            self._log.exception(err_msg)
        self._log.debug(self._exit_msg)

    def _should_exit(self) -> bool:
        if not self.service.started:
            return True
        return False
