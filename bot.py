#!/usr/bin/env python3
"""Bot Launcher Module."""

import asyncio

from hikcamerabot.launcher import BotLauncher
from hikcamerabot.utils.shared import setup_logging

try:
    import uvloop
except ImportError:  # uvloop is installed only on Linux.
    uvloop = None


async def main() -> None:
    setup_logging()
    await BotLauncher().launch()


if __name__ == '__main__':
    if uvloop is not None:
        uvloop.run(main())
    else:
        asyncio.run(main())
