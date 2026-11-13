import pytest

from hikcamerabot.clients.github.version_checker import BotVersion
from hikcamerabot.enums import DetectionType
from hikcamerabot.services.alarm.camera.chunk import (
    AlarmEventChunkDetector,
    CameraNvrChannelNameDetector,
)

CHUNK_TPL = """--boundary
Content-Type: application/xml; charset="UTF-8"

<EventNotificationAlert version="2.0">
<ipAddress>192.168.1.10</ipAddress>
<channelID>1</channelID>
<channelName>{channel}</channelName>
<eventType>{event}</eventType>
<eventState>active</eventState>
</EventNotificationAlert>
"""


@pytest.mark.parametrize(
    ('event', 'expected'),
    [
        ('VMD', DetectionType.MOTION),
        ('linedetection', DetectionType.LINE),
        ('fielddetection', DetectionType.INTRUSION),
        ('videoloss', None),
    ],
)
def test_detect_chunk(event, expected):
    chunk = CHUNK_TPL.format(event=event, channel='Front door')
    assert AlarmEventChunkDetector.detect_chunk(chunk) == expected


def test_detect_nvr_channel_name():
    chunk = CHUNK_TPL.format(event='VMD', channel='Front door')
    # The first matching tag is used.
    assert CameraNvrChannelNameDetector.detect_channel_name(chunk) == '1'
    assert CameraNvrChannelNameDetector.detect_channel_name('<eventType/>') is None


@pytest.mark.parametrize(
    ('current', 'latest', 'expected'),
    [('2.0', '2.0', False), ('2.0', '2.1', True), ('2.0.1', '2.0', False)],
)
def test_bot_version(current, latest, expected):
    assert BotVersion(current=current, latest=latest).has_new_version() is expected
