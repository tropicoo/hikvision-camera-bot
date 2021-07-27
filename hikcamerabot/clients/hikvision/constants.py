from enum import Enum


class Endpoints(Enum):
    PICTURE = 'ISAPI/Streaming/channels/102/picture?snapShotImageType=JPEG'
    MOTION_DETECTION = 'ISAPI/System/Video/inputs/channels/1/motionDetection'
    LINE_CROSSING_DETECTION = 'ISAPI/Smart/LineDetection/1'
    INTRUSION_DETECTION = 'ISAPI/Smart/FieldDetection/1'
    ALERT_STREAM = 'ISAPI/Event/notification/alertStream'
