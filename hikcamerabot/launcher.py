import asyncio
import contextlib
import logging
import signal
from typing import TYPE_CHECKING

from hikcamerabot.bot_setup import BotSetup
from hikcamerabot.utils.process import terminate_all_processes
from hikcamerabot.utils.task import cancel_background_tasks
from hikcamerabot.version import __version__

if TYPE_CHECKING:
    from hikcamerabot.camerabot import CameraBot


class BotLauncher:
    """Bot launcher which parses configuration file, creates bot with camera instances and finally starts the bot."""

    def __init__(self) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._bot: CameraBot | None = None
        self._stop_event = asyncio.Event()

    async def launch(self) -> None:
        """Set up and launch bot."""
        self._setup_bot()
        self._setup_signal_handlers()
        try:
            await self._start_bot()
        finally:
            await self._shutdown()

    def _setup_bot(self) -> None:
        bot_setup = BotSetup()
        bot_setup.perform_setup()
        self._bot = bot_setup.get_bot()

    def _setup_signal_handlers(self) -> None:
        """Stop gracefully on `docker stop` (SIGTERM) and Ctrl+C (SIGINT)."""
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, self._on_signal, sig)

    def _on_signal(self, sig: signal.Signals) -> None:
        self._log.info('Received %s, stopping the bot', sig.name)
        self._stop_event.set()

    async def _start_bot(self) -> None:
        """Start telegram bot and related processes."""
        await self._bot.start()

        bot_name = (await self._bot.get_me()).first_name
        self._log.info('Starting "%s" bot version %s', bot_name, __version__)

        self._bot.start_tasks()
        await self._bot.set_commands_menu()
        await self._bot.send_startup_message()

        self._log.info('Telegram bot "%s" has started', bot_name)
        await self._stop_event.wait()

    async def _shutdown(self) -> None:
        """Stop tasks, ffmpeg processes (finalizes DVR/video files) and client."""
        self._log.info('Shutting down')
        # Cancel tasks first so stream watchers don't restart stopped ffmpeg.
        for step in (
            cancel_background_tasks,
            terminate_all_processes,
            self._stop_client,
        ):
            try:
                await step()
            except Exception:
                self._log.exception('Shutdown step "%s" failed', step.__name__)
        self._log.info('Bot stopped')

    async def _stop_client(self) -> None:
        if self._bot and self._bot.is_connected:
            await self._bot.stop()
