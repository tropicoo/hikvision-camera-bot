import enum


class _BaseNonUniqueEnum(enum.Enum):
    @classmethod
    def choices(cls) -> frozenset[str]:
        return frozenset(member.value for member in cls)


@enum.unique
class _BaseUniqueEnum(_BaseNonUniqueEnum):
    pass


class RtspTransportType(_BaseUniqueEnum):
    TCP = 'tcp'
    UDP = 'udp'


class ConfigFile(_BaseUniqueEnum):
    MAIN = 'config.json'
    LIVESTREAM = 'livestream_templates.json'
    ENCODING = 'encoding_templates.json'


class VideoGifType(_BaseUniqueEnum):
    ON_ALERT = 'on_alert'
    ON_DEMAND = 'on_demand'


class Event(_BaseUniqueEnum):
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


class CmdSectionType(_BaseUniqueEnum):
    general = 'General'
    infrared = 'Infrared Mode'
    motion_detection = 'Motion Detection'
    line_detection = 'Line Crossing Detection'
    intrusion_detection = 'Intrusion (Field) Detection'
    alert_service = 'Alert Service'
    stream_youtube = 'YouTube Stream'
    stream_telegram = 'Telegram Stream'
    stream_icecast = 'Icecast Stream'


class Alarm(_BaseNonUniqueEnum):
    ALARM = 'Alarm'


class ServiceType(_BaseUniqueEnum):
    ALARM = 'alarm'
    STREAM = 'stream'
    UPLOAD = 'upload'


class DvrUploadType(_BaseUniqueEnum):
    TELEGRAM = 'telegram'


class Stream(_BaseUniqueEnum):
    DVR = 'DVR'
    ICECAST = 'ICECAST'
    SRS = 'SRS'
    TELEGRAM = 'TELEGRAM'
    YOUTUBE = 'YOUTUBE'


class VideoEncoder(_BaseUniqueEnum):
    X264 = 'x264'
    VP9 = 'vp9'
    DIRECT = 'direct'


class Detection(_BaseUniqueEnum):
    """Detection type/name in config file."""

    MOTION = 'motion_detection'
    LINE = 'line_crossing_detection'
    INTRUSION = 'intrusion_detection'


class DetectionEventName(_BaseUniqueEnum):
    """Event name coming from Hikvision's camera alert stream."""

    INTRUSION = 'fielddetection'
    LINE = 'linedetection'
    MOTION = 'VMD'


class DetectionXMLMethodName(_BaseUniqueEnum):
    """Detection XML method name used in API requests to Hikvision camera."""

    INTRUSION = 'FieldDetection'
    LINE = 'LineDetection'
    MOTION = 'MotionDetection'


class DetectionVerboseName(_BaseUniqueEnum):
    """Detection verbose name."""

    INTRUSION = 'Intrusion (Field) Detection'
    LINE = 'Line Crossing Detection'
    MOTION = 'Motion Detection'
