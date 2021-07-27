import logging
from collections import defaultdict

from aiogram import Dispatcher

from hikcamerabot.camera import HikvisionCam
from hikcamerabot.camerabot import CameraBot
from hikcamerabot.commands import setup_commands
from hikcamerabot.config.config import get_main_config
from hikcamerabot.registry import CameraRegistry


class BotSetup:
    """Setup everything before bot start."""

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        self._conf = get_main_config()
        self._bot = CameraBot()
        self._dispatcher = Dispatcher(bot=self._bot)
        cam_registry = self._create_and_setup_cameras()
        self._bot.add_cam_registry(cam_registry)

    def _create_and_setup_cameras(self) -> CameraRegistry:
        """Create cameras and setup for the dispatcher.

        Iterate trough the config, create event queues per camera,
        setup camera registry and command callbacks (handlers).
        """
        cam_registry = CameraRegistry()
        tpl_cmds, global_cmds = setup_commands()

        for cam_id, cam_conf in self._conf.camera_list.items():
            cam_cmds = defaultdict(list)
            for description, group in tpl_cmds.items():
                for cmd, callback in group['commands'].items():
                    cmd = cmd.format(cam_id)
                    cam_cmds[description].append(cmd)
                    self._dispatcher.register_message_handler(callback,
                                                              commands=cmd)

            cam = HikvisionCam(cam_id, cam_conf, bot=self._bot)
            cam_registry.add(cam_id, cam, cam_cmds)

        self._setup_global_cmds(global_cmds)
        self._log.debug('Camera Meta Registry: %r', cam_registry)
        return cam_registry

    def _setup_global_cmds(self, global_cmds: dict) -> None:
        """Set up global bot command callbacks (handlers) in place."""
        for cmd, callback in global_cmds.items():
            self._dispatcher.register_message_handler(callback, commands=cmd)

    def get_bot(self) -> CameraBot:
        return self._bot

    def get_dispatcher(self) -> Dispatcher:
        return self._dispatcher
