"""Live stream module."""

import subprocess
import time
from threading import Event
from urllib.parse import urlsplit

from psutil import NoSuchProcess

from camerabot.config import get_livestream_tpl_config
from camerabot.constants import (LIVESTREAM_YT_CMD_MAP, LIVESTREAM_DIRECT,
                                 LIVESTREAM_TRANSCODE, CMD_YT_FFMPEG_CMD,
                                 FFMPEG_NULL_AUDIO, FFMPEG_SCALE_FILTER)
from camerabot.exceptions import HomeCamError
from camerabot.service import BaseService
from camerabot.utils import kill_proc_tree


class LiveStreamService(BaseService):
    """Live Stream Service Base class."""
    pass


class YouTubeStreamService(LiveStreamService):
    """YouTube Live Stream Service class."""

    def __init__(self, conf, hik_user, hik_password, hik_host):
        super().__init__()

        self._cmd_gen_dispatcher = {LIVESTREAM_DIRECT: self._generate_direct_cmd,
                                    LIVESTREAM_TRANSCODE: self._generate_transcode_cmd}

        self._conf = conf
        self._conf_tpl = get_livestream_tpl_config()

        self._hik_user = hik_user
        self._hik_password = hik_password
        self._hik_host = hik_host

        self._proc = None
        self._start_ts = None
        self._stream_conf = None
        self._cmd = None
        self._generate_cmd()

        self._started = Event()

    def start(self, skip_check=False):
        """Start the stream."""
        if not skip_check and self.is_started():
            msg = 'YouTube stream already started'
            self._log.info(msg)
            raise HomeCamError(msg)
        try:
            self._log.debug('YouTube ffmpeg command: {0}'.format(
                ' '.join(self._cmd)))
            self._proc = subprocess.Popen(self._cmd,
                                          stderr=subprocess.STDOUT,
                                          stdout=subprocess.PIPE,
                                          universal_newlines=True)
            self._start_ts = int(time.time())
            self._started.set()
        except Exception:
            err_msg = 'YouTube stream failed to start'
            self._log.exception(err_msg)
            raise HomeCamError(err_msg)

    def get_stdout(self):
        return self._proc.stdout.readline().rstrip()

    def stop(self, disable=True):
        """Stop the stream."""
        def clear_status():
            if disable:
                self._started.clear()

        if not self.is_started():
            msg = 'YouTube stream already stopped'
            self._log.info(msg)
            raise HomeCamError(msg)
        try:
            kill_proc_tree(self._proc.pid)
            clear_status()
        except NoSuchProcess as err:
            self._log.warning('PID {0} is not running: {1}'.format(
                self._proc.pid, str(err)))
            clear_status()
        except Exception:
            err_msg = 'Failed to kill/disable YouTube stream'
            self._log.exception(err_msg)
            raise HomeCamError(err_msg)

    def need_restart(self):
        """Check if the stream needs to be restarted."""
        return int(time.time()) > \
               self._start_ts + self._stream_conf.restart_period

    def restart(self):
        """Restart the stream."""
        if self.is_started():
            self.stop(disable=False)
        self._log.debug('Sleeping for {0}s'.format(
            self._stream_conf.restart_pause))
        time.sleep(self._stream_conf.restart_pause)
        self.start(skip_check=True)

    def is_enabled_in_conf(self):
        """Check if stream is enabled in configuration."""
        return self._conf.enabled

    def is_started(self):
        """Check if stream is started."""
        return self._started.is_set()

    def is_alive(self):
        """Check whether the stream (ffmpeg process) is still running."""
        alive_state = self._proc.poll() is None
        if not alive_state:
            self._started.clear()
        return alive_state

    def _generate_cmd(self):
        try:
            stream_type, tpl_name = self._conf.template.split('.')
        except ValueError:
            err_msg = 'Failed to load YouTube Livestream ' \
                      'template "{0}"'.format(self._conf.template)
            self._log.error(err_msg)
            raise HomeCamError(err_msg)

        inner_cmd_tpl = LIVESTREAM_YT_CMD_MAP[stream_type]
        cmd_tpl = CMD_YT_FFMPEG_CMD.format(inner_cmd=inner_cmd_tpl)
        self._stream_conf = self._conf_tpl.youtube[stream_type][tpl_name]

        null_audio = FFMPEG_NULL_AUDIO if self._stream_conf.null_audio else \
            {k: '' for k in FFMPEG_NULL_AUDIO}

        self._cmd_gen_dispatcher[stream_type](cmd_tpl, null_audio)

    def _generate_direct_cmd(self, cmd_tpl, null_audio):
        self._cmd = cmd_tpl.format(bitrate=null_audio['bitrate'],
                                   channel=self._stream_conf.channel,
                                   filter=null_audio['filter'],
                                   host=urlsplit(self._hik_host).netloc,
                                   key=self._stream_conf.key,
                                   loglevel=self._stream_conf.loglevel,
                                   map=null_audio['map'],
                                   pw=self._hik_password,
                                   url=self._stream_conf.url,
                                   user=self._hik_user).split()

    def _generate_transcode_cmd(self, cmd_tpl, null_audio):
        scale = ''
        if self._stream_conf.encode.scale.enabled:
            scale = FFMPEG_SCALE_FILTER.format(
                width=self._stream_conf.encode.scale.width,
                height=self._stream_conf.encode.scale.height,
                format=self._stream_conf.encode.scale.format)

        self._cmd = cmd_tpl.format(bitrate=null_audio['bitrate'],
                                   bufsize=self._stream_conf.encode.bufsize,
                                   channel=self._stream_conf.channel,
                                   filter=null_audio['filter'],
                                   framerate=self._stream_conf.encode.framerate,
                                   group=self._stream_conf.encode.framerate*2,
                                   host=urlsplit(self._hik_host).netloc,
                                   key=self._stream_conf.key,
                                   loglevel=self._stream_conf.loglevel,
                                   map=null_audio['map'],
                                   maxrate=self._stream_conf.encode.maxrate,
                                   pix_fmt=self._stream_conf.encode.pix_fmt,
                                   preset=self._stream_conf.encode.preset,
                                   pw=self._hik_password,
                                   scale=scale,
                                   tune=self._stream_conf.encode.tune,
                                   url=self._stream_conf.url,
                                   user=self._hik_user).split()


class TwitchStreamService(LiveStreamService):
    """Twitch Live stream class."""
    def __init__(self):
        super().__init__()

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def is_started(self):
        raise NotImplementedError

    def is_enabled_in_conf(self):
        raise NotImplementedError
