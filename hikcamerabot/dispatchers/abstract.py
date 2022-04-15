import abc
import logging
from typing import TYPE_CHECKING

from hikcamerabot.types import DispatchTypeDict

if TYPE_CHECKING:
    from hikcamerabot.camerabot import CameraBot


class AbstractDispatcher(metaclass=abc.ABCMeta):
    DISPATCH: DispatchTypeDict = {}

    def __init__(self, bot: 'CameraBot') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._bot = bot
        self._dispatch = {k: v(self._bot) for k, v in self.DISPATCH.items()}

    @abc.abstractmethod
    async def dispatch(self, data: dict) -> None:
        pass
