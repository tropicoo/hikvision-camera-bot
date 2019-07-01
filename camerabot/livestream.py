"""livestream module."""

import abc
import subprocess
import time
from threading import Event
from urllib.parse import urlsplit

from psutil import NoSuchProcess

from camerabot.config import get_livestream_tpl_config
from camerabot.constants import (LIVESTREAM_DIRECT, StreamMap,
                                 LIVESTREAM_TRANSCODE,
                                 FFMPEG_CMD, FFMPEG_CMD_NULL_AUDIO,
                                 FFMPEG_CMD_SCALE_FILTER,
                                 FFMPEG_CMD_TRANSCODE_GENERAL,
                                 FFMPEG_TRANSCODE_MAP)
from camerabot.exceptions import HomeCamError
from camerabot.service import BaseService
from camerabot.utils import kill_proc_tree


class FFMPEGBaseStreamService(BaseService, metaclass=abc.ABCMeta):
    """livestream Service Base class."""

    # Not needed since abc.abstractethods are defined
    # def __new__(cls, *args, **kwargs):
    #     if cls is FFMPEGBaseStreamService:
    #         raise TypeError('{0} class may not be instantiated'.format(
    #             cls.__name__))
    #     return super().__new__(cls)

    def __init__(self, stream_name, conf, hik_user, hik_password, hik_host):
        super().__init__()

        self._cmd_gen_dispatcher = {
            LIVESTREAM_DIRECT: self._generate_direct_cmd,
            LIVESTREAM_TRANSCODE: self._generate_transcode_cmd}

        self.name = stream_name
        self.type = StreamMap.type

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
            msg = '{0} stream already started'.format(self._cls_name)
            self._log.info(msg)
            raise HomeCamError(msg)
        try:
            self._log.debug('{0} ffmpeg command: {1}'.format(
                self._cls_name, self._cmd))
            self._proc = subprocess.Popen(self._cmd,
                                          shell=True,
                                          stderr=subprocess.STDOUT,
                                          stdout=subprocess.PIPE,
                                          universal_newlines=True)
            self._start_ts = int(time.time())
            self._started.set()
        except Exception:
            err_msg = '{0} failed to start'.format(self._cls_name)
            self._log.exception(err_msg)
            raise HomeCamError(err_msg)

    def stop(self, disable=True):
        """Stop the stream."""
        def clear_status():
            if disable:
                self._started.clear()

        if not self.is_started():
            msg = '{0} already stopped'.format(self._cls_name)
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

    def get_stdout(self):
        return self._proc.stdout.readline().rstrip()

    def _generate_cmd(self):
        try:
            # e.g. transcode, tpl_kitchen
            processing_type, tpl_name = self._conf.template.split('.')
        except ValueError:
            err_msg = 'Failed to load {0} template "{1}"'.format(
                self._cls_name, self._conf.template)
            self._log.error(err_msg)
            raise HomeCamError(err_msg)

        self._stream_conf = self._conf_tpl[self.name][processing_type][tpl_name]

        null_audio = FFMPEG_CMD_NULL_AUDIO if self._stream_conf.null_audio else \
            {k: '' for k in FFMPEG_CMD_NULL_AUDIO}

        cmd_transcode = ''
        if processing_type == LIVESTREAM_TRANSCODE:
            cmd_transcode = FFMPEG_CMD_TRANSCODE_GENERAL.format(
                average_bitrate=self._stream_conf.encode.average_bitrate,
                bufsize=self._stream_conf.encode.bufsize,
                framerate=self._stream_conf.encode.framerate,
                maxrate=self._stream_conf.encode.maxrate,
                pass_mode=self._stream_conf.encode.pass_mode,
                pix_fmt=self._stream_conf.encode.pix_fmt,
                scale=self._generate_scale_cmd())

        cmd_tpl = FFMPEG_CMD.format(abitrate=null_audio['bitrate'],
                                    acodec=self._stream_conf.acodec,
                                    channel=self._stream_conf.channel,
                                    filter=null_audio['filter'],
                                    format=self._stream_conf.format,
                                    host=urlsplit(self._hik_host).netloc,
                                    inner_args=cmd_transcode,
                                    loglevel=self._stream_conf.loglevel,
                                    map=null_audio['map'],
                                    pw=self._hik_password,
                                    rtsp_transport_type=
                                        self._stream_conf.rtsp_transport_type,
                                    user=self._hik_user,
                                    vcodec=self._stream_conf.vcodec)

        self._cmd_gen_dispatcher[processing_type](cmd_tpl)

    def _generate_scale_cmd(self):
        return FFMPEG_CMD_SCALE_FILTER.format(
                width=self._stream_conf.encode.scale.width,
                height=self._stream_conf.encode.scale.height,
                format=self._stream_conf.encode.scale.format) \
            if self._stream_conf.encode.scale.enabled else ''

    @abc.abstractmethod
    def _generate_direct_cmd(self, cmd_tpl):
        # self._cmd = cmd_tpl.format(...)
        pass

    @abc.abstractmethod
    def _generate_transcode_cmd(self, cmd_tpl):
        # self._cmd = cmd_tpl.format(...)
        pass


class YouTubeStreamService(FFMPEGBaseStreamService):
    """YouTube livestream Service class."""

    def __init__(self, conf, hik_user, hik_password, hik_host):
        super().__init__(StreamMap.YOUTUBE, conf, hik_user, hik_password, hik_host)

    def _generate_direct_cmd(self, cmd_tpl):
        self._cmd = cmd_tpl.format(output=self._generate_output())

    def _generate_transcode_cmd(self, cmd_tpl):
        inner_args = FFMPEG_TRANSCODE_MAP[self.name].format(
            preset=self._stream_conf.encode.preset,
            tune=self._stream_conf.encode.tune)
        self._cmd = cmd_tpl.format(output=self._generate_output(),
                                   inner_args=inner_args)

    def _generate_output(self):
        # urljoin does not support rtmp protocol
        return '{0}/{1}'.format(self._stream_conf.url, self._stream_conf.key)


class IcecastStreamService(FFMPEGBaseStreamService):
    """Icecast livestream class."""

    def __init__(self, conf, hik_user, hik_password, hik_host):
        super().__init__(StreamMap.ICECAST, conf, hik_user, hik_password, hik_host)

    def _generate_direct_cmd(self):
        raise HomeCamError('{0} does not support direct streaming, change'
                           'template type'.format(self._cls_name))

    def _generate_transcode_cmd(self, cmd_tpl):
        inner_args = FFMPEG_TRANSCODE_MAP[self.name].format(
            ice_genre=self._stream_conf.ice_stream.ice_genre,
            ice_name=self._stream_conf.ice_stream.ice_name,
            ice_description=self._stream_conf.ice_stream.ice_description,
            ice_public=self._stream_conf.ice_stream.ice_public,
            content_type=self._stream_conf.ice_stream.content_type,
            deadline=self._stream_conf.ice_stream.deadline,
            password=self._stream_conf.ice_stream.password,
            speed=self._stream_conf.ice_stream.speed)
        self._cmd = cmd_tpl.format(output=self._stream_conf.ice_stream.url,
                                   inner_args=inner_args)


class TwitchStreamService(FFMPEGBaseStreamService):
    """Twitch livestream class."""

    def __init__(self, conf, hik_user, hik_password, hik_host):
        super().__init__(StreamMap.TWITCH, conf, hik_user, hik_password, hik_host)
        raise NotImplementedError
