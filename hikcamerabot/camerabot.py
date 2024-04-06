"""Camera Bot Module."""

import asyncio
import logging

from pyrogram import Client

from hikcamerabot.config.config import get_main_config
from hikcamerabot.event_engine.dispatchers.inbound import InboundEventDispatcher
from hikcamerabot.event_engine.dispatchers.outbound import OutboundEventDispatcher
from hikcamerabot.event_engine.workers.manager import ResultWorkerManager
from hikcamerabot.registry import CameraRegistry
from hikcamerabot.services.alarm.nvr.tasks.alarm_monitoring_task import (
    NvrAlarmMonitoringTask,
)
from hikcamerabot.utils.task import create_task


class CameraBot(Client):
    """Extended pyrogram 'Client' class."""

    def __init__(self) -> None:
        conf = get_main_config()
        super().__init__(
            name='default_client',
            api_id=conf.telegram.api_id,
            api_hash=conf.telegram.api_hash,
            bot_token=conf.telegram.token,
        )
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.info('Initializing bot client')

        self.chat_users: list[int] = conf.telegram.chat_users
        self.alert_users: list[int] = conf.telegram.alert_users
        self.startup_message_users: list[int] = conf.telegram.startup_message_users

        self.cam_registry = CameraRegistry()
        self.inbound_dispatcher = InboundEventDispatcher(bot=self)
        self.outbound_dispatcher = OutboundEventDispatcher(bot=self)
        self.result_worker_manager = ResultWorkerManager(self.outbound_dispatcher)

    def start_tasks(self) -> None:
        """Start and forget async launch per camera tasks. They start all
        enabled services on user cameras like motion detection etc.
        """
        self.result_worker_manager.start_worker_tasks()
        self._start_nvr_services()
        for cam in self.cam_registry.get_instances():
            task_name = f'{cam.id} launch task'
            create_task(
                cam.service_manager.start_all(only_conf_enabled=True),
                task_name=task_name,
                logger=self._log,
                exception_message='Task "%s" raised an exception',
                exception_message_args=(task_name,),
            )

    def _start_nvr_services(self) -> None:
        """Start NVR services which replace per-camera services due the nature of the setup."""
        nvr_cameras = self.cam_registry.get_nvr_cameras()
        for nvr_host, cameras in nvr_cameras.items():
            self._log.info(
                'Start NVR monitoring service for NVR host "%s" and cameras: %s',
                nvr_host,
                nvr_cameras,
            )
            task_name = f'{NvrAlarmMonitoringTask.__name__}_{nvr_host}'
            create_task(
                NvrAlarmMonitoringTask(host=nvr_host, cameras=cameras).run(),
                task_name=task_name,
                logger=self._log,
                exception_message='Task "%s" raised an exception',
                exception_message_args=(task_name,),
            )

    async def run_forever(self) -> None:
        """That's how we roll."""
        while True:
            await asyncio.sleep(86400)

    async def send_startup_message(self) -> None:
        """Send welcome message to defined telegram ids after bot launch."""
        text = (
            f'{(await self.get_me()).first_name} bot started, see /help for '
            f'available commands'
        )
        for user_id in self.startup_message_users:
            telegram_id_type = 'group_id' if user_id < 0 else 'user_id'
            self._log.debug(
                'Sending welcome message to %s "%d"', telegram_id_type, user_id
            )
            await self._send_message(text, user_id)

    async def send_alert_message(self, text: str, **kwargs) -> None:
        """Send message to alert users."""
        self._log.info('Sending message to alert users')
        for user_id in self.alert_users:
            await self._send_message(text, user_id, **kwargs)

    async def _send_message(self, text: str, user_id: int, **kwargs) -> None:
        try:
            await self.send_message(user_id, text, **kwargs)
        except Exception:
            self._log.exception(
                'Failed to send message "%s" to user ID %s', text, user_id
            )
