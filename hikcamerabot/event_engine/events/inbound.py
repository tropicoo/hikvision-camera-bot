from dataclasses import dataclass

from hikcamerabot.clients.hikvision.constants import IrcutFilterType
from hikcamerabot.constants import Alarm, Detection, ServiceType, Stream
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
    switch: bool


@dataclass
class StreamEvent(BaseInboundEvent):
    service_type: ServiceType
    stream_type: Stream
    switch: bool


@dataclass
class AlertConfEvent(BaseInboundEvent):
    service_type: ServiceType
    service_name: Alarm
    switch: bool
