"""Camera Bot Module."""
import logging
from typing import Optional

from aiogram import Bot

from hikcamerabot.config.config import get_main_config
from hikcamerabot.dispatchers.event_result import ResultDispatcher
from hikcamerabot.dispatchers.event_task import EventDispatcher
from hikcamerabot.registry import CameraRegistry
from hikcamerabot.utils.task import create_task


class CameraBot(Bot):
    """Extended aiogram `Bot` class."""

    def __init__(self):
        conf = get_main_config()
        super().__init__(conf.telegram.token)
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.info('Initializing bot')
        self.user_ids = conf.telegram.allowed_user_ids
        self.cam_registry: Optional[CameraRegistry] = None
        self.event_dispatcher = EventDispatcher()
        self.result_dispatcher = ResultDispatcher()

    def add_cam_registry(self, cam_registry: CameraRegistry):
        # TODO: Rework.
        self.cam_registry = cam_registry

    async def start_tasks(self) -> None:
        """Start async launch tasks per camera."""
        # await self.result_work_manager.start_worker_tasks()
        for cam in self.cam_registry.get_instances():
            task_name = f'{cam.id} launch task'
            create_task(
                cam.service_manager.start_all(only_conf_enabled=True),
                task_name=task_name,
                logger=self._log,
                exception_message='Task %s raised an exception',
                exception_message_args=(task_name,),
            )

    async def send_startup_message(self) -> None:
        """Send welcome message after bot launch."""
        self._log.info('Sending welcome message')
        await self.send_message_all(
            f'{(await self.me).first_name} bot started, see /help for '
            f'available commands')

    async def send_message_all(self, msg: str) -> None:
        """Send message to all defined user IDs in config.json."""
        for user_id in self.user_ids:
            try:
                await self.send_message(user_id, msg)
            except Exception:
                self._log.exception('Failed to send message "%s" to user ID '
                                    '%s', msg, user_id)
