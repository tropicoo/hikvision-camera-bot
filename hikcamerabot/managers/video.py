"""Video managers module."""

import logging
import os
import subprocess
import time
from urllib.parse import urlsplit

from hikcamerabot.constants import VIDEO_GIF_FILENAME, FFMPEG_VIDEO_GIF_CMD
from hikcamerabot.utils import format_ts


class VideoGifManager:
    """Video Gif Manager Class."""

    def __init__(self, conf):
        """Constructor.

        :Parameters:
            - `conf`: obj, camera configuration object.
        """
        self._log = logging.getLogger(self.__class__.__name__)

        self._procs = {}
        self.__conf = conf
        self._cmd = self._prepare_cmd()

    def _prepare_cmd(self):
        """Prepare ffmpeg command."""
        user = self.__conf.api.auth.user
        password = self.__conf.api.auth.password
        host = self.__conf.api.host

        rec_time = self.__conf.alert.video_gif.record_time
        loglevel = self.__conf.alert.video_gif.loglevel
        channel = self.__conf.alert.video_gif.channel

        return FFMPEG_VIDEO_GIF_CMD.format(host=urlsplit(host).netloc,
                                           user=user,
                                           pw=password,
                                           channel=channel,
                                           rec_time=rec_time,
                                           loglevel=loglevel)

    def start_rec(self):
        """Start recording to temporary file."""
        if not self.__conf.alert.video_gif.enabled:
            return

        tmp_storage = self.__conf.alert.video_gif.tmp_storage

        filename = VIDEO_GIF_FILENAME.format(
            format_ts(time.time(), time_format='%Y-%b-%d--%H-%M-%S'))
        filename = os.path.join(tmp_storage, filename)

        cmd = f'{self._cmd} {filename}'
        self._log.debug('Recording video gif for %s: %s',
                        self.__conf.description, cmd)
        proc = subprocess.Popen(cmd, shell=True)
        self._procs[filename] = proc

    def get_videos(self):
        """Get recorded videos."""
        videos = []
        if self._procs:
            # deepcopy throws `_thread.lock` pickling exception
            procs_copy = self._procs.copy()
            for filename, proc in procs_copy.items():
                if proc.poll() is not None:
                    videos.append(filename)
                    self._procs.pop(filename, None)
        return videos
