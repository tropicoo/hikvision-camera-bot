import asyncio
import logging
import os
import time
from typing import TYPE_CHECKING

from addict import Dict
from aiogram.types import Message

from hikcamerabot.config.config import get_result_queue
from hikcamerabot.constants import Event, VideoGifType
from hikcamerabot.utils.utils import format_ts, gen_random_str

if TYPE_CHECKING:
    from hikcamerabot.camerabot import CameraBot
    from hikcamerabot.camera import HikvisionCam


class RecordVideoTask:
    _video_filename = {
        VideoGifType.ALERT: '{0}-alert-{1}-{2}.mp4',
        VideoGifType.REGULAR: '{0}-{1}-{2}.mp4',
    }

    _video_type_to_event = {
        VideoGifType.ALERT: Event.ALERT_VIDEO,
        VideoGifType.REGULAR: Event.RECORD_VIDEOGIF,
    }

    FILENAME_TIME_FORMAT = '%Y-%b-%d--%H-%M-%S'

    def __init__(self, ffmpeg_cmd: str, storage_path: str, conf: Dict,
                 cam: 'HikvisionCam', video_type: str, context: Message = None):
        self._log = logging.getLogger(self.__class__.__name__)
        self._conf = conf
        self._cam = cam
        self._bot: 'CameraBot' = cam.bot
        self._video_type = video_type
        self._file_path = os.path.join(storage_path, self._get_filename())
        self._ffmpeg_cmd_full = f'{ffmpeg_cmd} {self._file_path}'
        self._msg = context
        self._event = self._video_type_to_event[self._video_type]

    async def run(self) -> None:
        if await self._record():
            await self._send_result()

    async def _record(self) -> bool:
        """Start Ffmpeg subprocess and return file path and video type."""
        self._log.debug('Recording video gif from %s: %s',
                        self._conf.description, self._ffmpeg_cmd_full)
        await self._start_ffmpeg_subprocess()
        validated = await self._validate_file()
        if not validated:
            err_msg = f'Failed to record {self._file_path}'
            self._log.error(err_msg)
            await self._bot.send_message(
                self._msg.chat.id,
                text=f'{err_msg}.\nEvent type: {self._event}\nCheck logs.',
                reply_to_message_id=self._msg.message_id if self._msg else None,
            )
        return validated

    async def _start_ffmpeg_subprocess(self) -> None:
        proc = await asyncio.create_subprocess_shell(self._ffmpeg_cmd_full)
        await proc.wait()

    async def _validate_file(self) -> bool:
        """Validate recorded file existence and size."""
        try:
            is_empty = os.path.getsize(self._file_path) == 0
        except FileNotFoundError:
            self._log.error('Failed to validate %s: File does not exist',
                            self._file_path)
            return False
        except Exception:
            self._log.exception('Failed to validate %s', self._file_path)
            return False

        if is_empty:
            self._log.error('Failed to validate %s: File %s is empty',
                            self._file_path)
        return not bool(is_empty)

    async def _send_result(self):
        await get_result_queue().put({
            'event': self._event,
            'video_path': self._file_path,
            'cam': self._cam,
            'message': self._msg
        })

    def _get_filename(self) -> str:
        return self._video_filename[self._video_type].format(
            self._cam.id,
            format_ts(time.time(), time_format=self.FILENAME_TIME_FORMAT),
            gen_random_str())
