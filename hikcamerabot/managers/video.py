"""Video managers module."""
import asyncio
import logging
import os
import time
from collections import deque
from urllib.parse import urlsplit

from addict import Addict

from hikcamerabot.constants import FFMPEG_VIDEO_GIF_CMD
from hikcamerabot.utils.task import create_task
from hikcamerabot.utils.utils import format_ts, gen_uuid


class VideoRecTask:
    VIDEO_GIF_FILENAME = '{0}-alert-{1}-{2}.mp4'
    FILENAME_TIME_FORMAT = '%Y-%b-%d--%H-%M-%S'

    def __init__(self, ffmpeg_cmd: str, storage_path: str, conf: Addict,
                 cam_id: str):
        self._log = logging.getLogger(self.__class__.__name__)
        self._conf = conf
        self._cam_id = cam_id
        self._file_path = os.path.join(storage_path, self._get_filename())
        self._ffmpeg_cmd_full = f'{ffmpeg_cmd} {self._file_path}'

    async def run(self) -> str:
        return await self._record()

    async def _record(self) -> str:
        self._log.debug('Recording video gif from %s: %s',
                        self._conf.description, self._ffmpeg_cmd_full)
        await self._start_ffmpeg_subprocess()
        return self._file_path

    async def _start_ffmpeg_subprocess(self) -> None:
        proc = await asyncio.create_subprocess_shell(self._ffmpeg_cmd_full)
        await proc.wait()

    def _get_filename(self) -> str:
        return self.VIDEO_GIF_FILENAME.format(
            self._cam_id,
            format_ts(time.time(), time_format=self.FILENAME_TIME_FORMAT),
            gen_uuid())


class VideoGifManager:
    """Video Gif Manager Class."""

    def __init__(self, cam_id: str, conf: Addict):
        """Constructor.

        :Parameters:
            - `conf`: obj, camera configuration object.
        """
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam_id = cam_id
        self._conf = conf
        self._proc_task_queue = deque()

        self._ffmpeg_cmd = self.build_ffmpeg_cmd()
        self._tmp_storage_path: str = self._conf.alert.video_gif.tmp_storage

    def start_rec(self) -> None:
        """Start rtsp video stream recording to a temporary file."""
        if not self._conf.alert.video_gif.enabled:
            return

        rec_task = VideoRecTask(
            ffmpeg_cmd=self._ffmpeg_cmd,
            storage_path=self._tmp_storage_path,
            conf=self._conf,
            cam_id=self._cam_id,
        )
        task = create_task(
            rec_task.run(),
            task_name=VideoRecTask.__name__,
            logger=self._log,
            exception_message='Task %s raised an exception',
            exception_message_args=(VideoRecTask.__name__,),
        )
        self._proc_task_queue.appendleft(task)

    def get_recorded_videos(self) -> list[str]:
        """Get recorded video file paths."""
        videos = []
        for _ in range(len(self._proc_task_queue)):
            task = self._proc_task_queue.pop()
            if task.done():
                videos.append(task.result())
            else:
                self._proc_task_queue.appendleft(task)
        return videos

    def build_ffmpeg_cmd(self) -> str:
        user: str = self._conf.api.auth.user
        password: str = self._conf.api.auth.password
        host: str = self._conf.api.host

        gif_conf: Addict = self._conf.alert.video_gif
        rec_time: int = gif_conf.record_time
        loglevel: str = gif_conf.loglevel
        channel: int = gif_conf.channel
        rtsp_type: str = gif_conf.get('rtsp_transport_type', 'tcp')

        return FFMPEG_VIDEO_GIF_CMD.format(host=urlsplit(host).netloc,
                                           user=user,
                                           pw=password,
                                           channel=channel,
                                           rec_time=rec_time,
                                           loglevel=loglevel,
                                           rtsp_transport_type=rtsp_type)
