import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Final

from hikcamerabot.config.schemas.main_config import BaseDVRStorageUploadConfSchema
from hikcamerabot.enums import DvrUploadType

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam
    from hikcamerabot.services.stream.dvr.file_wrapper import DvrFile

_UPLOAD_RETRY_WAIT: Final[int] = 5


class AbstractDvrUploadTask(ABC):
    UPLOAD_TYPE: DvrUploadType | None = None

    def __init__(
        self,
        cam: 'HikvisionCam',
        conf: BaseDVRStorageUploadConfSchema,
        queue: asyncio.Queue['DvrFile'],
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam = cam
        self._bot = cam.bot
        self._conf = conf
        self._queue = queue

    @abstractmethod
    async def run(self) -> None:
        pass
