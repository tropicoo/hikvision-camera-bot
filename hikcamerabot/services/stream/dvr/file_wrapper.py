import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from hikcamerabot.common.video.tasks.ffprobe_context import GetFfprobeContextTask
from hikcamerabot.common.video.tasks.thumbnail import MakeThumbnailTask

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam


class DvrFile:
    """Recorded DVR File Wrapper Class."""

    def __init__(self, filename: str, lock_count: int, cam: 'HikvisionCam') -> None:
        if lock_count <= 0:
            raise RuntimeError('Lock count cannot be lower or equal 0')

        self._log = logging.getLogger(self.__class__.__name__)
        self._filename = filename
        self._lock_count = lock_count
        self._cam = cam

        self._storage_path: str = self._cam.conf.livestream.dvr.local_storage_path
        self._full_path = os.path.join(self._storage_path, self._filename)
        self._thumbnail = os.path.join(self._storage_path, f'{self.name}-thumb.jpg')

        self._duration: int | None = None
        self._width: int | None = None
        self._height: int | None = None
        self._probe_ctx: dict | None = None

        self._is_broken = False

    def __str__(self) -> str:
        return self._filename

    def __repr__(self) -> str:
        return f'DVR File {self.full_path}'

    def __hash__(self) -> int:
        return hash(self._filename)

    async def _get_probe_ctx(self) -> None:
        self._probe_ctx = await GetFfprobeContextTask(self.full_path).run()
        if not self._probe_ctx:
            self._is_broken = True
            return
        video_streams = [
            stream
            for stream in self._probe_ctx['streams']
            if stream['codec_type'] == 'video'
        ]
        self._duration = int(float(self._probe_ctx['format']['duration']))
        self._height = video_streams[0]['height']
        self._width = video_streams[0]['width']

    async def _make_thumbnail_frame(self) -> None:
        if not await MakeThumbnailTask(self._thumbnail, self.full_path).run():
            self._log.error('Error during making thumbnail for %s', self.full_path)

    async def make_context(self) -> None:
        await asyncio.gather(self._get_probe_ctx(), self._make_thumbnail_frame())

    def decrement_lock_count(self) -> None:
        if self._lock_count > 0:
            self._lock_count -= 1

    @property
    def is_broken(self) -> bool:
        return self._is_broken

    @property
    def is_empty(self) -> bool:
        return Path(self.full_path).stat().st_size == 0

    @property
    def exists(self) -> bool:
        return Path(self.full_path).is_file()

    @property
    def name(self) -> str:
        return self._filename

    @property
    def thumbnail(self) -> str | None:
        if Path(self._thumbnail).is_file():
            return self._thumbnail
        return None

    @property
    def height(self) -> int | None:
        return self._height

    @property
    def width(self) -> int | None:
        return self._width

    @property
    def duration(self) -> int | None:
        return self._duration

    @property
    def full_path(self) -> str:
        return self._full_path

    @property
    def is_locked(self) -> bool:
        return self._lock_count != 0

    @property
    def lock_count(self) -> int:
        return self._lock_count
