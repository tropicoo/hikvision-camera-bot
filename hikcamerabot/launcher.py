import asyncio
import logging

from hikcamerabot.bot_setup import BotSetup
from hikcamerabot.version import __version__


class BotLauncher:
    """Bot launcher which parses configuration file, creates bot with
    camera instances and finally starts the bot.
    """

    def __init__(self) -> None:
        """Constructor."""
        self._log = logging.getLogger(self.__class__.__name__)
        self._setup = BotSetup()
        self._bot = self._setup.get_bot()

    async def launch(self) -> None:
        """Launch bot."""
        await self._start_bot()

    async def _start_bot(self) -> None:
        """Start telegram bot and related processes."""
        await self._bot.start()

        bot_name = (await self._bot.get_me()).first_name
        self._log.info('Starting "%s" bot version %s', bot_name, __version__)

        self._bot.start_tasks()
        await self._bot.send_startup_message()

        self._log.info('Bot "%s" has started', bot_name)
        await self._run_bot_forever()

    async def _run_bot_forever(self) -> None:
        """That's how we roll."""
        while True:
            await asyncio.sleep(86400)
