import re
from typing import Optional

from hikcamerabot.constants import (
    DETECTION_SWITCH_MAP,
)
from hikcamerabot.enums import Detection, DetectionEventName
from hikcamerabot.exceptions import AlarmEventChunkDetectorError


class AlarmEventChunkDetector:
    """Detect trigger chunk from alarm/alert stream."""

    DETECTION_REGEX = re.compile(
        fr'^<eventType>('
        fr'{DetectionEventName.MOTION.value}|'
        fr'{DetectionEventName.LINE.value}|'
        fr'{DetectionEventName.INTRUSION.value})<',
        re.MULTILINE,
    )
    DETECTION_KEY_GROUP = 1

    @classmethod
    def detect_chunk(cls, chunk: str) -> Optional[Detection]:
        """Detect chunk in regard of `DETECTION_REGEX` string and return
        detection key.

        :param chunk: string, one line from alert stream.
        """
        match = cls.DETECTION_REGEX.search(chunk)
        if not match:
            return None

        event_name = match.group(cls.DETECTION_KEY_GROUP)
        for key, inner_map in DETECTION_SWITCH_MAP.items():
            if inner_map['event_name'].value == event_name:
                return key
        else:
            raise AlarmEventChunkDetectorError(
                f'Unknown alert stream event {event_name}'
            )


class CameraNvrChannelNameDetector:
    DETECTION_REGEX = re.compile(
        r'<channelName>(.*)</channelName>',
        re.MULTILINE,
    )
    DETECTION_KEY_GROUP = 1

    @classmethod
    def detect_channel_name(cls, chunk: str) -> str | None:
        match = cls.DETECTION_REGEX.search(chunk)
        return match.group(cls.DETECTION_KEY_GROUP) if match else None
