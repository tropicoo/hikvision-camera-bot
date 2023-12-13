import abc
import asyncio
import logging
from typing import TYPE_CHECKING

from addict import Dict

from hikcamerabot.enums import DvrUploadType

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam
    from hikcamerabot.services.stream.dvr.file_wrapper import DvrFile

_UPLOAD_RETRY_WAIT = 5


class AbstractDvrUploadTask(metaclass=abc.ABCMeta):
    UPLOAD_TYPE: DvrUploadType | None = None

    def __init__(
        self, cam: 'HikvisionCam', conf: Dict, queue: asyncio.Queue['DvrFile']
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam = cam
        self._bot = cam.bot
        self._conf = conf
        self._queue = queue

    @abc.abstractmethod
    async def run(self) -> None:
        pass
