import asyncio
import logging
from typing import TYPE_CHECKING

from addict import Dict

from hikcamerabot.constants import (
    DvrUploadType,
)
from hikcamerabot.services.stream.dvr.file_wrapper import DvrFile
from hikcamerabot.services.stream.dvr.tasks.file_delete import DvrFileDeleteTask
from hikcamerabot.services.stream.dvr.tasks.file_monitoring import DvrFileMonitoringTask
from hikcamerabot.services.stream.dvr.upload.tasks.telegram import TelegramDvrUploadTask
from hikcamerabot.utils.task import create_task

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam


class DvrUploadEngine:
    _UPLOAD_TASKS = {
        DvrUploadType.TELEGRAM: TelegramDvrUploadTask,
    }

    _FILE_DELETE_TASK_CLS = DvrFileDeleteTask

    def __init__(self, conf: Dict, cam: 'HikvisionCam') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._conf = conf
        self._cam = cam
        self._storage_queues = self._create_storage_queues()
        self._delete_after_upload: bool = self._conf.upload.delete_after_upload
        self._delete_candidates_queue: asyncio.Queue[DvrFile] = asyncio.Queue()
        self._upload_cache: set[str] = set()

    def _create_storage_queues(self) -> dict[str, asyncio.Queue]:
        storage_queues = {}
        for storage, settings in self._conf.upload.storage.items():
            if settings.enabled:
                storage_queues[storage] = asyncio.Queue()

        self._log.debug('Created storage queues: %s', storage_queues)
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
        self._log.debug('Upload Engine for %s has started', self._cam.description)

    async def _start_tasks(self):
        await asyncio.gather(
            self._start_storage_tasks(),
            self._start_file_monitoring_task_(),
            self._start_file_deletion_task_(),
        )

    async def _start_storage_tasks(self) -> None:
        for storage, queue in self._storage_queues.items():
            self._log.debug(
                'Starting %s upload task for %s storage', self._cam.description, storage
            )
            task = self._UPLOAD_TASKS[DvrUploadType(storage)]
            create_task(
                task(
                    cam=self._cam, conf=self._conf.upload.storage[storage], queue=queue
                ).run(),
                task_name=task.__name__,
                logger=self._log,
                exception_message='Task %s raised an exception',
                exception_message_args=(task.__name__,),
            )

    async def _start_file_monitoring_task_(self) -> None:
        self._log.debug(
            'Starting DVR file monitoring task for %s', self._cam.description
        )
        create_task(
            DvrFileMonitoringTask(engine=self, conf=self._cam.conf).run(),
            task_name=DvrFileMonitoringTask.__name__,
            logger=self._log,
            exception_message='Task %s raised an exception',
            exception_message_args=(DvrFileMonitoringTask.__name__,),
        )

    async def _start_file_deletion_task_(self) -> None:
        if self._conf.upload.delete_after_upload:
            self._log.debug(
                'Starting DVR file deletion task for %s', self._cam.description
            )
            create_task(
                self._FILE_DELETE_TASK_CLS(
                    queue=self._delete_candidates_queue,
                ).run(),
                task_name=self._FILE_DELETE_TASK_CLS.__name__,
                logger=self._log,
                exception_message='Task %s raised an exception',
                exception_message_args=(self._FILE_DELETE_TASK_CLS.__name__,),
            )
