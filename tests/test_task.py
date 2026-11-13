import asyncio
import logging
from types import SimpleNamespace

import pytest

from hikcamerabot.utils import task as task_module
from hikcamerabot.utils.task import cancel_background_tasks, create_task, retry_forever

log = logging.getLogger(__name__)


@pytest.fixture
def sleeps(monkeypatch):
    """Record retry delays instead of really sleeping."""
    delays: list[float] = []
    real_sleep = asyncio.sleep

    async def fake_sleep(delay, *args, **kwargs):
        delays.append(delay)
        await real_sleep(0)

    monkeypatch.setattr(task_module.asyncio, 'sleep', fake_sleep)
    return delays


async def test_retry_forever_restarts_with_exponential_backoff(sleeps):
    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        if calls <= 5:
            raise ConnectionError('camera is offline')

    await retry_forever(flaky, logger=log, name='test', min_delay=1, max_delay=4)
    assert calls == 6
    assert sleeps == [1, 2, 4, 4, 4]


async def test_retry_forever_resets_delay_after_long_run(sleeps, monkeypatch):
    clock = iter([0, 1, 1, 2, 2, 1000, 1000, 1001])
    # Patch only the `time` used by the task module, not the event loop clock.
    monkeypatch.setattr(
        task_module, 'time', SimpleNamespace(monotonic=lambda: next(clock))
    )
    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        if calls <= 3:
            raise ConnectionError

    await retry_forever(
        flaky, logger=log, name='test', min_delay=1, max_delay=30, reset_after=60
    )
    # Third failure happened after ~1000s of work, so delay is reset to minimum.
    assert sleeps == [1, 2, 1]


async def test_retry_forever_does_not_swallow_cancel(sleeps):
    async def forever():
        await asyncio.Event().wait()

    task = asyncio.create_task(retry_forever(forever, logger=log, name='test'))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_create_task_keeps_strong_reference_until_done():
    event = asyncio.Event()
    task = create_task(event.wait(), logger=log, task_name='ref-test')
    assert task in task_module._BACKGROUND_TASKS
    event.set()
    await task
    await asyncio.sleep(0)
    assert task not in task_module._BACKGROUND_TASKS


async def test_cancel_background_tasks():
    task = create_task(asyncio.Event().wait(), logger=log, task_name='cancel-test')
    await cancel_background_tasks(wait_timeout=1)
    assert task.cancelled()
