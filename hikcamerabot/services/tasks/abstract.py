import abc
import logging
from typing import Optional

from hikcamerabot.config.config import get_result_queue
from hikcamerabot.types import ServiceTypeType


class AbstractServiceTask(abc.ABC):
    type: Optional[str] = None
    _event_manager_cls = None

    def __init__(self, service: ServiceTypeType, run_forever: bool = False) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._run_forever = run_forever
        self.service = service
        self._cam = service.cam
        self._bot = self._cam.bot
        self._cls_name = self.__class__.__name__
        self._result_queue = get_result_queue()

    @abc.abstractmethod
    async def run(self) -> None:
        """Main async task entry point."""
        pass
