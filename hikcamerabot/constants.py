"""Constants module."""

from hikcamerabot.enums import (
    Detection,
    DetectionEventName,
    DetectionVerboseName,
    DetectionXMLMethodName,
    VideoEncoder,
)

# /cmds_cam_1 | /cmds_cam_1@SomeNameBot -> cam_1
CMD_CAM_ID_REGEX = r'(cam_[0-9]+)(?:@|$)'

CONN_TIMEOUT = 5
SEND_TIMEOUT = 300

TG_MAX_MSG_SIZE = 4096


class Img:
    FORMAT = 'JPEG'
    SIZE = (1280, 724)
    QUALITY = 60


FFMPEG_LOG_LEVELS = frozenset(
    ['quiet', 'panic', 'fatal', 'error', 'warning', 'info', 'verbose', 'debug', 'trace']
)

SRS_DOCKER_CONTAINER_NAME = 'hikvision_srs_server'

_FFMPEG_BIN = 'ffmpeg'
_FFMPEG_LOG_LEVEL = '-loglevel {loglevel}'

FFMPEG_CAM_VIDEO_SRC = (
    '"rtsp://{user}:{pw}@{host}:{rtsp_port}/Streaming/Channels/{channel}/"'
)
FFMPEG_SRS_RTMP_VIDEO_SRC = (
    f'"rtmp://{SRS_DOCKER_CONTAINER_NAME}/live/{{livestream_name}}"'
)
FFMPEG_SRS_HLS_VIDEO_SRC = '"http://{ip_address}:8080/hls/live/{livestream_name}.m3u8"'

SRS_LIVESTREAM_NAME_TPL = 'livestream_{channel}_{cam_id}'
RTSP_TRANSPORT_TPL = '-rtsp_transport {rtsp_transport_type}'

# Video Gif Command. Hardcoded aac audio to mitigate any issues regarding
# supported formats for mp4 container.
FFMPEG_CMD_VIDEO_GIF = (
    f'{_FFMPEG_BIN} {_FFMPEG_LOG_LEVEL} '
    '{rtsp_transport} '
    '-i {video_source} '
    '-c:v copy -c:a aac '
    '-t {rec_time} '
    '{filepath}'
)

FFMPEG_CMD_HLS_VIDEO_GIF = (
    f'{_FFMPEG_BIN} {_FFMPEG_LOG_LEVEL} '
    '-live_start_index 0 '
    '-i {video_source} '
    '-c copy '
    '-t {rec_time} '
    '{filepath}'
)

# Livestream constants.
FFMPEG_CMD_SRS = (
    f'{_FFMPEG_BIN} {_FFMPEG_LOG_LEVEL} '
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

FFMPEG_CMD_LIVESTREAM = (
    f'{_FFMPEG_BIN} {_FFMPEG_LOG_LEVEL} '
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

FFMPEG_CMD_DVR = (
    f'{_FFMPEG_BIN} {_FFMPEG_LOG_LEVEL} '
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

FFMPEG_CMD_TRANSCODE_GENERAL = (
    '-b:v {average_bitrate} -maxrate {maxrate} '
    '-bufsize {bufsize} '
    '-pass {pass_mode} -pix_fmt {pix_fmt} '
    '-r {framerate} {scale} {{inner_args}}'
)

FFMPEG_CMD_TRANSCODE: dict[VideoEncoder, str] = {
    VideoEncoder.DIRECT: '',
    VideoEncoder.VP9: '-deadline {deadline} -speed {speed}',
    VideoEncoder.X264: '-preset {preset} -tune {tune}',
}

FFMPEG_CMD_TRANSCODE_ICECAST = (
    '-ice_genre "{ice_genre}" -ice_name "{ice_name}" '
    '-ice_description "{ice_description}" '
    '-ice_public {ice_public} -password "{password}" '
    '-content_type "{content_type}"'
)

FFMPEG_CMD_SCALE_FILTER = '-vf scale={width}:{height},format={format}'
FFMPEG_CMD_NULL_AUDIO = {
    'filter': '-f lavfi -i anullsrc=' 'channel_layout=mono:sample_rate=8000',
    'map': '-map 0:a -map 1:v',
    'bitrate': '-b:a 10k',
}

DETECTION_SWITCH_MAP: dict[
    Detection,
    dict[str, DetectionEventName | DetectionXMLMethodName | DetectionVerboseName],
] = {
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
