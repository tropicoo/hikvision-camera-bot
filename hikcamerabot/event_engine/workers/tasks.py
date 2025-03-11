import logging
from typing import TYPE_CHECKING

from hikcamerabot.event_engine.queue import get_result_queue
from hikcamerabot.utils.shared import shallow_sleep_async

if TYPE_CHECKING:
    from hikcamerabot.event_engine.dispatchers.outbound import OutboundEventDispatcher


class ResultWorkerTask:
    def __init__(
        self, outbound_dispatcher: 'OutboundEventDispatcher', worker_id: int
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._outbound_dispatcher = outbound_dispatcher
        self._worker_id = worker_id
        self._res_queue = get_result_queue()

    async def run(self) -> None:
        while True:
            while not self._res_queue.empty():
                event = await self._res_queue.get()
                try:
                    await self._outbound_dispatcher.dispatch(event)
                except Exception:
                    self._log.exception(
                        'Unhandled exception in result worker %s. Event context: %s',
                        self._worker_id,
                        event,
                    )
            await shallow_sleep_async(0.2)
