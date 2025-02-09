from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyrogram.types import Message

from hikcamerabot.enums import EventType

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam


@dataclass
class BaseInboundEvent:
    cam: 'HikvisionCam'
    event: EventType
    message: Message


@dataclass
class BaseOutboundEvent:
    cam: 'HikvisionCam'
    event: EventType
    message: Message | None
