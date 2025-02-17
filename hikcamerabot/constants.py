"""Constants module."""

from dataclasses import dataclass
from typing import Final, Literal

from hikcamerabot.enums import (
    DetectionEventName,
    DetectionType,
    DetectionVerboseName,
    DetectionXMLMethodName,
    VideoEncoderType,
)

# /cmds_cam_1 | /cmds_cam_1@SomeNameBot -> cam_1
CMD_CAM_ID_REGEX: Final[str] = r'(cam_[0-9]+)(?:@|$)'

CONN_TIMEOUT: Final[int] = 5
SEND_TIMEOUT: Final[int] = 300

TG_MAX_MSG_SIZE: Final[int] = 4096

TIMELAPSE_STILL_EXT: Final[str] = 'jpg'


@dataclass(frozen=True)
class _Img:
    FORMAT: Literal['JPEG'] = 'JPEG'
    SIZE: tuple[int, int] = (1280, 724)
    QUALITY: int = 60


Img: Final[_Img] = _Img()

FFMPEG_LOG_LEVELS: Final[frozenset[str]] = frozenset(
    ('quiet', 'panic', 'fatal', 'error', 'warning', 'info', 'verbose', 'debug', 'trace')
)

SRS_DOCKER_CONTAINER_NAME: Final[str] = 'hikvision_srs_server'

DAY_HOURS_RANGE: Final[range] = range(24)

FFMPEG_BIN: Final[str] = 'ffmpeg'
_FFMPEG_LOG_LEVEL: Final[str] = '-loglevel {loglevel}'

FFMPEG_CAM_VIDEO_SRC: Final[str] = (
    '"rtsp://{user}:{pw}@{host}:{rtsp_port}/Streaming/Channels/{channel}/"'
)
FFMPEG_SRS_RTMP_VIDEO_SRC: Final[str] = '"rtmp://{ip_address}/live/{livestream_name}"'
FFMPEG_SRS_HLS_VIDEO_SRC: Final[str] = (
    '"http://{ip_address}:8080/hls/live/{livestream_name}.m3u8"'
)

SRS_LIVESTREAM_NAME_TPL: Final[str] = 'livestream_{channel}_{cam_id}'
RTSP_TRANSPORT_TPL: Final[str] = '-rtsp_transport {rtsp_transport_type}'

# Video Gif Command. Hardcoded aac audio to mitigate any issues regarding
# supported formats for mp4 container.
FFMPEG_CMD_VIDEO_GIF: Final[str] = (
    f'{FFMPEG_BIN} {_FFMPEG_LOG_LEVEL} '
    '{rtsp_transport} '
    '-i {video_source} '
    '-c:v copy -c:a aac '
    '-t {rec_time} '
    '{filepath}'
)

FFMPEG_CMD_HLS_VIDEO_GIF: Final[str] = (
    f'{FFMPEG_BIN} {_FFMPEG_LOG_LEVEL} '
    '-live_start_index 0 '
    '-i {video_source} '
    '-c copy '
    '-t {rec_time} '
    '{filepath}'
)

# Livestream constants.
FFMPEG_CMD_SRS: Final[str] = (
    f'{FFMPEG_BIN} {_FFMPEG_LOG_LEVEL} '
    '-reorder_queue_size 1000000 '
    '-buffer_size 1000000 '
    '{filter} '
    '-rtsp_transport {rtsp_transport_type} '
    '-timeout 10000000 '
    f'-i {FFMPEG_CAM_VIDEO_SRC} '
    '{map} '
    '-c:v {vcodec} '
    '{{inner_args}} '
    '-c:a {acodec} {abitrate} {asample_rate} '
    '-f {format} '
    '-flvflags no_duration_filesize '
    '-rtmp_live live '
    '"{{output}}"'
)

FFMPEG_CMD_LIVESTREAM: Final[str] = (
    f'{FFMPEG_BIN} {_FFMPEG_LOG_LEVEL} '
    '{filter} '
    '{rtsp_transport} '
    '-i {video_source} '
    '{map} '
    '-c:v {vcodec} '
    '{{inner_args}} '
    '-c:a {acodec} {abitrate} {asample_rate} '
    '-f {format} '
    '-flvflags no_duration_filesize '
    '-rtmp_live live '
    '"{{output}}"'
)

FFMPEG_CMD_DVR: Final[str] = (
    f'{FFMPEG_BIN} {_FFMPEG_LOG_LEVEL} '
    '{filter} '
    '{rtsp_transport} '
    '-i {video_source} '
    '{map} '
    '-c:v {vcodec} '
    '{{inner_args}} '
    '-c:a {acodec} {abitrate} {asample_rate} '
    '-strftime 1 '
    '-f segment -segment_time {segment_time} -reset_timestamps 1 '
    '"{{output}}"'
)

FFMPEG_CMD_TRANSCODE_GENERAL: Final[str] = (
    '-b:v {average_bitrate} -maxrate {maxrate} '
    '-bufsize {bufsize} '
    '-pass {pass_mode} -pix_fmt {pix_fmt} '
    '-r {framerate} {scale} {{inner_args}}'
)

FFMPEG_CMD_TRANSCODE: Final[dict[VideoEncoderType, str]] = {
    VideoEncoderType.VP9: '-deadline {deadline} -speed {speed}',
    VideoEncoderType.X264: '-preset {preset} -tune {tune}',
}

FFMPEG_CMD_TRANSCODE_ICECAST: Final[str] = (
    '-ice_genre "{ice_genre}" -ice_name "{ice_name}" '
    '-ice_description "{ice_description}" '
    '-ice_public {ice_public} -password "{password}" '
    '-content_type "{content_type}"'
)

FFMPEG_CMD_SCALE_FILTER: Final[str] = '-vf scale={width}:{height},format={format}'
FFMPEG_CMD_NULL_AUDIO: Final[dict[str, str]] = {
    'filter': '-f lavfi -i anullsrc=channel_layout=mono:sample_rate=8000',
    'map': '-map 0:a -map 1:v',
    'bitrate': '-b:a 10k',
}

DETECTION_SWITCH_MAP: Final[
    dict[
        DetectionType,
        dict[str, DetectionEventName | DetectionXMLMethodName | DetectionVerboseName],
    ]
] = {
    DetectionType.MOTION: {
        'method': DetectionXMLMethodName.MOTION,
        'name': DetectionVerboseName.MOTION,
        'event_name': DetectionEventName.MOTION,
    },
    DetectionType.LINE: {
        'method': DetectionXMLMethodName.LINE,
        'name': DetectionVerboseName.LINE,
        'event_name': DetectionEventName.LINE,
    },
    DetectionType.INTRUSION: {
        'method': DetectionXMLMethodName.INTRUSION,
        'name': DetectionVerboseName.INTRUSION,
        'event_name': DetectionEventName.INTRUSION,
    },
}


# TODO: Remove this
PYTHON_LOG_LEVELS: frozenset[str] = frozenset(
    ('DEBUG', 'WARNING', 'INFO', 'ERROR', 'CRITICAL')
)


XML_HEADERS: Final[dict[str, str]] = {'Content-Type': 'application/xml'}
