"""Video managers module."""

import logging
from collections import deque
from typing import TYPE_CHECKING

from pyrogram.types import Message

from hikcamerabot.common.video.tasks.videogif import RecordVideoGifTask
from hikcamerabot.enums import VideoGifType
from hikcamerabot.utils.task import create_task

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam


class VideoGifRecorder:
    """Video Gif Manager Class."""

    def __init__(self, cam: 'HikvisionCam') -> None:
        """Constructor."""
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam = cam
        self._proc_task_queue = deque()

    def start_rec(
        self, video_type: VideoGifType, rewind: bool = False, message: Message = None
    ) -> None:
        """Start recording video-gif."""
        self._start_rec(video_type=video_type, rewind=rewind, message=message)

    def _start_rec(
        self, video_type: VideoGifType, rewind: bool, message: Message
    ) -> None:
        """Start rtsp video stream recording to a temporary file."""
        rec_task = RecordVideoGifTask(
            rewind=rewind,
            cam=self._cam,
            video_type=video_type,
            message=message,
        )
        task = create_task(
            rec_task.run(),
            task_name=RecordVideoGifTask.__name__,
            logger=self._log,
            exception_message='Task "%s" raised an exception',
            exception_message_args=(RecordVideoGifTask.__name__,),
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
