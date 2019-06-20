"""Live stream module."""

import logging
import subprocess
import time
from threading import Event
from urllib.parse import urlsplit

from camerabot.constants import CMD_YT_FFMPEG, FFMPEG_NULL_AUDIO
from camerabot.exceptions import HomeCamError
from camerabot.utils import kill_proc_tree


class LiveStream:

    """Live stream base class."""

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)


class YouTubeStream(LiveStream):

    """YouTube Live stream class."""

    def __init__(self, conf, api_conf):
        super().__init__()
        self._conf = conf
        self._api_conf = api_conf

        self._proc = None
        self._start_ts = None

        self._enabled, self._started = Event(), Event()
        if self._conf.enabled:
            self._enabled.set()

    def stop(self, disable=True):
        """Stop the stream."""
        if not self.is_started():
            msg = 'YouTube stream already stopped'
            self._log.info(msg)
            raise HomeCamError(msg)
        try:
            kill_proc_tree(self._proc.pid)
            self._started.clear()
            if disable:
                self._enabled.clear()
        except Exception:
            err_msg = 'Failed to kill/disable YouTube stream'
            self._log.exception(err_msg)
            raise HomeCamError(err_msg)

    def start(self):
        """Start the stream."""
        if self.is_started():
            msg = 'YouTube stream already started'
            self._log.info(msg)
            raise HomeCamError(msg)

        try:
            self._enabled.set()
            null_audio = FFMPEG_NULL_AUDIO if self._conf.null_audio else \
                {k: '' for k in FFMPEG_NULL_AUDIO}

            cmd = CMD_YT_FFMPEG.format(filter=null_audio['filter'],
                                       user=self._api_conf.auth.user,
                                       pw=self._api_conf.auth.password,
                                       host=urlsplit(self._api_conf.host).netloc,
                                       channel=self._conf.channel,
                                       map=null_audio['map'],
                                       bitrate=null_audio['bitrate'],
                                       url=self._conf.url,
                                       key=self._conf.key).split()

            self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT)
            self._start_ts = int(time.time())
            self._started.set()
        except Exception:
            err_msg = 'YouTube stream failed to start'
            self._log.exception(err_msg)
            raise HomeCamError(err_msg)

    def need_restart(self):
        """Check if the stream needs to be restarted."""
        return int(time.time()) > self._start_ts + self._conf.restart_period

    def restart(self):
        """Restart the stream."""
        self.stop(disable=False)
        time.sleep(self._conf.restart_pause)
        self.start()

    def is_enabled(self):
        """Check if stream is enabled."""
        return self._enabled.is_set()

    def is_started(self):
        """Check if stream is started."""
        return self._started.is_set()
