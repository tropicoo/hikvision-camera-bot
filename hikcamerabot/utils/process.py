import asyncio
import contextlib
import logging
import os
import re
import shlex
import signal
from asyncio.subprocess import Process
from signal import Signals
from typing import Any, Final

_log = logging.getLogger(__name__)

_KILL_WAIT_TIMEOUT: Final[float] = 10.0

# `rtsp://user:password@host` -> `rtsp://user:***@host`
_URL_CREDENTIALS_REGEX: Final[re.Pattern[str]] = re.compile(
    r'(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*://)(?P<user>[^:@/\s"\']*):[^@\s"\']*@'
)
# `rtmps://dc4-1.rtmp.t.me/s/KEY` -> `rtmps://dc4-1.rtmp.t.me/s/***`.
# Stream keys of external services (Telegram, YouTube) are the last path part.
# Local SRS URLs (IP address or SRS container name) are kept for debugging.
_STREAM_KEY_REGEX: Final[re.Pattern[str]] = re.compile(
    r'(?P<prefix>rtmps?://(?P<host>[^/\s"\':]+)(?::\d+)?/(?:[^\s"\']*/)?)'
    r'(?P<key>[^/\s"\']+)'
)
_LOCAL_STREAM_HOSTS: Final[frozenset[str]] = frozenset(
    ('localhost', 'hikvision_srs_server')
)
# `-password "secret"` -> `-password "***"`
_PASSWORD_ARG_REGEX: Final[re.Pattern[str]] = re.compile(
    r'(?P<arg>-password\s+)(?:"[^"]*"|\'[^\']*\'|\S+)'
)

# All subprocesses started with `start_process`. Used to gracefully stop
# ffmpeg (e.g. to finalize DVR segments) on bot shutdown.
_RUNNING_PROCESSES: set[Process] = set()


def mask_secrets(text: str) -> str:
    """Hide credentials in commands/URLs before writing them to logs."""
    text = _URL_CREDENTIALS_REGEX.sub(r'\g<scheme>\g<user>:***@', text)
    text = _STREAM_KEY_REGEX.sub(_mask_stream_key, text)
    return _PASSWORD_ARG_REGEX.sub(r'\g<arg>"***"', text)


def _mask_stream_key(match: re.Match[str]) -> str:
    host = match['host']
    if host in _LOCAL_STREAM_HOSTS or host.replace('.', '').isdigit():
        return match[0]
    return f'{match["prefix"]}***'


async def start_process(cmd: str, **kwargs: Any) -> Process:
    """Start a command without a shell, in its own process group.

    The command string is split with POSIX shell rules, so existing quoted
    command templates keep working, but nothing is interpreted by a shell
    (no variable expansion, no injection through config values).
    """
    proc = await asyncio.create_subprocess_exec(
        *shlex.split(cmd), start_new_session=True, **kwargs
    )
    # Forget already finished processes.
    for finished in [p for p in _RUNNING_PROCESSES if p.returncode is not None]:
        _RUNNING_PROCESSES.discard(finished)
    _RUNNING_PROCESSES.add(proc)
    return proc


async def get_stdout_stderr(proc: Process) -> tuple[str, str]:
    stdout = await proc.stdout.read() if proc.stdout else b''
    stderr = await proc.stderr.read() if proc.stderr else b''
    return (
        stdout.decode(errors='replace').strip(),
        stderr.decode(errors='replace').strip(),
    )


def _send_signal(process: Process, signal_: Signals) -> None:
    """Signal process group if the process owns one, otherwise only the process.

    Never signal our own process group - that would interrupt the bot itself.
    """
    pgid = os.getpgid(process.pid)
    if pgid != os.getpgid(0):
        os.killpg(pgid, signal_)
    else:
        process.send_signal(signal_)


async def kill_proc(
    process: Process,
    signal_: Signals = signal.SIGINT,
    reraise: bool = True,
    wait_timeout: float = _KILL_WAIT_TIMEOUT,
) -> None:
    """Stop the process gracefully, falling back to SIGKILL if it hangs."""
    try:
        if process.returncode is not None:
            return
        _send_signal(process, signal_)
        try:
            await asyncio.wait_for(process.wait(), timeout=wait_timeout)
        except TimeoutError:
            _log.warning(
                'Process %s did not exit in %ss after %s, killing it',
                process.pid,
                wait_timeout,
                signal_.name,
            )
            with contextlib.suppress(ProcessLookupError):
                _send_signal(process, signal.SIGKILL)
            await process.wait()
    except Exception:
        if reraise:
            raise


async def terminate_all_processes(wait_timeout: float = _KILL_WAIT_TIMEOUT) -> None:
    """Gracefully stop every still running subprocess (used on shutdown)."""
    procs = [proc for proc in _RUNNING_PROCESSES if proc.returncode is None]
    if not procs:
        return
    _log.info('Stopping %d running subprocess(es)', len(procs))
    await asyncio.gather(
        *(
            kill_proc(proc, signal.SIGINT, reraise=False, wait_timeout=wait_timeout)
            for proc in procs
        )
    )
