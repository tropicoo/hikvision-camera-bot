"""Video managers module."""
import logging
from collections import deque
from urllib.parse import urlsplit

from addict import Addict
from aiogram.types import Message

from hikcamerabot.constants import FFMPEG_VIDEO_GIF_CMD, VideoGifType
from hikcamerabot.services.tasks.video import RecordVideoTask
from hikcamerabot.utils.task import create_task


class VideoGifManager:
    """Video Gif Manager Class."""

    def __init__(self, cam, conf: Addict):
        """Constructor.

        :Parameters:
            - `conf`: obj, camera configuration object.
        """
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam = cam
        self._conf = conf
        self._proc_task_queue = deque()
        self._ffmpeg_cmd = self.build_ffmpeg_cmd()
        self._tmp_storage_path: str = self._conf.alert.video_gif.tmp_storage

    def start_rec(self, context: Message) -> None:
        self._start_rec(video_type=VideoGifType.REGULAR, context=context)

    def start_alert_rec(self) -> None:
        self._start_rec(video_type=VideoGifType.ALERT)

    def _start_rec(self, video_type: str, context: Message = None) -> None:
        """Start rtsp video stream recording to a temporary file."""
        rec_task = RecordVideoTask(
            ffmpeg_cmd=self._ffmpeg_cmd,
            storage_path=self._tmp_storage_path,
            conf=self._conf,
            cam=self._cam,
            video_type=video_type,
            context=context,
        )
        task = create_task(
            rec_task.run(),
            task_name=RecordVideoTask.__name__,
            logger=self._log,
            exception_message='Task %s raised an exception',
            exception_message_args=(RecordVideoTask.__name__,),
        )
        self._proc_task_queue.appendleft(task)

    def get_recorded_videos(self) -> list[tuple[str, str]]:
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
        rtsp_port: int = self._conf.rtsp_port

        gif_conf: Addict = self._conf.alert.video_gif
        rec_time: int = gif_conf.record_time
        loglevel: str = gif_conf.loglevel
        channel: int = gif_conf.channel
        rtsp_transport_type: str = gif_conf.rtsp_transport_type

        return FFMPEG_VIDEO_GIF_CMD.format(host=urlsplit(host).netloc,
                                           rtsp_port=rtsp_port,
                                           user=user,
                                           pw=password,
                                           channel=channel,
                                           rec_time=rec_time,
                                           loglevel=loglevel,
                                           rtsp_transport_type=rtsp_transport_type)
