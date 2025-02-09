from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pyrogram.enums import ParseMode
from pyrogram.types import Message

from hikcamerabot.enums import (
    AlarmType,
    DetectionType,
    EventType,
    ServiceType,
    StreamType,
)
from hikcamerabot.event_engine.events.abstract import BaseOutboundEvent
from hikcamerabot.utils.file import format_bytes


@dataclass
class FileSizeMixin:
    file_size: int

    def file_size_human(self) -> str:
        return format_bytes(num=self.file_size)


@dataclass
class VideoOutboundEvent(BaseOutboundEvent, FileSizeMixin):
    thumb_path: Path | None
    video_path: Path
    video_duration: int
    video_height: int
    video_width: int
    create_ts: int


@dataclass
class AlertSnapshotOutboundEvent(BaseOutboundEvent, FileSizeMixin):
    img: BytesIO
    ts: int
    resized: bool
    detection_type: DetectionType
    alert_count: int


@dataclass
class SnapshotOutboundEvent(BaseOutboundEvent, FileSizeMixin):
    img: BytesIO
    create_ts: int
    taken_count: int
    resized: bool
    message: Message


@dataclass
class SendTextOutboundEvent:
    event: EventType
    text: str
    parse_mode: ParseMode = ParseMode.HTML
    message: Message | None = None


@dataclass
class AlarmConfOutboundEvent(BaseOutboundEvent):
    service_type: ServiceType
    service_name: AlarmType
    state: bool
    message: Message
    text: str | None = None


@dataclass
class StreamOutboundEvent(BaseOutboundEvent):
    service_type: ServiceType
    stream_type: StreamType
    state: bool
    message: Message
    text: str | None = None


@dataclass
class DetectionConfOutboundEvent(BaseOutboundEvent):
    type: DetectionType
    state: bool
    message: Message
    text: str | None = None
