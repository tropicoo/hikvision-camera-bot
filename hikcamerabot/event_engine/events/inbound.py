from dataclasses import dataclass

from hikcamerabot.clients.hikvision.enums import IrcutFilterType
from hikcamerabot.enums import Alarm, Detection, ServiceType, Stream
from hikcamerabot.event_engine.events.abstract import BaseInboundEvent


@dataclass
class IrcutConfEvent(BaseInboundEvent):
    filter_type: IrcutFilterType


@dataclass
class GetPicEvent(BaseInboundEvent):
    resize: bool


@dataclass
class GetVideoEvent(BaseInboundEvent):
    rewind: bool


@dataclass
class DetectionConfEvent(BaseInboundEvent):
    type: Detection
    state: bool


@dataclass
class StreamEvent(BaseInboundEvent):
    service_type: ServiceType
    stream_type: Stream
    state: bool


@dataclass
class AlertConfEvent(BaseInboundEvent):
    service_type: ServiceType
    service_name: Alarm
    state: bool
