from dataclasses import dataclass

from hikcamerabot.clients.hikvision.enums import IrcutFilterType
from hikcamerabot.enums import AlarmType, DetectionType, ServiceType, StreamType
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
    type: DetectionType
    state: bool


@dataclass
class StreamEvent(BaseInboundEvent):
    service_type: ServiceType
    stream_type: StreamType
    state: bool


@dataclass
class AlertConfEvent(BaseInboundEvent):
    service_type: ServiceType
    service_name: AlarmType
    state: bool
