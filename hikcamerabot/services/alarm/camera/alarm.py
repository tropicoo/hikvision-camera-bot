"""Alarm module."""

import asyncio
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Literal

from hikcamerabot.clients.hikvision import HikvisionAPI
from hikcamerabot.config.schemas.main_config import AlertSchema
from hikcamerabot.constants import DETECTION_SWITCH_MAP
from hikcamerabot.enums import AlarmType, DetectionType, ServiceType
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

    ALARM_TRIGGERS = DetectionType.choices()

    NAME: Literal[AlarmType.ALARM] = AlarmType.ALARM
    TYPE: Literal[ServiceType.ALARM] = ServiceType.ALARM

    def __init__(
        self,
        conf: AlertSchema,
        api: HikvisionAPI,
        cam: 'HikvisionCam',
        bot: 'CameraBot',
    ) -> None:
        super().__init__(cam)
        self._conf = conf
        self._api = api
        self.bot = bot
        self.alert_delay: int = conf.delay
        self._alert_count: int = 0

        self._started: asyncio.Event = asyncio.Event()
        self._monitoring_task: asyncio.Task | None = None

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
    def conf(self) -> AlertSchema:
        return self._conf

    def update_conf(self, conf: AlertSchema) -> None:
        """Apply alert settings changed from the bot menu without restart."""
        self._conf = conf
        self.alert_delay = conf.delay

    @property
    def enabled_in_conf(self) -> bool:
        """Check if alarm is enabled and any alarm trigger is enabled in conf."""
        return self._conf.enabled and any(
            self._conf.get_detection_schema_by_type(type_=trigger).enabled
            for trigger in self.ALARM_TRIGGERS
        )

    async def start(self) -> None:
        """Enable alarm service and enable triggers on physical camera."""
        if self.cam.is_behind_nvr:
            self._log.info(
                '[%s] Do not start Alarm Service - camera is behind NVR', self.cam.id
            )
            return

        if self.started:
            raise ServiceRuntimeError('Оповещения уже включены')
        await self._enable_triggers_on_camera()
        self._started.set()
        self._start_service_task()

    def _start_service_task(self) -> None:
        # Quick `alert_off` -> `alert_on` could leave the old task alive (it
        # checks the state only on the next chunk) and duplicate every alert.
        self._cancel_service_task()
        task_name = f'{ServiceAlarmMonitoringTask.__name__}_{self.cam.id}'
        self._monitoring_task = create_task(
            ServiceAlarmMonitoringTask(service=self).run(),
            task_name=task_name,
            logger=self._log,
            exception_message='Task "%s" raised an exception',
            exception_message_args=(task_name,),
        )

    async def _enable_triggers_on_camera(self) -> None:
        """Enable triggers which are enabled in config.

        Some (old) cameras don't support e.g. Line Crossing Detection and return
        an error. Then just warn and keep monitoring the alert stream: other
        detections (or ones enabled manually in camera web UI) still work.
        """
        for trigger in self.ALARM_TRIGGERS:
            if not self._conf.get_detection_schema_by_type(type_=trigger).enabled:
                continue
            try:
                await self.trigger_switch(trigger=DetectionType(trigger), state=True)
            except ServiceRuntimeError as err:
                self._log.warning(
                    '[%s] %s. Is it supported by the camera and is the user allowed '
                    'to change it? Configure it in camera web UI or set '
                    '"enabled": false for it in config to hide this warning',
                    self.cam.id,
                    err,
                )

    async def stop(self) -> None:
        """Disable alarm."""
        if not self.started:
            raise ServiceRuntimeError('Оповещения уже выключены')
        self._started.clear()
        self._cancel_service_task()

    def _cancel_service_task(self) -> None:
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
        self._monitoring_task = None

    async def alert_stream(self) -> AsyncGenerator[str]:
        """Get Alarm stream from Hikvision Camera."""
        async for chunk in self._api.alert_stream():
            yield chunk

    async def trigger_switch(self, trigger: DetectionType, state: bool) -> str | None:
        """Trigger switch."""
        full_name = DETECTION_SWITCH_MAP[trigger]['name']
        self._log.debug('%s %s', 'Enabling' if state else 'Disabling', full_name)
        try:
            return await self._api.switch(trigger=trigger, state=state)
        except HikvisionAPIError as err:
            err_msg = f'{full_name} Switch encountered an error: {err}'
            self._log.error(err_msg)
            raise ServiceRuntimeError(err_msg) from err
