from pathlib import Path
from typing import TYPE_CHECKING

from tenacity import retry, wait_fixed

from hikcamerabot.constants import DvrUploadType
from hikcamerabot.services.stream.dvr.upload.tasks.abstract import (
    AbstractDvrUploadTask,
)

if TYPE_CHECKING:
    from hikcamerabot.services.stream.dvr.file_wrapper import DvrFile

_UPLOAD_RETRY_WAIT = 5


class TelegramDvrUploadTask(AbstractDvrUploadTask):
    UPLOAD_TYPE = DvrUploadType.TELEGRAM

    async def run(self) -> None:
        self._log.debug('Running %s task', self.__class__.__name__)
        await self._process_queue()

    async def _process_queue(self) -> None:
        while True:
            file_ = await self._queue.get()
            await self._upload_video(file_)
            file_.decrement_lock_count()

    @retry(wait=wait_fixed(_UPLOAD_RETRY_WAIT))
    async def _upload_video(self, file_: 'DvrFile') -> None:
        try:
            await self.__upload(file_)
        except Exception:
            self._log.exception('Failed to upload video %s. Retrying', file_.full_path)
            raise

    def _validate_file(self, file_: 'DvrFile') -> bool:
        if not file_.exists:
            self._log.error('File %s does not exist, cannot upload', file_.full_path)
            return False
        if Path(file_.full_path).stat().st_size == 0:
            self._log.error('File %s empty, cannot upload', file_.full_path)
            return False
        return True

    async def __upload(self, file_: 'DvrFile') -> None:
        if not self._validate_file(file_):
            return

        self._log.debug('Uploading DVR video %s', file_.full_path)
        caption = f'Video from {self._cam.description} {self._cam.hashtag}'
        await self._bot.send_chat_action(self._conf.group_id, action='upload_video')
        await self._bot.send_video(
            self._conf.group_id,
            caption=caption,
            video=file_.full_path,
            file_name=file_.name,
            duration=file_.duration or 0,
            height=file_.height or 0,
            width=file_.width or 0,
            thumb=file_.thumbnail,
            supports_streaming=True,
        )
        self._log.debug('Finished uploading DVR video %s', file_.full_path)
