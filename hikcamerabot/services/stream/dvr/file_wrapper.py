import abc
import asyncio
import json
import logging
import os
import signal
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from addict import Dict

from hikcamerabot.config.config import get_livestream_tpl_config
from hikcamerabot.utils.task import wrap

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam


class DvrFile:
    """Recorded DVR File Wrapper Class."""

    def __init__(self, filename: str, lock_count: int,
                 cam: 'HikvisionCam') -> None:
        if lock_count <= 0:
            raise RuntimeError('Lock count cannot be lower or equal 0')

        self._log = logging.getLogger(self.__class__.__name__)
        self._filename = filename
        self._lock_count = lock_count
        self._cam = cam

        tpl_name_ls: str = self._cam.conf.livestream.dvr.livestream_template
        self._storage_path: str = self._cam.conf.livestream.dvr.local_storage_path

        self._full_path = os.path.join(self._storage_path, self._filename)

        self._thumbnail = f'{self._storage_path}/{self.name}.jpg'
        self._duration: Optional[int] = None
        self._width: Optional[int] = None
        self._height: Optional[int] = None
        self._probe_ctx: Optional[dict] = None

    def __str__(self) -> str:
        return self._filename

    def __repr__(self) -> str:
        return f'DVR File {self.full_path}'

    def __hash__(self) -> int:
        return hash(self._filename)

    async def _get_probe_ctx(self) -> None:
        self._probe_ctx = await GetFfprobeContextTask(file=self).run()
        if not self._probe_ctx:
            return
        video_streams = [stream for stream in self._probe_ctx['streams'] if
                         stream['codec_type'] == 'video']
        self._duration = int(float(self._probe_ctx['format']['duration']))
        self._height = video_streams[0]['height']
        self._width = video_streams[0]['width']

    async def _make_thumbnail_frame(self) -> None:
        if not await MakeThumbnailTask(file=self).run():
            self._log.error('Error during making thumbnail context of %s',
                            self.full_path)

    async def make_context(self) -> None:
        await asyncio.gather(self._get_probe_ctx(), self._make_thumbnail_frame())

    def decrement_lock_count(self) -> None:
        if self._lock_count > 0:
            self._lock_count -= 1

    @property
    def exists(self) -> bool:
        return Path(self.full_path).is_file()

    @property
    def name(self) -> str:
        return self._filename

    @property
    def thumbnail(self) -> Optional[str]:
        if Path(self._thumbnail).is_file():
            return self._thumbnail
        return None

    @property
    def height(self) -> Optional[int]:
        return self._height

    @property
    def width(self) -> Optional[int]:
        return self._width

    @property
    def duration(self) -> Optional[int]:
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


class AbstractFfBinaryTask(metaclass=abc.ABCMeta):
    _CMD: Optional[str] = None
    _CMD_TIMEOUT = 10

    def __init__(self, file: DvrFile) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._file = file
        self._killpg = wrap(os.killpg)

    async def _run_proc(self, cmd: str) -> Optional[asyncio.subprocess.Process]:
        proc = await asyncio.create_subprocess_shell(
            cmd=cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=self._CMD_TIMEOUT)
            return proc
        except asyncio.TimeoutError:
            self._log.error('Failed to execute %s: process ran longer than '
                            'expected and was killed', cmd)
            await self._killpg(os.getpgid(proc.pid), signal.SIGINT)
            return None

    @staticmethod
    async def _get_stdout_stderr(
            proc: asyncio.subprocess.Process) -> tuple[str, str]:
        stdout, stderr = await proc.stdout.read(), await proc.stderr.read()
        return stdout.decode().strip(), stderr.decode().strip()

    @abc.abstractmethod
    async def run(self) -> None:
        """Main entry point."""
        pass


class GetFfprobeContextTask(AbstractFfBinaryTask):
    _CMD = 'ffprobe -loglevel error -show_format -show_streams -of json {filepath}'

    async def run(self) -> Optional[dict]:
        return await self._get_context()

    async def _get_context(self) -> Optional[dict]:
        cmd = self._CMD.format(filepath=self._file.full_path)
        proc = await self._run_proc(cmd)
        if not proc:
            return None

        stdout, stderr = await self._get_stdout_stderr(proc)
        self._log.debug('Process %s returncode: %d, stderr: %s',
                        cmd, proc.returncode, stderr)
        if proc.returncode:
            self._log.error('Failed to make video context. Is file broken? %s?',
                            self._file.full_path)
            return None
        try:
            return json.loads(stdout)
        except Exception:
            self._log.exception('Failed to load ffprobe output [type %s]: %s',
                                type(stdout), stdout)
            return None


class MakeThumbnailTask(AbstractFfBinaryTask):
    _CMD = 'ffmpeg -y -loglevel error -i {filepath} -vframes 1 {thumbpath}'

    async def run(self) -> bool:
        return await self._make_thumbnail()

    async def _make_thumbnail(self) -> bool:
        cmd = self._CMD.format(filepath=self._file.full_path,
                               thumbpath=self._file._thumbnail)
        proc = await self._run_proc(cmd)
        if not proc:
            return False

        stdout, stderr = await self._get_stdout_stderr(proc)
        self._log.debug('Process %s returncode: %d, stdout: %s, stderr: %s',
                        cmd, proc.returncode, stdout, stderr)
        if proc.returncode:
            self._log.error('Failed to make thumbnail for %s',
                            self._file.full_path)
            return False
        return True
