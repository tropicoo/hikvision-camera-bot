import asyncio
from functools import cached_property
from typing import TYPE_CHECKING

from hikcamerabot.clients.hikvision import HikvisionAPI
from hikcamerabot.config.schemas.main_config import TimelapseSchema
from hikcamerabot.exceptions import ServiceRuntimeError
from hikcamerabot.services.abstract import AbstractService
from hikcamerabot.services.timelapse.task import TimelapseTask
from hikcamerabot.utils.task import create_task

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam
    from hikcamerabot.camerabot import CameraBot


class TimelapseService(AbstractService):
    def __init__(
        self,
        configs: list[TimelapseSchema],
        api: HikvisionAPI,
        cam: 'HikvisionCam',
        bot: 'CameraBot',
    ) -> None:
        super().__init__(cam)
        self._configs = configs
        self._api = api
        self.bot = bot

        self._started = asyncio.Event()

    async def start(self) -> None:
        if self.started:
            raise ServiceRuntimeError('Timelapse service has already started')
        self._started.set()
        self._start_service_task()

    def _start_service_task(self) -> None:
        for conf in self._configs:
            if conf.enabled:
                task_name = f'{TimelapseTask.__name__}_{self.cam.id}_{conf.name}_{conf.start_hour}-{conf.end_hour}'
                create_task(
                    TimelapseTask(conf=conf, service=self).run(),
                    task_name=task_name,
                    logger=self._log,
                    exception_message='Task %s raised an exception',
                    exception_message_args=(task_name,),
                )

    async def stop(self) -> None:
        if not self.started:
            raise ServiceRuntimeError('Timelapse service has been already stopped')
        self._started.clear()

    @cached_property
    def enabled_in_conf(self) -> bool:
        """Check if any of the timelapses are enabled in configuration."""
        return any(conf.enabled for conf in self._configs)

    @property
    def started(self) -> bool:
        """Check if service is started."""
        return self._started.is_set()
