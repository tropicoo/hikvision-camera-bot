import asyncio
import logging
from typing import TYPE_CHECKING, ClassVar

from hikcamerabot.config.schemas.main_config import (
    DvrLivestreamConfSchema,
)
from hikcamerabot.enums import DvrUploadType
from hikcamerabot.services.stream.dvr.file_wrapper import DvrFile
from hikcamerabot.services.stream.dvr.tasks.file_delete import DvrFileDeleteTask
from hikcamerabot.services.stream.dvr.tasks.file_monitoring import DvrFileMonitoringTask
from hikcamerabot.services.stream.dvr.upload.tasks.abstract import AbstractDvrUploadTask
from hikcamerabot.services.stream.dvr.upload.tasks.telegram import TelegramDvrUploadTask
from hikcamerabot.utils.task import create_task

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam


class DvrUploadEngine:
    _UPLOAD_TASKS: ClassVar[dict[DvrUploadType, AbstractDvrUploadTask]] = {
        DvrUploadType.TELEGRAM: TelegramDvrUploadTask,
    }

    _FILE_DELETE_TASK_CLS = DvrFileDeleteTask

    def __init__(self, conf: DvrLivestreamConfSchema, cam: 'HikvisionCam') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._conf = conf
        self._cam = cam
        self._storage_queues = self._create_storage_queues()
        self._delete_after_upload = self._conf.upload.delete_after_upload
        self._delete_candidates_queue: asyncio.Queue[DvrFile] = asyncio.Queue()
        self._upload_cache: set[str] = set()

    def _create_storage_queues(self) -> dict[str, asyncio.Queue]:
        storage_queues: dict[str, asyncio.Queue] = {}

        for storage_name, settings in self._conf.upload.storage.get_storage_items():
            if settings.enabled:
                storage_queues[storage_name] = asyncio.Queue()

        self._log.debug('[%s] Created storage queues: %s', self._cam.id, storage_queues)
        return storage_queues

    async def upload_files(self, files: list[str]) -> None:
        files = [f for f in files if f not in self._upload_cache]
        if not files:
            return

        for file_ in await self._wrap_as_dvr_files(files):
            if self._delete_after_upload:
                await self._delete_candidates_queue.put(file_)
            for queue in self._storage_queues.values():
                await queue.put(file_)
            self._upload_cache.add(file_.name)

    async def _wrap_as_dvr_files(self, files: list[str]) -> list[DvrFile]:
        lock_count = len(self._storage_queues)
        files = [DvrFile(f, lock_count, self._cam) for f in files]
        await asyncio.gather(*[f.make_context() for f in files])
        return files

    async def start(self) -> None:
        await self._start_tasks()
        self._log.debug(
            '[%s] Upload Engine for "%s" has started',
            self._cam.id,
            self._cam.description,
        )

    async def _start_tasks(self) -> None:
        await asyncio.gather(
            self._start_storage_tasks(),
            self._start_file_monitoring_task(),
            self._start_file_deletion_task(),
        )

    async def _start_storage_tasks(self) -> None:
        for storage, queue in self._storage_queues.items():
            self._log.debug(
                '[%s] Starting upload task for "%s" storage', self._cam.id, storage
            )
            task = self._UPLOAD_TASKS[DvrUploadType(storage)]
            create_task(
                task(
                    cam=self._cam,
                    conf=self._conf.upload.storage.get_storage_conf_by_type(
                        type_=storage
                    ),
                    queue=queue,
                ).run(),
                task_name=task.__name__,
                logger=self._log,
                exception_message='Task "%s" raised an exception',
                exception_message_args=(task.__name__,),
            )

    async def _start_file_monitoring_task(self) -> None:
        self._log.debug(
            '[%s] Starting DVR file monitoring task for "%s"',
            self._cam.id,
            self._cam.description,
        )
        create_task(
            DvrFileMonitoringTask(
                engine=self, conf=self._cam.conf, cam_id=self._cam.id
            ).run(),
            task_name=DvrFileMonitoringTask.__name__,
            logger=self._log,
            exception_message='Task "%s" raised an exception',
            exception_message_args=(DvrFileMonitoringTask.__name__,),
        )

    async def _start_file_deletion_task(self) -> None:
        if self._conf.upload.delete_after_upload:
            self._log.debug(
                '[%s] Starting DVR file deletion task for "%s"',
                self._cam.id,
                self._cam.description,
            )
            create_task(
                self._FILE_DELETE_TASK_CLS(
                    queue=self._delete_candidates_queue,
                ).run(),
                task_name=self._FILE_DELETE_TASK_CLS.__name__,
                logger=self._log,
                exception_message='Task "%s" raised an exception',
                exception_message_args=(self._FILE_DELETE_TASK_CLS.__name__,),
            )
