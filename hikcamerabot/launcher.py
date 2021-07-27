import logging

from hikcamerabot.config.config import get_main_config
from hikcamerabot.setup import BotSetup
from hikcamerabot.version import __version__


class BotLauncher:
    """Bot launcher which parses configuration file, creates bot with
    camera instances and finally starts the bot.
    """

    def __init__(self):
        """Constructor."""
        self._log = logging.getLogger(self.__class__.__name__)
        logging.getLogger().setLevel(get_main_config().log_level)
        self._setup = BotSetup()
        self._bot = self._setup.get_bot()
        self._dispatcher = self._setup.get_dispatcher()

    async def run(self) -> None:
        """Run bot and DirectoryWatcher."""
        self._log.info('Starting %s bot version %s',
                       (await self._bot.me).first_name, __version__)
        await self._start_bot()

    async def _start_bot(self) -> None:
        """Start telegram bot and related processes."""
        await self._bot.start_tasks()
        await self._bot.send_startup_message()

        # TODO: Look into theirs `executor`.
        try:
            await self._dispatcher.start_polling()
        finally:
            await self._dispatcher.bot.close()
