"""Video managers module."""

import logging
from collections import deque
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from addict import Dict
from pyrogram.types import Message

from hikcamerabot.constants import (
    FFMPEG_CAM_VIDEO_SOURCE, FFMPEG_CMD_VIDEO_GIF,
    FFMPEG_SRS_VIDEO_SOURCE, RTSP_TRANSPORT_TPL, SRS_LIVESTREAM_NAME_TPL,
    VideoGifType,
)
from hikcamerabot.services.tasks.video import RecordVideoTask
from hikcamerabot.utils.task import create_task

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam


class VideoGifManager:
    """Video Gif Manager Class."""

    def __init__(self, cam: 'HikvisionCam') -> None:
        """Constructor."""
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam = cam
        self._proc_task_queue = deque()
        self._ffmpeg_cmd = self.build_ffmpeg_cmd()
        self._tmp_storage_path: str = self._cam.conf.alert.video_gif.tmp_storage

    def start_rec(self, video_type: VideoGifType,
                  context: Message = None) -> None:
        """Start recording video-gif."""
        self._start_rec(video_type=video_type, context=context)

    def _start_rec(self, video_type: VideoGifType,
                   context: Message = None) -> None:
        """Start rtsp video stream recording to a temporary file."""
        rec_task = RecordVideoTask(
            ffmpeg_cmd=self._ffmpeg_cmd,
            storage_path=self._tmp_storage_path,
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
        gif_conf: Dict = self._cam.conf.alert.video_gif
        rec_time: int = gif_conf.record_time
        loglevel: str = gif_conf.loglevel
        channel: int = gif_conf.channel
        is_srs_enabled = self._cam.conf.livestream.srs.enabled

        if is_srs_enabled:
            video_source = FFMPEG_SRS_VIDEO_SOURCE.format(
                livestream_name=SRS_LIVESTREAM_NAME_TPL.format(
                    channel=channel,
                    cam_id=self._cam.id,
                )
            )
        else:
            video_source = FFMPEG_CAM_VIDEO_SOURCE.format(
                user=self._cam.conf.api.auth.user,
                pw=self._cam.conf.api.auth.password,
                host=urlsplit(self._cam.conf.api.host).netloc,
                rtsp_port=self._cam.conf.rtsp_port,
                channel=channel,
            )
        return FFMPEG_CMD_VIDEO_GIF.format(
            rtsp_transport=RTSP_TRANSPORT_TPL.format(
                rtsp_transport_type=gif_conf.rtsp_transport_type
            ) if not is_srs_enabled else '',
            video_source=video_source,
            rec_time=rec_time,
            loglevel=loglevel,
        )
