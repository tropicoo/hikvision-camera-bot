import abc
import logging


class AbstractServiceTask(abc.ABC):
    type = None
    _event_manager_cls = None

    def __init__(self, service):
        self._log = logging.getLogger(self.__class__.__name__)
        self.service = service
        self._cam = service.cam
        self._bot = self._cam.bot
        self._cls_name = self.__class__.__name__

    @abc.abstractmethod
    async def run(self) -> None:
        """Main async task entry point."""
        pass
