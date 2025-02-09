import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from hikcamerabot.camerabot import CameraBot


class AbstractDispatcher(ABC):
    DISPATCH: ClassVar[dict] = {}

    def __init__(self, bot: 'CameraBot') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._bot = bot
        self._dispatch = {k: v(self._bot) for k, v in self.DISPATCH.items()}

    @abstractmethod
    async def dispatch(self, data: dict) -> None:
        pass
