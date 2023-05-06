"""Result event handlers module."""

import abc
import logging
import os
from io import BytesIO
from typing import TYPE_CHECKING, Optional

from emoji import emojize
from pyrogram.enums import ChatAction
from pyrogram.types import Message
from tenacity import retry, stop_after_attempt, wait_fixed

from hikcamerabot.constants import DETECTION_SWITCH_MAP
from hikcamerabot.event_engine.events.abstract import BaseOutboundEvent
from hikcamerabot.event_engine.events.outbound import (
    AlarmConfOutboundEvent,
    AlertSnapshotOutboundEvent,
    DetectionConfOutboundEvent,
    SendTextOutboundEvent,
    SnapshotOutboundEvent,
    StreamOutboundEvent,
    VideoOutboundEvent,
)
from hikcamerabot.utils.shared import bold, format_ts, send_text

if TYPE_CHECKING:
    from hikcamerabot.camerabot import CameraBot


class AbstractResultEventHandler(metaclass=abc.ABCMeta):
    def __init__(self, bot: 'CameraBot') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._bot = bot

    async def handle(self, event: BaseOutboundEvent) -> None:
        await self._handle(event)

    @abc.abstractmethod
    async def _handle(self, event: BaseOutboundEvent) -> None:
        pass


class ResultAlertVideoHandler(AbstractResultEventHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._video_file_cache: dict[str, str] = {}

    async def _handle(self, event: VideoOutboundEvent) -> None:
        try:
            await self.__handle(event)
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        self._video_file_cache = {}

    async def __handle(self, event: VideoOutboundEvent) -> None:
        cam = event.cam
        caption = (
            f'{emojize(":rotating_light:", language="alias")} '
            f'Alert video from {cam.description} {cam.hashtag}\n/cmds_{cam.id}, '
            f'/list_cams'
        )
        try:
            # Simple for loop because video cache will be used.
            for uid in self._bot.alert_users:
                await self._send_video(uid, event, caption)
        finally:
            os.remove(event.video_path)
            if event.thumb_path:
                os.remove(event.thumb_path)

    @retry(wait=wait_fixed(0.5), stop=stop_after_attempt(10))
    async def _send_video(
        self, uid: int, event: VideoOutboundEvent, caption: str
    ) -> None:
        try:
            file_, is_cached = self._get_file(event.video_path)
            await self._bot.send_chat_action(
                chat_id=uid, action=ChatAction.UPLOAD_VIDEO
            )
            message = await self._bot.send_video(
                chat_id=uid,
                caption=caption,
                video=file_,
                duration=event.video_duration,
                height=event.video_height,
                width=event.video_width,
                thumb=event.thumb_path,
                supports_streaming=True,
            )
            self._log.debug('Debug context message: %s', message)
            if message and message.video and not is_cached:
                self._video_file_cache[event.video_path] = message.video.file_id
        except Exception:
            self._log.exception(
                'Failed to send video in %s. Retrying', self.__class__.__name__
            )
            raise

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

    async def _handle(self, event: VideoOutboundEvent) -> None:
        try:
            await self._upload_video(event)
        finally:
            os.remove(event.video_path)
            if event.thumb_path:
                os.remove(event.thumb_path)

    @retry(wait=wait_fixed(0.5), stop=stop_after_attempt(10))
    async def _upload_video(self, event: VideoOutboundEvent) -> None:
        try:
            cam = event.cam
            message = event.message
            caption = (
                f'Video from {cam.description} {cam.hashtag}\n/cmds_{cam.id}, '
                f'/list_cams'
            )
            await self._bot.send_chat_action(
                message.chat.id, action=ChatAction.UPLOAD_VIDEO
            )
            await self._bot.send_video(
                message.chat.id,
                caption=caption,
                video=event.video_path,
                duration=event.video_duration,
                height=event.video_height,
                width=event.video_width,
                thumb=event.thumb_path,
                supports_streaming=True,
                reply_to_message_id=message.id,
            )
        except Exception:
            self._log.exception('Failed to upload video gif. Retrying')
            raise


class ResultAlertSnapshotHandler(AbstractResultEventHandler):
    async def _handle(self, event: AlertSnapshotOutboundEvent) -> None:
        cam = event.cam

        datetime_str = format_ts(event.ts)
        detection_type = event.detection_type
        alert_count = event.alert_count
        resized = event.resized
        photo = event.img
        trigger_name: str = DETECTION_SWITCH_MAP[detection_type]['name'].value

        caption = (
            f'[{cam.description}] {trigger_name} on {datetime_str} '
            f'(alert #{alert_count}) {cam.hashtag}\n/cmds_{cam.id}, /list_cams'
        )

        async def send_document(photo_: BytesIO | str) -> Message:
            return await self._bot.send_document(
                chat_id=uid,
                document=photo_,
                file_name=f'Full_alert_snapshot_{datetime_str}.jpg',
                caption=caption,
            )

        async def send_photo(photo_: BytesIO | str) -> Message:
            return await self._bot.send_photo(
                chat_id=uid, photo=photo_, caption=caption
            )

        cached_id: Optional[str] = None
        for uid in self._bot.alert_users:
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
    async def _handle(self, event: StreamOutboundEvent) -> None:
        message = event.message
        stream_type = event.stream_type
        state = event.state
        text: str = event.text or '{0} stream successfully {1}'.format(
            stream_type.value.capitalize(), 'enabled' if state else 'disabled'
        )
        await send_text(text=bold(text), message=message, quote=True)
        self._log.info(text)


class ResultSendTextHandler(AbstractResultEventHandler):
    async def _handle(self, event: SendTextOutboundEvent) -> None:
        text = event.text
        parse_mode = event.parse_mode
        message = event.message
        if message:
            await send_text(
                text=text, message=message, quote=True, parse_mode=parse_mode
            )
        else:
            await self._bot.send_alert_message(text, parse_mode=parse_mode)


class ResultAlarmConfHandler(AbstractResultEventHandler):
    async def _handle(self, event: AlarmConfOutboundEvent) -> None:
        message = event.message
        service_name = event.service_name
        state = event.state

        text: str = event.text or '{0} successfully {1}'.format(
            service_name.value, 'enabled' if state else 'disabled'
        )
        await send_text(text=bold(text), message=message, quote=True)
        self._log.info(text)


class ResultDetectionConfHandler(AbstractResultEventHandler):
    async def _handle(self, event: DetectionConfOutboundEvent) -> None:
        message = event.message
        name: str = DETECTION_SWITCH_MAP[event.type]['name'].value
        state = event.state

        text: str = event.text or '{0} successfully {1}'.format(
            name, 'enabled' if state else 'disabled'
        )
        await send_text(text=bold(text), message=message, quote=True)


class ResultTakeSnapshotHandler(AbstractResultEventHandler):
    async def _handle(self, event: SnapshotOutboundEvent) -> None:
        if event.resized:
            await self._send_resized_photo(event)
        else:
            await self._send_full_photo(event)

    async def _send_resized_photo(self, event: SnapshotOutboundEvent) -> None:
        cam = event.cam
        message = event.message

        caption = (
            f'[{cam.conf.description}] '
            f'Snapshot taken on {format_ts(event.create_ts)} '
            f'(snapshot #{event.taken_count}) {cam.hashtag}'
        )
        caption = f'{caption}\n/cmds_{cam.id}, /list_cams'

        self._log.info('Sending resized cam snapshot')
        await self._bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.UPLOAD_PHOTO,
        )
        await message.reply_photo(event.img, caption=caption, quote=True)
        self._log.info('Resized snapshot sent')

    async def _send_full_photo(self, event: SnapshotOutboundEvent) -> None:
        cam = event.cam
        message = event.message

        datetime_str = format_ts(event.create_ts)
        filename = f'Full snapshot {datetime_str}.jpg'
        caption = (
            f'[{cam.description}] Full snapshot on {datetime_str} '
            f'(snapshot #{event.taken_count}) {cam.hashtag}'
        )
        caption = f'{caption}\n/cmds_{cam.id}, /list_cams'

        self._log.info('Sending full cam snapshot')
        await self._bot.send_chat_action(
            chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO
        )
        await message.reply_document(
            document=event.img,
            caption=caption,
            quote=True,
            file_name=filename,
        )
        self._log.info('Full snapshot "%s" sent', filename)
