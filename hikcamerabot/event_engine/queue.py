from asyncio import Queue

from hikcamerabot.event_engine.events.abstract import BaseOutboundEvent
from hikcamerabot.event_engine.events.outbound import SendTextOutboundEvent

_RESULT_QUEUE = Queue()


def get_result_queue() -> Queue[BaseOutboundEvent | SendTextOutboundEvent]:
    return _RESULT_QUEUE
