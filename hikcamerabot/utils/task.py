import asyncio
import functools
import logging
import time
from collections.abc import Awaitable, Callable
from concurrent.futures import Executor
from functools import partial, wraps
from typing import Any, Final, TypeVar

T = TypeVar('T')

# The event loop keeps only weak references to tasks, so a "fire and forget"
# task without a strong reference may be garbage collected before it finishes.
# See https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
_BACKGROUND_TASKS: set[asyncio.Task] = set()

RETRY_MIN_DELAY: Final[float] = 0.5
RETRY_MAX_DELAY: Final[float] = 30.0
# If the coroutine worked at least this long, consider it healthy and reset delay.
RETRY_RESET_AFTER: Final[float] = 60.0


def create_task[T](
    coroutine: Awaitable[T],
    logger: logging.Logger,
    loop: asyncio.AbstractEventLoop | None = None,
    task_name: str | None = None,
    exception_message: str = 'Task raised an exception',
    exception_message_args: tuple[Any, ...] = (),
    thread_safe: bool = False,
) -> asyncio.Task[T]:
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning('No running asyncio loop, creating new')
            loop = asyncio.get_event_loop()

    if thread_safe:
        task = asyncio.run_coroutine_threadsafe(coroutine, loop)
    else:
        task = loop.create_task(coroutine, name=task_name)
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(_BACKGROUND_TASKS.discard)

    task.add_done_callback(
        functools.partial(
            _handle_task_result,
            logger=logger,
            exception_message=exception_message,
            exception_message_args=exception_message_args,
        )
    )
    return task


def _handle_task_result(
    task: asyncio.Task,
    logger: logging.Logger,
    exception_message: str,
    exception_message_args: tuple[Any, ...] = (),
) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception(exception_message, *exception_message_args)


async def cancel_background_tasks(wait_timeout: float = 10.0) -> None:
    """Cancel all tasks created with `create_task` (used on shutdown)."""
    tasks = [task for task in _BACKGROUND_TASKS if not task.done()]
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.wait(tasks, timeout=wait_timeout)


async def retry_forever(
    func: Callable[[], Awaitable[None]],
    logger: logging.Logger,
    name: str,
    min_delay: float = RETRY_MIN_DELAY,
    max_delay: float = RETRY_MAX_DELAY,
    reset_after: float = RETRY_RESET_AFTER,
) -> None:
    """Run `func` until it returns normally, restarting it on any exception.

    Delay between restarts grows exponentially (`min_delay` -> `max_delay`) so an
    unreachable camera doesn't flood logs and CPU, and resets to `min_delay`
    once the function has been working fine for `reset_after` seconds.
    """
    delay = min_delay
    while True:
        started_at = time.monotonic()
        try:
            await func()
        except asyncio.CancelledError:
            raise
        except Exception:
            if time.monotonic() - started_at >= reset_after:
                delay = min_delay
            logger.warning('"%s" failed, restarting in %.1f seconds', name, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)
        else:
            return


def wrap[T](func: Callable[..., T]) -> Callable[..., Awaitable[T]]:
    """Run sync code in executor."""

    @wraps(func)
    async def run(
        *args,
        loop: asyncio.AbstractEventLoop | None = None,
        executor: Executor | None = None,
        **kwargs,
    ) -> T:
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)

    return run
