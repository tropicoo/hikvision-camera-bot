import abc
import logging
from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from hikcamerabot.camerabot import CameraBot
    from hikcamerabot.event_engine.handlers.inbound import AbstractTaskEvent
    from hikcamerabot.event_engine.handlers.outbound import AbstractResultEventHandler

DispatchTypeDict = dict[str, Type['AbstractTaskEvent | AbstractResultEventHandler']]


class AbstractDispatcher(metaclass=abc.ABCMeta):
    DISPATCH: DispatchTypeDict = {}

    def __init__(self, bot: 'CameraBot') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._bot = bot
        self._dispatch = {k: v(self._bot) for k, v in self.DISPATCH.items()}

    @abc.abstractmethod
    async def dispatch(self, data: dict) -> None:
        pass
