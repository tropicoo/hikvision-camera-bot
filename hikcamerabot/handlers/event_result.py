"""Result event handlers module."""

import abc
import logging
import os
from io import BytesIO
from typing import Optional, TYPE_CHECKING, Union

from pyrogram.types import Message
from tenacity import retry, wait_fixed

from hikcamerabot.constants import (
    Alarm, DETECTION_SWITCH_MAP, Detection, Stream,
)
from hikcamerabot.utils.utils import format_ts, make_bold

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam
    from hikcamerabot.camerabot import CameraBot


class AbstractResultEventHandler(metaclass=abc.ABCMeta):

    def __init__(self, bot: 'CameraBot') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._bot = bot

    async def handle(self, event: dict) -> None:
        await self._handle(event)

    @abc.abstractmethod
    async def _handle(self, event: dict) -> None:
        pass


class ResultAlertVideoHandler(AbstractResultEventHandler):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._video_file_cache: dict[str, str] = {}

    async def _handle(self, event: dict) -> None:
        try:
            await self.__handle(event)
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        self._video_file_cache = {}

    async def __handle(self, event: dict) -> None:
        cam: 'HikvisionCam' = event['cam']
        video_path: str = event['video_path']
        caption = f'Alert video from {cam.description} {cam.hashtag}\n/cmds_{cam.id}, ' \
                  f'/list_cams'
        try:
            for uid in self._bot.user_ids:
                await self._send_video(uid, video_path, caption, self._bot)
        finally:
            os.remove(video_path)

    @retry(wait=wait_fixed(0.5))
    async def _send_video(self, uid: int, video_path: str, caption: str,
                          bot: 'CameraBot') -> None:
        file_, is_cached = self._get_file(video_path)
        await bot.send_chat_action(chat_id=uid, action='upload_video')
        message = await bot.send_video(chat_id=uid, video=file_, caption=caption)
        if not is_cached:
            self._video_file_cache[video_path] = message.video.file_id

    def _get_file(self, video_path: str) -> tuple[str, bool]:
        """Get str file id from cache or `InputFile` from video path.
        Indicate whether file is cached or not.
        """
        self._log.debug('Video cache: %s', self._video_file_cache)
        try:
            return self._video_file_cache[video_path], True
        except KeyError:
            return video_path, False


class ResultRecordVideoGifHandler(AbstractResultEventHandler):
    """Requested record of video gif result handler."""

    async def _handle(self, event: dict) -> None:
        video_path: str = event['video_path']
        try:
            await self._upload_video(event)
        finally:
            os.remove(video_path)

    @retry(wait=wait_fixed(0.5))
    async def _upload_video(self, event):
        cam: 'HikvisionCam' = event['cam']
        message: Message = event['message']  # Stale context, can't `reply`.
        video_path: str = event['video_path']
        caption = f'Video from {cam.description} {cam.hashtag}\n/cmds_{cam.id}, ' \
                  f'/list_cams'
        await self._bot.send_chat_action(message.chat.id, action='upload_video')
        await self._bot.send_video(
            message.chat.id,
            video=video_path,
            caption=caption,
            reply_to_message_id=message.message_id,
        )


class ResultAlertSnapshotHandler(AbstractResultEventHandler):

    async def _handle(self, event: dict) -> None:
        cam: 'HikvisionCam' = event['cam']

        date_ = format_ts(event['ts'])
        detection_type: Detection = event['detection_type']
        alert_count: int = event['alert_count']
        resized: bool = event['resized']
        photo: BytesIO = event['img']
        trigger_name: str = DETECTION_SWITCH_MAP[detection_type]['name'].value

        caption = f'[{cam.description}] {trigger_name} at {date_} ' \
                  f'(alert #{alert_count}) {cam.hashtag}\n/cmds_{cam.id}, /list_cams'

        async def send_document(photo_: Union[BytesIO, str]) -> Message:
            return await self._bot.send_document(
                chat_id=uid,
                document=photo_,
                file_name=f'Full_alert_snapshot_{date_}.jpg',
                caption=caption)

        async def send_photo(photo_: Union[BytesIO, str]) -> Message:
            return await self._bot.send_photo(chat_id=uid, photo=photo_,
                                              caption=caption)

        cached_id: Optional[str] = None
        for uid in self._bot.user_ids:
            try:
                if resized:
                    message = await send_photo(cached_id or photo)
                    cached_id = message.photo.file_id
                else:
                    message = await send_document(cached_id or photo)
                    cached_id = message.document.file_id
            except Exception:
                self._log.exception('Failed to send message to user ID %s', uid)


