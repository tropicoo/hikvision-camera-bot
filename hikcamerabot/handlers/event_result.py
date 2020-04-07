"""Result event handlers module."""

import abc
import logging
import os

from telegram import ParseMode

from hikcamerabot.constants import DETECTION_SWITCH_MAP, SEND_TIMEOUT
from hikcamerabot.utils import make_bold, format_ts


class BaseResultEventHandler(metaclass=abc.ABCMeta):

    def __init__(self, bot, cam_registry):
        self._log = logging.getLogger(self.__class__.__name__)
        self._bot = bot
        self._cam_registry = cam_registry

    def __call__(self, data):
        self._handle(data)

    @abc.abstractmethod
    def _handle(self, data):
        pass


class ResultAlertMessageHandler(BaseResultEventHandler):

    def _handle(self, data):
        msg = data['msg']
        cam_id = data['cam_id']
        is_html = data['html']
        self._bot.send_message_all(msg)


class ResultStreamMessageHandler(BaseResultEventHandler):

    def _handle(self, data):
        msg = data['msg']
        cam_id = data['cam_id']
        is_html = data['html']
        self._bot.send_message_all(msg)


class ResultAlertVideoHandler(BaseResultEventHandler):

    def _handle(self, data):
        videos = data['videos']
        cam_meta = self._cam_registry.get_conf(data['cam_id'])
        caption = f'Alert video from {cam_meta.description}\n/list cameras'

        for vid in videos:
            try:
                with open(vid, 'rb') as fd_in:
                    self._send_video(fd_in, caption)
            finally:
                os.remove(vid)

    def _send_video(self, video_fh, caption):
        for uid in self._bot.user_ids:
            self._bot.send_document(chat_id=uid, document=video_fh,
                                    caption=caption,
                                    timeout=SEND_TIMEOUT)


class ResultAlertSnapshotHandler(BaseResultEventHandler):

    def _handle(self, data):
        _date = format_ts(data['ts'])

        detection_key = data['detection_key']
        alert_count = data['alert_count']
        resized = data['resized']
        photo = data['img']
        cam_id = data['cam_id']
        cam_meta = self._cam_registry.get_conf(cam_id)

        caption = f'Alert snapshot taken on {_date} ' \
                  f'(alert #{alert_count})\n/list cameras'
        reply_html = '<b>{0} Alert</b>\nSending snapshot ' \
                     'from {1}'.format(
            cam_meta.description,
            DETECTION_SWITCH_MAP[detection_key]['name'])

        for uid in self._bot.user_ids:
            self._bot.send_message(chat_id=uid, text=reply_html,
                                   parse_mode=ParseMode.HTML)
            if resized:
                name = f'Full_alert_snapshot_{_date}.jpg'
                self._bot.send_document(chat_id=uid, document=photo,
                                        caption=caption,
                                        filename=name,
                                        timeout=SEND_TIMEOUT)
            else:
                self._bot.send_photo(chat_id=uid, photo=photo,
                                     caption=caption,
                                     timeout=SEND_TIMEOUT)


class ResultStreamConfHandler(BaseResultEventHandler):

    def _handle(self, data):
        cam_id, update = self._bot._updates.pop(data['event_id'])
        name = data['name']
        switch = data['params']['switch']
        msg = data.get('msg') or '{0} stream successfully {1}'.format(
            name, 'enabled' if switch else 'disabled')
        update.message.reply_html(make_bold(msg))
        self._log.info(msg)


class ResultAlarmConfHandler(BaseResultEventHandler):

    def _handle(self, data):
        cam_id, update = self._bot._updates.pop(data['event_id'])
        name = data['name']
        switch = data['params']['switch']

        msg = data.get('msg') or '{0} successfully {1}'.format(
            name, 'enabled' if switch else 'disabled')
        update.message.reply_html(make_bold(msg))
        self._log.info(msg)
        # err_msg = 'Failed to {0} {1}: {2}'.format(
        #     'enable' if switch else 'disable', name, err)
        # update.message.reply_text(err_msg)


class ResultDetectionConfHandler(BaseResultEventHandler):
    def _handle(self, data):
        cam_id, update = self._bot._updates.pop(data['event_id'])
        name = DETECTION_SWITCH_MAP[data['name']]['name']
        switch = data['params']['switch']

        msg = data.get('msg') or '{0} successfully {1}'.format(
            name, 'enabled' if switch else 'disabled')
        update.message.reply_html(make_bold(msg))
        self._log.info(msg)
        # err_msg = 'Failed to {0} {1}: {2}'.format(
        #     'enable' if switch else 'disable', name, err)
        # update.message.reply_text(err_msg)


class ResultTakeSnapshotHandler(BaseResultEventHandler):

    def _handle(self, data):
        resize = data['params']['resize']
        if resize:
            return self._send_resized_photo(data)
        return self._send_full_photo(data)

    def _send_resized_photo(self, data):
        cam_id, update = self._bot._updates.pop(data['event_id'])
        meta = self._cam_registry.get_conf(cam_id)

        caption = f'Snapshot taken on {format_ts(data["create_ts"])} ' \
                  f'(snapshot #{data["taken_count"]})'
        caption = f'{caption}\n/cmds_{cam_id}, /list'

        reply_html = f'Sending snapshot from {meta.description}'
        self._log.info('Sending resized cam snapshot')
        self._bot.reply_cam_photo(photo=data.get('img'), update=update,
                                  caption=caption,
                                  reply_html=make_bold(reply_html))
        self._log.info('Resized snapshot sent')

    def _send_full_photo(self, data):
        cam_id, update = self._bot._updates.pop(data['event_id'])
        meta = self._cam_registry.get_conf(cam_id)

        _date = format_ts(data["create_ts"])
        filename = f'Full snapshot {_date}.jpg'
        caption = f'Full snapshot at {_date} ' \
                  f'(snapshot #{data["taken_count"]})'
        caption = f'{caption}\n/cmds_{cam_id}, /list'

        reply_html = f'Sending snapshot from {meta.description}'
        self._log.info('Sending resized cam snapshot')
        self._bot.reply_cam_photo(photo=data.get('img'), update=update,
                                  caption=caption,
                                  reply_html=make_bold(reply_html),
                                  fullpic_name=filename,
                                  fullpic=True)
        self._log.info('Full snapshot %s sent', filename)
