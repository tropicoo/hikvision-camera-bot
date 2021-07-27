#!/usr/bin/env python3
"""Bot Launcher Module."""

import asyncio

from hikcamerabot.launcher import BotLauncher
from hikcamerabot.utils.utils import setup_logging


async def main():
    setup_logging()
    bot_engine = BotLauncher()
    await bot_engine.run()


if __name__ == '__main__':
    asyncio.run(main())
