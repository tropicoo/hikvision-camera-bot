from collections.abc import Callable
from enum import StrEnum, unique


class BaseNonUniqueChoiceStrEnum(StrEnum):
    @classmethod
    def choices(cls) -> frozenset[Callable[[], str]]:
        return frozenset(member.value for member in cls)


@unique
class BaseUniqueChoiceStrEnum(BaseNonUniqueChoiceStrEnum):
    pass


class RtspTransportType(BaseUniqueChoiceStrEnum):
    TCP = 'tcp'
    UDP = 'udp'


class ConfigFile(BaseUniqueChoiceStrEnum):
    MAIN = 'config.json'
    LIVESTREAM = 'livestream_templates.json'
    ENCODING = 'encoding_templates.json'


class PictureType(BaseUniqueChoiceStrEnum):
    ON_ALERT = 'on_alert'
    ON_DEMAND = 'on_demand'


class VideoGifType(BaseUniqueChoiceStrEnum):
    ON_ALERT = 'on_alert'
    ON_DEMAND = 'on_demand'


class EventType(BaseUniqueChoiceStrEnum):
    ALERT_MSG = 'alert_msg'
    ALERT_SNAPSHOT = 'alert_snapshot'
    ALERT_VIDEO = 'alert_video'
    CONFIGURE_ALARM = 'alarm_conf'
    CONFIGURE_DETECTION = 'detection_conf'
    CONFIGURE_IRCUT_FILTER = 'ircut_conf'
    RECORD_VIDEOGIF = 'record_videogif'
    SEND_TEXT = 'send_text'
    STREAM = 'stream'
    TAKE_SNAPSHOT = 'take_snapshot'


class CmdSectionType(BaseUniqueChoiceStrEnum):
    GENERAL = 'General'
    INFRARED = 'Infrared Mode'
    MOTION_DETECTION = 'Motion DetectionType'
    LINE_DETECTION = 'Line Crossing DetectionType'
    INTRUSION_DETECTION = 'Intrusion (Field) DetectionType'
    ALERT_SERVICE = 'Alert Service'
    STREAM_YOUTUBE = 'YouTube StreamType'
    STREAM_TELEGRAM = 'Telegram StreamType'
    STREAM_ICECAST = 'Icecast StreamType'


class AlarmType(BaseUniqueChoiceStrEnum):
    ALARM = 'Alarm'


class ServiceType(BaseUniqueChoiceStrEnum):
    ALARM = 'alarm'
    STREAM = 'stream'
    UPLOAD = 'upload'
    TIMELAPSE = 'timelapse'


class DvrUploadType(BaseUniqueChoiceStrEnum):
    TELEGRAM = 'telegram'


class StreamType(BaseUniqueChoiceStrEnum):
    DVR = 'DVR'
    ICECAST = 'ICECAST'
    SRS = 'SRS'
    TELEGRAM = 'TELEGRAM'
    YOUTUBE = 'YOUTUBE'


class VideoEncoderType(BaseUniqueChoiceStrEnum):
    X264 = 'x264'
    VP9 = 'vp9'
    DIRECT = 'direct'


class DetectionType(BaseUniqueChoiceStrEnum):
    """Detection type/name in config file."""

    MOTION = 'motion_detection'
    LINE = 'line_crossing_detection'
    INTRUSION = 'intrusion_detection'


class DetectionEventName(BaseUniqueChoiceStrEnum):
    """EventType name coming from Hikvision's camera alert stream."""

    INTRUSION = 'fielddetection'
    LINE = 'linedetection'
    MOTION = 'VMD'


class DetectionXMLMethodName(BaseUniqueChoiceStrEnum):
    """Detection XML method name used in API requests to Hikvision camera."""

    INTRUSION = 'FieldDetection'
    LINE = 'LineDetection'
    MOTION = 'MotionDetection'


class DetectionVerboseName(BaseUniqueChoiceStrEnum):
    """Detection verbose name."""

    INTRUSION = 'Intrusion (Field) DetectionType'
    LINE = 'Line Crossing DetectionType'
    MOTION = 'Motion DetectionType'


class FfmpegVideoCodecType(BaseUniqueChoiceStrEnum):
    X264 = 'libx264'
    X265 = 'libx265'
    VP9 = 'vp9'


class FfmpegPixFmt(BaseUniqueChoiceStrEnum):
    YUV420P = 'yuv420p'
    YUV422P = 'yuv422p'
    YUV444P = 'yuv444p'
