from dataclasses import dataclass
from io import BytesIO
from typing import Optional

from pyrogram.types import Message

from hikcamerabot.constants import Alarm, Detection, Event, ServiceType, Stream
from hikcamerabot.event_engine.events.abstract import BaseOutboundEvent


@dataclass
class VideoOutboundEvent(BaseOutboundEvent):
    thumb_path: Optional[str]
    video_path: str
    video_duration: int
    video_height: int
    video_width: int


@dataclass
class AlertSnapshotOutboundEvent(BaseOutboundEvent):
    img: BytesIO
    ts: int
    resized: bool
    detection_type: Detection
    alert_count: int


@dataclass
class SnapshotOutboundEvent(BaseOutboundEvent):
    img: BytesIO
    create_ts: int
    taken_count: int
    resized: bool
    message: Message


@dataclass
class SendTextOutboundEvent:
    event: Event
    text: str
    parse_mode: str = 'HTML'
    message: Optional[Message] = None


@dataclass
class AlarmConfOutboundEvent(BaseOutboundEvent):
    service_type: ServiceType
    service_name: Alarm
    switch: bool
    message: Message
    text: Optional[str] = None


@dataclass
class StreamOutboundEvent(BaseOutboundEvent):
    service_type: ServiceType
    stream_type: Stream
    switch: bool
    message: Message
    text: Optional[str] = None


@dataclass
class DetectionConfOutboundEvent(BaseOutboundEvent):
    type: Detection
    switch: bool
    message: Message
    text: Optional[str] = None