class ResultStreamConfHandler(AbstractResultEventHandler):

    async def _handle(self, event: dict) -> None:
        message: Message = event['message']
        name: Stream = event['name']
        switch: bool = event['params']['switch']
        text: str = event.get('text') or '{0} stream successfully {1}'.format(
            name.value.capitalize(), 'enabled' if switch else 'disabled')
        await message.reply(make_bold(text), parse_mode='HTML')
        self._log.info(text)


class ResultSendTextHandler(AbstractResultEventHandler):

    async def _handle(self, event: dict) -> None:
        message: Optional[Message] = event.get('message')
        parse_mode: Optional[str] = event.get('parse_mode')
        text: str = event['text']
        if message:
            await self._bot.send_message(
                text=text,
                chat_id=message.chat.id,
                reply_to_message_id=message.message_id,
                parse_mode=parse_mode,
            )
        else:
            await self._bot.send_message_all(text, parse_mode=parse_mode)


class ResultAlarmConfHandler(AbstractResultEventHandler):

    async def _handle(self, event: dict) -> None:
        message: Message = event['message']
        name: Alarm = event['name']
        switch: bool = event['params']['switch']

        text: str = event.get('text') or '{0} successfully {1}'.format(
            name.value.capitalize(), 'enabled' if switch else 'disabled')
        await message.reply(make_bold(text), parse_mode='HTML')
        self._log.info(text)
        # err_msg = 'Failed to {0} {1}: {2}'.format(
        #     'enable' if switch else 'disable', name, err)
        # await message.reply_text(err_msg)


class ResultDetectionConfHandler(AbstractResultEventHandler):
    async def _handle(self, event: dict) -> None:
        message: Message = event['message']
        name: str = DETECTION_SWITCH_MAP[event['name']]['name'].value
        switch: bool = event['params']['switch']

        text = event.get('text') or '{0} successfully {1}'.format(
            name, 'enabled' if switch else 'disabled')
        await message.reply(make_bold(text), parse_mode='HTML')
        self._log.info(text)
        # err_msg = 'Failed to {0} {1}: {2}'.format(
        #     'enable' if switch else 'disable', name, err)
        # await message.reply_text(err_msg)


class ResultTakeSnapshotHandler(AbstractResultEventHandler):

    async def _handle(self, event: dict) -> None:
        await self._send_resized_photo(event) if event['params']['resize'] else \
            await self._send_full_photo(event)

    async def _send_resized_photo(self, event: dict) -> None:
        cam: 'HikvisionCam' = event['cam']
        message: Message = event['message']

        caption = f'[{cam.conf.description}] ' \
                  f'Snapshot taken on {format_ts(event["create_ts"])} ' \
                  f'(snapshot #{event["taken_count"]}) {cam.hashtag}'
        caption = f'{caption}\n/cmds_{cam.id}, /list_cams'

        self._log.info('Sending resized cam snapshot')
        await self._bot.send_chat_action(chat_id=message.chat.id,
                                         action='upload_photo')
        await message.reply_photo(event['img'], caption=caption)
        self._log.info('Resized snapshot sent')

    async def _send_full_photo(self, event: dict) -> None:
        cam: 'HikvisionCam' = event['cam']
        message: Message = event['message']

        date_ = format_ts(event["create_ts"])
        filename = f'Full snapshot {date_}.jpg'
        caption = f'[{cam.description}] Full snapshot at {date_} ' \
                  f'(snapshot #{event["taken_count"]}) {cam.hashtag}'
        caption = f'{caption}\n/cmds_{cam.id}, /list_cams'

        self._log.info('Sending full cam snapshot')
        await self._bot.send_chat_action(chat_id=message.chat.id,
                                         action='upload_photo')
        await message.reply_document(document=event['img'], caption=caption,
                                     file_name=filename)
        self._log.info('Full snapshot "%s" sent', filename)
