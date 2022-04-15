"""Constants module."""

import enum

from typing import Union

CMD_CAM_ID_REGEX = r'^.*(?=cam_[0-9]+)'
CONN_TIMEOUT = 5
SEND_TIMEOUT = 300

TG_MAX_MSG_SIZE = 4096

FFMPEG_LOG_LEVELS = frozenset(['quiet', 'panic', 'fatal', 'error', 'warning',
                               'info', 'verbose', 'debug', 'trace'])
RTSP_DEFAULT_PORT = 554


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
    ALERT = 'alert'
    REGULAR = 'regular'


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


class ImgType:
    FORMAT = 'JPEG'
    SIZE = (1280, 724)
    QUALITY = 60


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


class _HTTPMethod:
    __slots__ = ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')

    def __init__(self) -> None:
        for method in self.__slots__:
            setattr(self, method, method)


class Alarm(_BaseNonUniqueEnum):
    ALARM = 'alarm'


class Detection(_BaseUniqueEnum):
    """Detection type/name in config file."""

    MOTION = 'motion_detection'
    LINE = 'line_crossing_detection'
    INTRUSION = 'intrusion_detection'


class ServiceType(_BaseUniqueEnum):
    ALARM = 'alarm'
    STREAM = 'stream'
    UPLOAD = 'upload'


class DvrUploadType(_BaseUniqueEnum):
    TELEGRAM = 'telegram'


class Stream(_BaseUniqueEnum):
    DVR = 'dvr'
    ICECAST = 'icecast'
    SRS = 'srs'
    TELEGRAM = 'telegram'
    YOUTUBE = 'youtube'


class VideoEncoder(_BaseUniqueEnum):
    X264 = 'x264'
    VP9 = 'vp9'
    DIRECT = 'direct'


Http = _HTTPMethod()

_FFMPEG_BIN = 'ffmpeg'
_FFMPEG_LOG_LEVEL = '-loglevel {loglevel}'
FFMPEG_CAM_VIDEO_SOURCE = '"rtsp://{user}:{pw}@{host}:{rtsp_port}/Streaming/Channels/{channel}/"'
FFMPEG_SRS_VIDEO_SOURCE = '"rtmp://hikvision_srs_server/live/{livestream_name}"'
SRS_LIVESTREAM_NAME_TPL = 'livestream_{channel}_{cam_id}'
RTSP_TRANSPORT_TPL = '-rtsp_transport {rtsp_transport_type}'

# Video Gif Command. Hardcoded aac audio to mitigate any issues regarding
# supported formats for mp4 container.
FFMPEG_CMD_VIDEO_GIF = f'{_FFMPEG_BIN} {_FFMPEG_LOG_LEVEL} ' \
                       '{rtsp_transport} ' \
                       '-i {video_source} ' \
                       f'-c:v copy -c:a aac ' \
                       f'-t {{rec_time}}'

# Livestream constants.
FFMPEG_CMD_SRS = f'{_FFMPEG_BIN} {_FFMPEG_LOG_LEVEL} ' \
                 '-reorder_queue_size 1000000 ' \
                 '-buffer_size 1000000 ' \
                 '{filter} ' \
                 '-rtsp_transport {rtsp_transport_type} ' \
                 '-stimeout 10000000 ' \
                 f'-i {FFMPEG_CAM_VIDEO_SOURCE} ' \
                 '{map} ' \
                 '-c:v {vcodec} ' \
                 '{{inner_args}} ' \
                 '-c:a {acodec} {abitrate} {asample_rate} ' \
                 '-f {format} ' \
                 '-flvflags no_duration_filesize ' \
                 '-rtmp_live live ' \
                 '"{{output}}"'

FFMPEG_CMD_LIVESTREAM = f'{_FFMPEG_BIN} {_FFMPEG_LOG_LEVEL} ' \
                        '{filter} ' \
                        '{rtsp_transport} ' \
                        '-i {video_source} ' \
                        '{map} ' \
                        '-c:v {vcodec} ' \
                        '{{inner_args}} ' \
                        '-c:a {acodec} {abitrate} {asample_rate} ' \
                        '-f {format} ' \
                        '-flvflags no_duration_filesize ' \
                        '-rtmp_live live ' \
                        '"{{output}}"'

FFMPEG_CMD_DVR = f'{_FFMPEG_BIN} {_FFMPEG_LOG_LEVEL} ' \
                 '{filter} ' \
                 '{rtsp_transport} ' \
                 '-i {video_source} ' \
                 '{map} ' \
                 '-c:v {vcodec} ' \
                 '{{inner_args}} ' \
                 '-c:a {acodec} {abitrate} {asample_rate} ' \
                 '-strftime 1 ' \
                 '-f segment -segment_time {segment_time} -reset_timestamps 1 ' \
                 '"{{output}}"'

FFMPEG_CMD_TRANSCODE_GENERAL = '-b:v {average_bitrate} -maxrate {maxrate} ' \
                               '-bufsize {bufsize} ' \
                               '-pass {pass_mode} -pix_fmt {pix_fmt} ' \
                               '-r {framerate} {scale} {{inner_args}}'

FFMPEG_CMD_TRANSCODE: dict[VideoEncoder, str] = {
    VideoEncoder.DIRECT: '',
    VideoEncoder.VP9: '-deadline {deadline} -speed {speed}',
    VideoEncoder.X264: '-preset {preset} -tune {tune}',
}

FFMPEG_CMD_TRANSCODE_ICECAST = '-ice_genre "{ice_genre}" -ice_name "{ice_name}" ' \
                               '-ice_description "{ice_description}" ' \
                               '-ice_public {ice_public} -password "{password}" ' \
                               '-content_type "{content_type}"'

FFMPEG_CMD_SCALE_FILTER = '-vf scale={width}:{height},format={format}'
FFMPEG_CMD_NULL_AUDIO = {
    'filter': '-f lavfi -i anullsrc='
              'channel_layout=mono:sample_rate=8000',
    'map': '-map 0:a -map 1:v',
    'bitrate': '-b:a 10k',
}


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


DETECTION_SWITCH_MAP: dict[Detection, dict[str, Union[DetectionEventName,
                                                      DetectionXMLMethodName,
                                                      DetectionVerboseName]]] = \
    {
        Detection.MOTION: {
            'method': DetectionXMLMethodName.MOTION,
            'name': DetectionVerboseName.MOTION,
            'event_name': DetectionEventName.MOTION,
        },
        Detection.LINE: {
            'method': DetectionXMLMethodName.LINE,
            'name': DetectionVerboseName.LINE,
            'event_name': DetectionEventName.LINE,
        },
        Detection.INTRUSION: {
            'method': DetectionXMLMethodName.INTRUSION,
            'name': DetectionVerboseName.INTRUSION,
            'event_name': DetectionEventName.INTRUSION,
        },
    }
