from hikcamerabot.enums import BaseUniqueChoiceStrEnum


class AuthType(BaseUniqueChoiceStrEnum):
    BASIC = 'basic'
    DIGEST = 'digest'
    DIGEST_CACHED = 'digest_cached'


class EndpointAddr(BaseUniqueChoiceStrEnum):
    ALERT_STREAM = 'ISAPI/Event/notification/alertStream'
    CHANNEL_CAPABILITIES = 'ISAPI/Image/channels/1/capabilities'
    EXPOSURE = 'ISAPI/Image/channels/1/exposure'
    IRCUT_FILTER = 'ISAPI/Image/channels/1/ircutFilter'
    INTRUSION_DETECTION = 'ISAPI/Smart/FieldDetection/1'
    LINE_CROSSING_DETECTION = 'ISAPI/Smart/LineDetection/1'
    MOTION_DETECTION = 'ISAPI/System/Video/inputs/channels/1/motionDetection'
    PICTURE = 'ISAPI/Streaming/channels/{channel}/picture?snapShotImageType=JPEG'


class IrcutFilterType(BaseUniqueChoiceStrEnum):
    AUTO = 'auto'
    DAY = 'day'
    NIGHT = 'night'


class ExposureType(BaseUniqueChoiceStrEnum):
    MANUAL = 'manual'


class OverexposeSuppressType(BaseUniqueChoiceStrEnum):
    AUTO = 'AUTO'
    MANUAL = 'MANUAL'


class OverexposeSuppressEnabledType(BaseUniqueChoiceStrEnum):
    TRUE = 'true'
    FALSE = 'false'
