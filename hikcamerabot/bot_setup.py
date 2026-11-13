import logging
import re
from collections import defaultdict
from collections.abc import Callable

from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from hikcamerabot.callbacks import cmd_list_group_cams, cmd_unknown
from hikcamerabot.camera import HikvisionCam
from hikcamerabot.camerabot import CameraBot
from hikcamerabot.commands import setup_commands
from hikcamerabot.config.config import main_conf
from hikcamerabot.menu import (
    CALLBACK_PREFIX,
    MENU_BUTTON_TEXT,
    cmd_menu,
    on_menu_callback,
)
from hikcamerabot.utils.shared import build_command_presentation


class BotSetup:
    """Setup everything before bot start."""

    def __init__(self) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._bot = CameraBot()

    def perform_setup(self) -> None:
        self._create_and_setup_cameras()

    def _create_and_setup_cameras(self) -> None:
        """Create cameras and setup for the dispatcher.

        Iterate through the config, create event queues per camera,
        setup camera registry and command callbacks (handlers).

        Hidden (undesirable) cameras will be excluded from the setup.
        """
        tpl_cmds, global_cmds = setup_commands()

        for cam_id, cam_conf in main_conf.camera_list.items():
            if cam_conf.hidden:
                self._log.info(
                    '[%s] Do not initialize camera "%s" because it is hidden',
                    cam_id,
                    cam_conf.description,
                )
                continue

            cam_cmds = defaultdict(list)
            for description, group in tpl_cmds.items():
                for cmd_, callback in group['commands'].items():
                    cmd = cmd_.format(cam_id)
                    cam_cmds[description].append(cmd)
                    self._setup_message_handler(callback, cmd)

            cam = HikvisionCam(id_=cam_id, conf=cam_conf, bot=self._bot)
            self._bot.cam_registry.add(
                cam=cam,
                commands=cam_cmds,
                commands_presentation=build_command_presentation(cam_cmds, cam),
            )

        self._setup_global_cmds(global_cmds)
        self._setup_group_cmds()
        self._setup_menu_callbacks()
        self._setup_unknown_command_handler()
        self._log.debug('Camera Meta Registry: %r', self._bot.cam_registry)

    def _setup_message_handler(self, callback: Callable, cmd: str) -> None:
        self._bot.add_handler(
            MessageHandler(
                callback,
                filters=filters.user(self._bot.chat_users) & filters.command(cmd),
            )
        )

    def _setup_global_cmds(self, global_cmds: dict) -> None:
        """Set up global bot command callbacks (handlers) in place."""
        for cmd, callback in global_cmds.items():
            self._setup_message_handler(callback, cmd)

    def _setup_menu_callbacks(self) -> None:
        self._bot.add_handler(
            MessageHandler(
                cmd_menu,
                filters=filters.user(self._bot.chat_users)
                & filters.regex(f'^{re.escape(MENU_BUTTON_TEXT)}$'),
            )
        )
        self._bot.add_handler(
            CallbackQueryHandler(
                on_menu_callback,
                filters=filters.user(self._bot.chat_users)
                & filters.regex(f'^{CALLBACK_PREFIX}\\|'),
            )
        )

    def _setup_unknown_command_handler(self) -> None:
        """Answer to unknown commands, e.g. a typo or `/getpic_cam_9`.

        Must be registered last: Pyrogram runs only the first matching handler
        of a group, so this one gets only commands nobody else handled.
        """
        self._bot.add_handler(
            MessageHandler(
                cmd_unknown,
                filters=filters.user(self._bot.chat_users) & filters.regex(r'^/\w'),
            )
        )

    def _setup_group_cmds(self) -> None:
        for cmd in self._bot.cam_registry.get_groups_registry():
            self._setup_message_handler(cmd_list_group_cams, cmd)

    def get_bot(self) -> CameraBot:
        return self._bot
