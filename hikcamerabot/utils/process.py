import os
import signal
from asyncio.subprocess import Process
from signal import Signals

from hikcamerabot.utils.task import wrap


async def get_stdout_stderr(proc: Process) -> tuple[str, str]:
    stdout, stderr = await proc.stdout.read(), await proc.stderr.read()
    return stdout.decode().strip(), stderr.decode().strip()


async def kill_proc(
    process: Process, signal_: Signals = signal.SIGINT, reraise: bool = True
) -> None:
    try:
        await wrap(os.killpg)(os.getpgid(process.pid), signal_)
    except Exception:
        if reraise:
            raise
