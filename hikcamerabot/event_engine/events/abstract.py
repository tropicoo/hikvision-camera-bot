from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyrogram.types import Message

from hikcamerabot.enums import Event

if TYPE_CHECKING:
    from hikcamerabot.camera import HikvisionCam


@dataclass
class BaseInboundEvent:
    cam: 'HikvisionCam'
    event: Event
    message: Message


@dataclass
class BaseOutboundEvent:
    cam: 'HikvisionCam'
    event: Event
    message: Message | None
