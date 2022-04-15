"""Camera Bot Module."""
import logging
from typing import Optional

from pyrogram import Client

from hikcamerabot.config.config import get_main_config
from hikcamerabot.dispatchers.event_result import ResultDispatcher
from hikcamerabot.dispatchers.event_task import EventDispatcher
from hikcamerabot.managers.result_worker import ResultWorkerManager
from hikcamerabot.registry import CameraRegistry
from hikcamerabot.utils.task import create_task


class CameraBot(Client):
    """Extended aiogram's 'Bot' class."""

    def __init__(self) -> None:
        conf = get_main_config()
        super().__init__(
            session_name='default_session',
            api_id=conf.telegram.api_id,
            api_hash=conf.telegram.api_hash,
            bot_token=conf.telegram.token,
        )
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.info('Initializing bot')
        self.user_ids: list[int] = conf.telegram.allowed_user_ids
        self.cam_registry: Optional[CameraRegistry] = None
        self.event_dispatcher = EventDispatcher(bot=self)
        self.result_dispatcher = ResultDispatcher(bot=self)
        self.result_worker_manager = ResultWorkerManager(self.result_dispatcher)

    def add_cam_registry(self, cam_registry: CameraRegistry) -> None:
        # TODO: Get rid of this injection.
        self.cam_registry = cam_registry

    def start_tasks(self) -> None:
        """Start and forget async launch tasks per camera. They start all
        enabled services on user cameras like motion detection etc.
        """
        self.result_worker_manager.start_worker_tasks()
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
            f'{(await self.get_me()).first_name} bot started, see /help for '
            f'available commands')

    async def send_message_all(self, msg: str, **kwargs) -> None:
        """Send message to all defined user IDs in config.json."""
        for user_id in self.user_ids:
            try:
                await self.send_message(user_id, msg, **kwargs)
            except Exception:
                self._log.exception('Failed to send message "%s" to user ID '
                                    '%s', msg, user_id)
