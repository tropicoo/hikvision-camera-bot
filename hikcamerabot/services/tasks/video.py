import asyncio
import logging
import os
import time

from addict import Addict
from aiogram.types import Message

from hikcamerabot.config.config import get_result_queue
from hikcamerabot.constants import Event, VideoGifType
from hikcamerabot.utils.utils import format_ts, gen_random_str


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

    def __init__(self, ffmpeg_cmd: str, storage_path: str, conf: Addict,
                 cam, video_type: str, context: Message = None):
        self._log = logging.getLogger(self.__class__.__name__)
        self._conf = conf
        self._cam = cam
        self._video_type = video_type
        self._file_path = os.path.join(storage_path, self._get_filename())
        self._ffmpeg_cmd_full = f'{ffmpeg_cmd} {self._file_path}'
        self._context = context

    async def run(self) -> None:
        await self._record()
        await self._send_result()

    async def _send_result(self):
        await get_result_queue().put({
            'event': self._video_type_to_event[self._video_type],
            'video_path': self._file_path,
            'cam': self._cam,
            'message': self._context
        })

    async def _record(self) -> None:
        """Start Ffmpeg subprocess and return file path and video type."""
        self._log.debug('Recording video gif from %s: %s',
                        self._conf.description, self._ffmpeg_cmd_full)
        await self._start_ffmpeg_subprocess()

    async def _start_ffmpeg_subprocess(self) -> None:
        proc = await asyncio.create_subprocess_shell(self._ffmpeg_cmd_full)
        await proc.wait()

    def _get_filename(self) -> str:
        return self._video_filename[self._video_type].format(
            self._cam.id,
            format_ts(time.time(), time_format=self.FILENAME_TIME_FORMAT),
            gen_random_str())
