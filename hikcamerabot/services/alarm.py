"""Alarm module."""

import asyncio
from typing import AsyncGenerator, Optional

from addict import Addict

from hikcamerabot.clients.hikvision import HikvisionAPI
from hikcamerabot.constants import Alarm, DETECTION_SWITCH_MAP, Detection
from hikcamerabot.exceptions import HikvisionAPIError, ServiceRuntimeError
from hikcamerabot.services.abstract import AbstractService
from hikcamerabot.services.tasks.alarm import ServiceAlarmPusherTask
from hikcamerabot.utils.task import create_task


class AlarmService(AbstractService):
    """Alarm Service Class."""

    ALARM_TRIGGERS: frozenset[str] = Detection.choices()

    def __init__(self, conf: Addict, api: HikvisionAPI, cam: 'HikvisionCam', bot):
        super().__init__(cam)
        self._conf = conf
        self._api = api
        self.bot = bot
        self.alert_delay: int = conf.delay
        self._alert_count = 0

        self._started = asyncio.Event()

        self.type: str = Alarm.SERVICE_TYPE
        self.name: str = Alarm.ALARM

    @property
    def alert_count(self) -> int:
        return self._alert_count

    def increase_alert_count(self):
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
        if self.started:
            raise ServiceRuntimeError('Alarm (alert) mode already started')
        await self._enable_triggers_on_camera()
        self._start_service_tasks()

    def _start_service_tasks(self) -> None:
        task_name = f'{ServiceAlarmPusherTask.__name__}_{self.cam.id}'
        create_task(
            ServiceAlarmPusherTask(service=self).run(),
            task_name=task_name,
            logger=self._log,
            exception_message='Task %s raised an exception',
            exception_message_args=(task_name,),
        )

    async def _enable_triggers_on_camera(self) -> None:
        for trigger in self.ALARM_TRIGGERS:
            if self._conf[trigger].enabled:
                await self.trigger_switch(enable=True, trigger=trigger)
        self._started.set()

    async def stop(self) -> None:
        """Disable alarm."""
        if not self.started:
            raise ServiceRuntimeError('Alarm alert mode already stopped')
        self._started.clear()

    async def alert_stream(self) -> AsyncGenerator:
        """Get Alarm stream from Hikvision Camera."""
        async for chunk in self._api.alert_stream():
            yield chunk

    async def trigger_switch(self, enable: bool, trigger: str) -> Optional[str]:
        """Trigger switch."""
        full_name = DETECTION_SWITCH_MAP[trigger]['name']
        self._log.debug('%s %s', 'Enabling' if enable else 'Disabling', full_name)
        try:
            return await self._api.switch(enable=enable, trigger=trigger)
        except HikvisionAPIError as err:
            err_msg = f'{full_name} Switch encountered an error: {err}'
            self._log.error(err_msg)
            raise ServiceRuntimeError(err_msg)
