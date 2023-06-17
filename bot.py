#!/usr/bin/env python3
"""Bot Launcher Module."""

import asyncio

import uvloop

from hikcamerabot.launcher import BotLauncher
from hikcamerabot.utils.shared import setup_logging


async def main() -> None:
    setup_logging()
    await BotLauncher().launch()


if __name__ == '__main__':
    uvloop.install()
    asyncio.run(main())
