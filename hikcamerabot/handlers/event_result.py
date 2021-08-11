"""Result event handlers module."""

import abc
import logging
import os
from typing import Union

from aiogram.types import InputFile, Message

from hikcamerabot.constants import DETECTION_SWITCH_MAP
from hikcamerabot.utils.utils import format_ts, make_bold


class AbstractResultEventHandler(metaclass=abc.ABCMeta):

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)

    async def handle(self, event: dict) -> None:
        await self._handle(event)

    @abc.abstractmethod
    async def _handle(self, event: dict) -> None:
        pass


class ResultAlertVideoHandler(AbstractResultEventHandler):

    def __init__(self):
        super().__init__()
        self._video_file_cache: dict[str, str] = {}

    async def _handle(self, event: dict) -> None:
        try:
            await self.__handle(event)
        finally:
            self._cleanup()

    def _cleanup(self):
        self._video_file_cache = {}

    async def __handle(self, event: dict) -> None:
        cam = event['cam']
        video_path = event['video_path']
        caption = f'Alert video from {cam.description} {cam.hashtag}\n/cmds_{cam.id}, ' \
                  f'/list_cams cameras'
        try:
            for uid in cam.bot.user_ids:
                await self._send_video(uid, video_path, caption, cam.bot)
        finally:
            os.remove(video_path)

    async def _send_video(self, uid: int, video_path: str, caption: str,
                          bot) -> None:
        file_, is_cached = self._get_file(video_path)
        try:
            await bot.send_chat_action(chat_id=uid, action='upload_video')
            message = await bot.send_video(chat_id=uid, video=file_,
                                           caption=caption)
        except Exception:
            self._log.exception('Failed to send video %s to user ID %s', file_,
                                uid)
            return
        if not is_cached:
            self._video_file_cache[video_path] = message.video.file_id

    def _get_file(self, video_path: str) -> tuple[Union[str, InputFile], bool]:
        """Get str file id from cache or `InputFile` from video path.
        Indicate whether file is cached or not.
        """
        self._log.debug('Video cache: %s', self._video_file_cache)
        try:
            return self._video_file_cache[video_path], True
        except KeyError:
            return InputFile(video_path), False


class ResultRecordVideoGifHandler(AbstractResultEventHandler):
    """Requested record of video gif result handler."""

    async def _handle(self, event: dict) -> None:
        await self.__handle(event)

    async def __handle(self, event: dict) -> None:
        cam = event['cam']
        message: Message = event['message']  # Stale context, can't `answer`.
        video_path = event['video_path']
        caption = f'Video from {cam.description} {cam.hashtag}\n/cmds_{cam.id}, ' \
                  f'/list_cams cameras'
        try:
            await cam.bot.send_chat_action(message.chat.id, action='upload_video')
            await cam.bot.send_video(
                message.chat.id,
                video=InputFile(video_path),
                caption=caption,
                reply_to_message_id=message.message_id,
            )
        finally:
            os.remove(video_path)


class ResultAlertSnapshotHandler(AbstractResultEventHandler):

    async def _handle(self, event: dict) -> None:
        cam = event['cam']

        date_ = format_ts(event['ts'])
        detection_key = event['detection_key']
        alert_count = event['alert_count']
        resized = event['resized']
        photo = InputFile(event['img'])
        trigger_name = DETECTION_SWITCH_MAP[detection_key]['name']

        caption = f'[{cam.description}] {trigger_name} at {date_} ' \
                  f'(alert #{alert_count}) {cam.hashtag}\n/cmds_{cam.id}, /list_cams'

        async def send_document(photo: Union[InputFile, str]) -> Message:
            if not isinstance(photo, str):
                photo.filename = f'Full_alert_snapshot_{date_}.jpg'
            return await cam.bot.send_document(
                chat_id=uid,
                document=photo,
                caption=caption)

        async def send_photo(photo: Union[InputFile, str]) -> Message:
            return await cam.bot.send_photo(chat_id=uid, photo=photo,
                                            caption=caption)

        cached = False
        for uid in cam.bot.user_ids:
            try:
                if resized:
                    message = await send_photo(photo)
                    file_id = message.photo[0]['file_id']
                else:
                    message = await send_document(photo)
                    file_id = message.document.file_id
                if not cached:
                    photo = file_id
            except Exception:
                self._log.exception('Failed to send message to user ID %s', uid)


class ResultStreamConfHandler(AbstractResultEventHandler):

    async def _handle(self, event: dict):
        message = event['message']
        name = event['name']
        switch = event['params']['switch']
        msg = event.get('msg') or '{0} stream successfully {1}'.format(
            name, 'enabled' if switch else 'disabled')
        await message.answer(make_bold(msg), parse_mode='HTML')
        self._log.info(msg)


class ResultAlarmConfHandler(AbstractResultEventHandler):

    async def _handle(self, event: dict):
        message = event['message']
        name = event['name']
        switch = event['params']['switch']

        msg = event.get('msg') or '{0} successfully {1}'.format(
            name, 'enabled' if switch else 'disabled')
        await message.answer(make_bold(msg), parse_mode='HTML')
        self._log.info(msg)
        # err_msg = 'Failed to {0} {1}: {2}'.format(
        #     'enable' if switch else 'disable', name, err)
        # await message.reply_text(err_msg)


class ResultDetectionConfHandler(AbstractResultEventHandler):
    async def _handle(self, event: dict):
        message = event['message']
        name = DETECTION_SWITCH_MAP[event['name']]['name']
        switch = event['params']['switch']

        msg = event.get('msg') or '{0} successfully {1}'.format(
            name, 'enabled' if switch else 'disabled')
        await message.answer(make_bold(msg), parse_mode='HTML')
        self._log.info(msg)
        # err_msg = 'Failed to {0} {1}: {2}'.format(
        #     'enable' if switch else 'disable', name, err)
        # await message.reply_text(err_msg)


class ResultTakeSnapshotHandler(AbstractResultEventHandler):

    async def _handle(self, event: dict) -> None:
        await self._send_resized_photo(event) if event['params']['resize'] else \
            await self._send_full_photo(event)

    async def _send_resized_photo(self, event: dict) -> None:
        cam = event['cam']
        message: Message = event['message']

        caption = f'[{cam.conf.description}] ' \
                  f'Snapshot taken on {format_ts(event["create_ts"])} ' \
                  f'(snapshot #{event["taken_count"]}) {cam.hashtag}'
        caption = f'{caption}\n/cmds_{cam.id}, /list_cams'

        self._log.info('Sending resized cam snapshot')
        await cam.bot.send_chat_action(chat_id=message.chat.id,
                                       action='upload_photo')
        await message.reply_photo(InputFile(event['img']), caption)
        self._log.info('Resized snapshot sent')

    async def _send_full_photo(self, event: dict) -> None:
        cam = event['cam']
        message: Message = event['message']

        date_ = format_ts(event["create_ts"])
        filename = f'Full snapshot {date_}.jpg'
        caption = f'[{cam.description}] Full snapshot at {date_} ' \
                  f'(snapshot #{event["taken_count"]}) {cam.hashtag}'
        caption = f'{caption}\n/cmds_{cam.id}, /list_cams'

        self._log.info('Sending full cam snapshot')
        await cam.bot.send_chat_action(chat_id=message.chat.id,
                                       action='upload_photo')
        photo = InputFile(event['img'], filename=filename)
        await message.reply_document(document=photo, caption=caption)
        self._log.info('Full snapshot "%s" sent', filename)
