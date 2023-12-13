"""Alarm module."""

import asyncio
from typing import TYPE_CHECKING, AsyncGenerator

from addict import Dict

from hikcamerabot.clients.hikvision import HikvisionAPI
from hikcamerabot.constants import DETECTION_SWITCH_MAP
from hikcamerabot.enums import Alarm, Detection, ServiceType
from hikcamerabot.exceptions import HikvisionAPIError, ServiceRuntimeError
from hikcamerabot.services.abstract import AbstractService
from hikcamerabot.services.alarm.camera.tasks.alarm_monitoring_task import (
    ServiceAlarmMonitoringTask,
)
from hikcamerabot.utils.task import create_task

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam
    from hikcamerabot.camerabot import CameraBot


class AlarmService(AbstractService):
    """Alarm Service Class."""

    ALARM_TRIGGERS = Detection.choices()

    type = ServiceType.ALARM
    name = Alarm.ALARM

    def __init__(
        self, conf: Dict, api: HikvisionAPI, cam: 'HikvisionCam', bot: 'CameraBot'
    ):
        super().__init__(cam)
        self._conf = conf
        self._api = api
        self.bot = bot
        self.alert_delay: int = conf.delay
        self._alert_count = 0

        self._started = asyncio.Event()

    @property
    def alert_count(self) -> int:
        return self._alert_count

    def increase_alert_count(self) -> None:
        self._alert_count += 1

    @property
    def started(self) -> bool:
        """Check if alarm is enabled."""
        return self._started.is_set()

    @property
    def enabled_in_conf(self) -> bool:
        """Check if any alarm trigger is enabled in conf."""
        for trigger in self.ALARM_TRIGGERS:
            if self._conf[trigger].enabled:
                return True
        return False

    async def start(self) -> None:
        """Enable alarm service and enable triggers on physical camera."""
        if self.cam.is_behind_nvr:
            self._log.info(
                '[%s] Do not start Alarm Service - camera is behind NVR', self.cam.id
            )
            return

        if self.started:
            raise ServiceRuntimeError('Alarm (alert) mode already started')
        await self._enable_triggers_on_camera()
        self._started.set()
        self._start_service_task()

    def _start_service_task(self) -> None:
        task_name = f'{ServiceAlarmMonitoringTask.__name__}_{self.cam.id}'
        create_task(
            ServiceAlarmMonitoringTask(service=self).run(),
            task_name=task_name,
            logger=self._log,
            exception_message='Task "%s" raised an exception',
            exception_message_args=(task_name,),
        )

    async def _enable_triggers_on_camera(self) -> None:
        for trigger in self.ALARM_TRIGGERS:
            if self._conf[trigger].enabled:
                await self.trigger_switch(trigger=Detection(trigger), state=True)

    async def stop(self) -> None:
        """Disable alarm."""
        if not self.started:
            raise ServiceRuntimeError('Alarm alert mode already stopped')
        self._started.clear()

    async def alert_stream(self) -> AsyncGenerator[str, None]:
        """Get Alarm stream from Hikvision Camera."""
        async for chunk in self._api.alert_stream():
            yield chunk

    async def trigger_switch(self, trigger: Detection, state: bool) -> str | None:
        """Trigger switch."""
        full_name: str = DETECTION_SWITCH_MAP[trigger]['name'].value
        self._log.debug('%s %s', 'Enabling' if state else 'Disabling', full_name)
        try:
            return await self._api.switch(trigger=trigger, state=state)
        except HikvisionAPIError as err:
            err_msg = f'{full_name} Switch encountered an error: {err}'
            self._log.error(err_msg)
            raise ServiceRuntimeError(err_msg)
