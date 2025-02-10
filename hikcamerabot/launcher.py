import logging
from typing import TYPE_CHECKING

from hikcamerabot.bot_setup import BotSetup
from hikcamerabot.version import __version__

if TYPE_CHECKING:
    from hikcamerabot.camerabot import CameraBot


class BotLauncher:
    """Bot launcher which parses configuration file, creates bot with camera instances and finally starts the bot."""

    def __init__(self) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._bot: CameraBot | None = None

    async def launch(self) -> None:
        """Set up and launch bot."""
        self._setup_bot()
        await self._start_bot()

    def _setup_bot(self) -> None:
        bot_setup = BotSetup()
        bot_setup.perform_setup()
        self._bot = bot_setup.get_bot()

    async def _start_bot(self) -> None:
        """Start telegram bot and related processes."""
        await self._bot.start()

        bot_name = (await self._bot.get_me()).first_name
        self._log.info('Starting "%s" bot version %s', bot_name, __version__)

        self._bot.start_tasks()
        await self._bot.send_startup_message()

        self._log.info('Telegram bot "%s" has started', bot_name)
        await self._bot.run_forever()
