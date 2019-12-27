"""Livestream module."""

import abc
import subprocess
import time
from threading import Event
from urllib.parse import urlsplit

from psutil import NoSuchProcess

from hikcamerabot.config import (get_livestream_tpl_config,
                                 get_encoding_tpl_config)
from hikcamerabot.constants import (Streams,
                                    VideoEncoders,
                                    FFMPEG_CMD, FFMPEG_CMD_NULL_AUDIO,
                                    FFMPEG_CMD_SCALE_FILTER,
                                    FFMPEG_CMD_TRANSCODE_GENERAL,
                                    FFMPEG_CMD_TRANSCODE,
                                    FFMPEG_CMD_TRANSCODE_ICECAST)
from hikcamerabot.exceptions import ServiceRuntimeError, ServiceConfigError
from hikcamerabot.services import BaseService
from hikcamerabot.utils import kill_proc_tree, shallow_sleep


class FFMPEGBaseStreamService(BaseService, metaclass=abc.ABCMeta):
    """livestream Service Base Class."""

    # Not needed since abc.abstractmethods are defined
    # def __new__(cls, *args, **kwargs):
    #     if cls is FFMPEGBaseStreamService:
    #         raise TypeError('{0} class may not be instantiated'.format(
    #             cls.__name__))
    #     return super().__new__(cls)

    def __init__(self, stream_name, conf, hik_user, hik_password, hik_host):
        super().__init__()

        self._cmd_gen_dispatcher = {
            VideoEncoders.X264: self._generate_x264_cmd,
            VideoEncoders.VP9: self._generate_vp9_cmd}

        self.name = stream_name
        self.type = Streams.SERVICE_TYPE
        self._conf = conf
        self._hik_user = hik_user
        self._hik_password = hik_password
        self._hik_host = hik_host

        self._proc = None
        self._start_ts = None
        self._stream_conf = None
        self._enc_conf = None
        self._cmd = None
        self._generate_cmd()

        self._started = Event()

    def start(self, skip_check=False):
        """Start the stream."""
        if not skip_check and self.is_started():
            msg = f'{self._cls_name} stream already started'
            self._log.info(msg)
            raise ServiceRuntimeError(msg)
        try:
            self._log.debug('%s ffmpeg command: %s', self._cls_name, self._cmd)
            self._proc = subprocess.Popen(self._cmd,
                                          shell=True,
                                          stderr=subprocess.STDOUT,
                                          stdout=subprocess.PIPE,
                                          universal_newlines=True)
            self._start_ts = int(time.time())
            self._started.set()
        except Exception:
            err_msg = f'{self._cls_name} failed to start'
            self._log.exception(err_msg)
            raise ServiceRuntimeError(err_msg)

    def stop(self, disable=True):
        """Stop the stream."""

        def clear_status():
            if disable:
                self._started.clear()

        if not self.is_started():
            msg = f'{self._cls_name} already stopped'
            self._log.info(msg)
            raise ServiceRuntimeError(msg)
        try:
            kill_proc_tree(self._proc.pid)
            clear_status()
        except NoSuchProcess as err:
            self._log.warning('PID %s is not running: %s', self._proc.pid, err)
            clear_status()
        except Exception:
            err_msg = 'Failed to kill/disable YouTube stream'
            self._log.exception(err_msg)
            raise ServiceRuntimeError(err_msg)

    def need_restart(self):
        """Check if the stream needs to be restarted."""
        return int(time.time()) > \
               self._start_ts + self._stream_conf.restart_period

    def restart(self):
        """Restart the stream."""
        if self.is_started():
            self.stop(disable=False)
        self._log.debug('Sleeping for %ss', self._stream_conf.restart_pause)
        shallow_sleep(self._stream_conf.restart_pause)
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
            tpl_name_ls = self._conf.livestream_template
            enc_codec_name, tpl_name_enc = self._conf.encoding_template.split(
                '.')
        except ValueError:
            err_msg = f'Failed to load {self._cls_name} templates'
            self._log.error(err_msg)
            raise ServiceConfigError(err_msg)

        self._stream_conf = get_livestream_tpl_config()[self.name][tpl_name_ls]
        self._enc_conf = get_encoding_tpl_config()[enc_codec_name][
            tpl_name_enc]

        null_audio = FFMPEG_CMD_NULL_AUDIO if self._enc_conf.null_audio else \
            {k: '' for k in FFMPEG_CMD_NULL_AUDIO}

        cmd_tpl = FFMPEG_CMD.format(abitrate=null_audio['bitrate'],
                                    acodec=self._enc_conf.acodec,
                                    channel=self._stream_conf.channel,
                                    filter=null_audio['filter'],
                                    format=self._enc_conf.format,
                                    host=urlsplit(self._hik_host).netloc,
                                    loglevel=self._enc_conf.loglevel,
                                    map=null_audio['map'],
                                    pw=self._hik_password,
                                    rtsp_transport_type=
                                    self._enc_conf.rtsp_transport_type,
                                    user=self._hik_user,
                                    vcodec=self._enc_conf.vcodec)

        cmd_transcode = ''
        if enc_codec_name in FFMPEG_CMD_TRANSCODE:
            cmd_transcode = FFMPEG_CMD_TRANSCODE_GENERAL.format(
                average_bitrate=self._enc_conf.average_bitrate,
                bufsize=self._enc_conf.bufsize,
                framerate=self._enc_conf.framerate,
                maxrate=self._enc_conf.maxrate,
                pass_mode=self._enc_conf.pass_mode,
                pix_fmt=self._enc_conf.pix_fmt,
                scale=self._generate_scale_cmd())

        self._generate_transcode_cmd(cmd_tpl, cmd_transcode, enc_codec_name)

    def _generate_scale_cmd(self):
        return FFMPEG_CMD_SCALE_FILTER.format(
            width=self._enc_conf.scale.width,
            height=self._enc_conf.scale.height,
            format=self._enc_conf.scale.format) \
            if self._enc_conf.scale.enabled else ''

    def _generate_x264_cmd(self):
        return FFMPEG_CMD_TRANSCODE[VideoEncoders.X264].format(
            preset=self._enc_conf.preset,
            tune=self._enc_conf.tune)

    def _generate_vp9_cmd(self):
        return FFMPEG_CMD_TRANSCODE[VideoEncoders.VP9].format(
            deadline=self._enc_conf.deadline,
            speed=self._enc_conf.speed)

    @abc.abstractmethod
    def _generate_transcode_cmd(self, cmd_tpl, cmd_transcode, enc_codec_name):
        # Example: self._cmd = cmd_tpl.format(...)
        pass


