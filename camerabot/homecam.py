"""Home Camera Module."""

import logging
import subprocess
import time
from datetime import datetime
from io import BytesIO
from queue import Queue
from threading import Event
from urllib.parse import urlsplit

from PIL import Image

from camerabot.api import API
from camerabot.constants import (IMG_SIZE, IMG_FORMAT, IMG_QUALITY,
                                 CMD_YT_FFMPEG, FFMPEG_NULL_AUDIO)
from camerabot.exceptions import HomeCamError
from camerabot.utils import kill_proc_tree


class HomeCam:
    """Camera class."""

    def __init__(self, cam_data):
        self._log = logging.getLogger(self.__class__.__name__)
        self.description = cam_data['description']
        self._log.debug('Initializing {0}'.format(self.description))
        self._api = API(api_conf=cam_data['api'])
        self.snapshots_taken = 0

        md_conf = cam_data['motion_detection']
        yt_conf = cam_data['live_stream']['youtube']
        self.__conf = cam_data

        self.alert_on = Event()
        self.alert_enabled = md_conf['alert']['enabled']
        self.alert_queue = Queue()

        self.alert_delay = md_conf['alert']['delay']
        self.alert_fullpic = md_conf['alert']['fullpic']
        self.alert_count = 0

        self.stream_yt_enabled = yt_conf['enabled']
        self.stream_yt_restart_period = yt_conf['restart_period']
        self.stream_yt_restart_pause = yt_conf['restart_pause']

        self.stream_yt_on = Event()
        self._stream_yt_proc = None

    def __repr__(self):
        return '<HomeCam desc="{0}">'.format(self.description)

    def take_snapshot(self, resize=False):
        """Takes and returns full or resized snapshot from the camera."""
        self._log.debug('Taking snapshot from {0}'.format(self.description))
        try:
            res = self._api.take_snapshot()
            snapshot_timestamp = int(datetime.now().timestamp())
            self.snapshots_taken += 1
            snapshot = self._resize_snapshot(res.raw) if resize else res.raw
        except HomeCamError:
            raise
        except Exception as err:
            err_msg = 'Failed to take snapshot from {0}'.format(self.description)
            self._log.error(err_msg)
            raise HomeCamError(err_msg) from err
        return snapshot, snapshot_timestamp

    def alert(self, enable=True):
        if enable and self.alert_on.is_set():
            raise HomeCamError('Alert Mode already enabled')
        elif not enable and not self.alert_on.is_set():
            raise HomeCamError('Alert Mode already disabled')
        if enable:
            self.alert_on.set()
        else:
            self.alert_on.clear()

    def get_alert_stream(self):
        return self._api.get_alert_stream()

    def stream_yt_enable(self, restart=False):
        if self.stream_yt_on.is_set() and not restart:
            raise HomeCamError('YT stream already enabled')
        self.stream_yt_on.set()

        api_conf = self.__conf['api']
        yt_conf = self.__conf['live_stream']['youtube']

        null_audio = FFMPEG_NULL_AUDIO if yt_conf['null_audio'] else \
            {k: '' for k in FFMPEG_NULL_AUDIO}

        cmd = CMD_YT_FFMPEG.format(filter=null_audio['filter'],
                                   user=api_conf['auth']['user'],
                                   pw=api_conf['auth']['password'],
                                   host=urlsplit(api_conf['host']).netloc,
                                   channel=yt_conf['channel'],
                                   map=null_audio['map'],
                                   bitrate=null_audio['bitrate'],
                                   url=yt_conf['url'],
                                   key=yt_conf['key']).split()
        try:
            if restart:
                kill_proc_tree(self._stream_yt_proc.pid)
                time.sleep(self.stream_yt_restart_pause)
            self._stream_yt_proc = subprocess.Popen(cmd,
                                                    stdout=subprocess.PIPE,
                                                    stderr=subprocess.STDOUT)
        except Exception as err:
            err_msg = 'YT stream start exception.'
            self._log.exception(err_msg)
            raise HomeCamError(err_msg) from err

    def stream_yt_disable(self):
        if not self.stream_yt_on.is_set():
            raise HomeCamError('YT stream already disabled')
        kill_proc_tree(self._stream_yt_proc.pid)
        self.stream_yt_on.clear()

    def motion_detection_switch(self, enable=True):
        """Motion Detection Switch."""
        try:
            self._log.debug('{0} Motion Detection'.format('Enabling' if enable
                                                          else 'Disabling'))
            msg = self._api.motion_detection_switch(enable=enable)
        except Exception as err:
            err_msg = 'Motion Detection Switch encountered an error.'
            self._log.exception(err_msg)
            raise HomeCamError(err_msg) from err
        return msg

    def _resize_snapshot(self, raw_snapshot):
        """Returns resized JPEG snapshot."""
        try:
            snapshot = Image.open(raw_snapshot)
            resized_snapshot = BytesIO()

            snapshot.resize(IMG_SIZE, Image.ANTIALIAS)
            snapshot.save(resized_snapshot, IMG_FORMAT, quality=IMG_QUALITY)
            resized_snapshot.seek(0)

            self._log.debug("Raw snapshot: {0}, {1}, {2}".format(snapshot.format,
                                                                 snapshot.mode,
                                                                 snapshot.size))
            self._log.debug("Resized snapshot: {0}".format(IMG_SIZE))
        except Exception as err:
            err_msg = 'Failed to resize snapshot taken from {0}'.format(
                self.description)
            self._log.exception(err_msg)
            raise HomeCamError(err_msg) from err
        return resized_snapshot
