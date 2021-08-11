"""Constants module."""

import enum

CMD_CAM_ID_REGEX = r'^.*(?=cam_[0-9]+)'
CONN_TIMEOUT = 5
SEND_TIMEOUT = 300

TG_MAX_MSG_SIZE = 4096

FFMPEG_LOG_LEVELS = {'quiet', 'panic', 'fatal', 'error', 'warning',
                     'info', 'verbose', 'debug', 'trace'}
RTSP_TRANSPORT_TYPES = {'tcp', 'udp'}
RTSP_DEFAULT_PORT: int = 554


@enum.unique
class ConfigFile(enum.Enum):
    MAIN = 'config.json'
    LIVESTREAM = 'livestream_templates.json'
    ENCODING = 'encoding_templates.json'

    @classmethod
    def choices(cls) -> frozenset[str]:
        return frozenset(member.value for member in cls)


class VideoGifType:
    ALERT = 'alert'
    REGULAR = 'regular'


class Event:
    ALERT_MSG = 'alert_msg'
    ALERT_SNAPSHOT = 'alert_snapshot'
    ALERT_VIDEO = 'alert_video'
    CONFIGURE_ALARM = 'alarm_conf'
    CONFIGURE_DETECTION = 'detection_conf'
    ERROR_MSG = 'error_message'
    STOP = 'stop'
    STREAM = 'stream'
    STREAM_MSG = 'stream_msg'
    TAKE_SNAPSHOT = 'take_snapshot'
    RECORD_VIDEOGIF = 'record_videogif'


class _HTTPMethod:
    __slots__ = ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')

    def __init__(self):
        for method in self.__slots__:
            setattr(self, method, method)


class Alarm:
    ALARM = 'alarm'
    SERVICE_TYPE = ALARM


@enum.unique
class Detection(enum.Enum):
    MOTION = 'motion_detection'
    LINE = 'line_crossing_detection'
    INTRUSION = 'intrusion_detection'

    @classmethod
    def choices(cls) -> frozenset[str]:
        return frozenset(member.value for member in cls)


class Stream:
    SERVICE_TYPE = 'stream'
    YOUTUBE = 'youtube'
    ICECAST = 'icecast'
    TWITCH = 'twitch'


class VideoEncoder:
    X264 = 'x264'
    VP9 = 'vp9'
    DIRECT = 'direct'


Http = _HTTPMethod()

FFMPEG_BIN = 'ffmpeg'
FFMPEG_VIDEO_SOURCE = '"rtsp://{user}:{pw}@{host}:{rtsp_port}/Streaming/Channels/{channel}/"'
FFMPEG_LOG_LEVEL = '-loglevel {loglevel}'

# VIDEO GIF COMMAND
FFMPEG_VIDEO_GIF_CMD = f'{FFMPEG_BIN} {FFMPEG_LOG_LEVEL} ' \
                       f'-rtsp_transport {{rtsp_transport_type}} ' \
                       f'-i {FFMPEG_VIDEO_SOURCE} -t {{rec_time}}'

# Livestream constants
FFMPEG_CMD = f'{FFMPEG_BIN} {FFMPEG_LOG_LEVEL} ' \
             '{filter} ' \
             '-rtsp_transport {rtsp_transport_type} ' \
             f'-i {FFMPEG_VIDEO_SOURCE} ' \
             '{map} ' \
             '-c:v {vcodec} ' \
             '{{inner_args}} ' \
             '-c:a {acodec} {abitrate} ' \
             '-f {format} ' \
             '{{output}}'

FFMPEG_CMD_TRANSCODE_GENERAL = '-b:v {average_bitrate} -maxrate {maxrate} ' \
                               '-bufsize {bufsize} ' \
                               '-pass {pass_mode} -pix_fmt {pix_fmt} ' \
                               '-r {framerate} {scale} {{inner_args}}'

FFMPEG_CMD_TRANSCODE = {
    VideoEncoder.X264: '-preset {preset} -tune {tune}',
    VideoEncoder.VP9: '-deadline {deadline} -speed {speed}',
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

DETECTION_SWITCH_MAP = {
    Detection.MOTION.value: {
        'method': 'MotionDetection',
        'name': 'Motion Detection',
        'event_name': 'VMD',
    },
    Detection.LINE.value: {
        'method': 'LineDetection',
        'name': 'Line Crossing Detection',
        'event_name': 'linedetection',
    },
    Detection.INTRUSION.value: {
        'method': 'FieldDetection',
        'name': 'Intrusion (Field) Detection',
        'event_name': 'fielddetection',
    },
}