class YouTubeStreamService(FFMPEGBaseStreamService):
    """YouTube livestream Service Class."""

    def __init__(self, conf, hik_user, hik_password, hik_host):
        super().__init__(Streams.YOUTUBE, conf, hik_user, hik_password,
                         hik_host)

    def _generate_transcode_cmd(self, cmd_tpl, cmd_transcode, enc_codec_name):
        try:
            inner_args = self._cmd_gen_dispatcher[enc_codec_name]()
        except KeyError:
            inner_args = ''
        self._cmd = cmd_tpl.format(output=self._generate_output(),
                                   inner_args=cmd_transcode.format(
                                       inner_args=inner_args))

    def _generate_output(self):
        # urljoin does not support rtmp protocol
        return f'{self._stream_conf.url}/{self._stream_conf.key}'


class IcecastStreamService(FFMPEGBaseStreamService):
    """Icecast livestream Class."""

    def __init__(self, conf, hik_user, hik_password, hik_host):
        super().__init__(Streams.ICECAST, conf, hik_user, hik_password,
                         hik_host)

    def _generate_transcode_cmd(self, cmd_tpl, cmd_transcode, enc_codec_name):
        try:
            inner_args = self._cmd_gen_dispatcher[enc_codec_name]()
        except KeyError:
            raise ServiceConfigError(
                f'{self._cls_name} does not support {enc_codec_name} streaming,'
                f' change template type')
        icecast_args = FFMPEG_CMD_TRANSCODE_ICECAST.format(
            ice_genre=self._stream_conf.ice_stream.ice_genre,
            ice_name=self._stream_conf.ice_stream.ice_name,
            ice_description=self._stream_conf.ice_stream.ice_description,
            ice_public=self._stream_conf.ice_stream.ice_public,
            content_type=self._stream_conf.ice_stream.content_type,
            password=self._stream_conf.ice_stream.password)
        self._cmd = cmd_tpl.format(
            output=self._stream_conf.ice_stream.url,
            inner_args=' '.join([
                cmd_transcode.format(inner_args=inner_args),
                icecast_args]))


class TwitchStreamService(FFMPEGBaseStreamService):
    """Twitch livestream Class."""

    def __init__(self, conf, hik_user, hik_password, hik_host):
        super().__init__(Streams.TWITCH, conf, hik_user, hik_password,
                         hik_host)
        raise NotImplementedError
