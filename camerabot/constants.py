"""Constants module."""

IMG_SIZE = (1280, 724)
IMG_FORMAT = 'JPEG'
IMG_QUALITY = 90
BAD_RESPONSE_CODES = {401: 'Got 401: Unauthorized. Wrong credentials?',
                      403: 'Got 403: Forbidden. Wrong URL?\n{0}',
                      404: 'Got 404: URL Not Found\n{0}'}
CONN_TIMEOUT = 5
SEND_TIMEOUT = 300


class StreamMap:
    type = 'stream'
    YOUTUBE = 'youtube'
    ICECAST = 'icecast'
    TWITCH = 'twitch'


class AlarmMap:
    ALARM = type = 'alarm'


# Livestream constants
FFMPEG_CMD = 'ffmpeg -loglevel {loglevel} ' \
             '{filter} ' \
             '-rtsp_transport {rtsp_transport_type} ' \
             '-i rtsp://{user}:{pw}@{host}/Streaming/Channels/{channel}/ ' \
             '{map} ' \
             '-c:v {vcodec} ' \
             '{inner_args} ' \
             '-c:a {acodec} {abitrate} ' \
             '-f {format} ' \
             '{{output}}'
FFMPEG_CMD_TRANSCODE_GENERAL = '-b:v {average_bitrate} -maxrate {maxrate} ' \
                               '-bufsize {bufsize} ' \
                               '-pass {pass_mode} -pix_fmt {pix_fmt} ' \
                               '-r {framerate} {scale} {{inner_args}}'
_FFMPEG_CMD_TRANSCODE_YT = '-preset {preset} -tune {tune}'
_FFMPEG_CMD_TRANSCODE_ICECAST = '-ice_genre "{ice_genre}" -ice_name "{ice_name}" ' \
                                '-ice_description "{ice_description}" ' \
                                '-ice_public {ice_public} -password "{password}" ' \
                                '-content_type "{content_type}" ' \
                                '-threads {threads} -preset {preset} -deadline {deadline} -speed {speed}'
FFMPEG_CMD_SCALE_FILTER = '-vf scale={width}:{height},format={format}'
FFMPEG_CMD_NULL_AUDIO = {'filter': '-f lavfi -i anullsrc='
                               'channel_layout=mono:sample_rate=8000',
                     'map': '-map 0:a -map 1:v',
                     'bitrate': '-b:a 5k'}
FFMPEG_TRANSCODE_MAP = {StreamMap.YOUTUBE: _FFMPEG_CMD_TRANSCODE_YT,
                        StreamMap.ICECAST: _FFMPEG_CMD_TRANSCODE_ICECAST}
LIVESTREAM_DIRECT = 'direct'
LIVESTREAM_TRANSCODE = 'transcode'

# Alert (alarm) constants
MOTION_DETECTION = 'motion_detection'
LINE_DETECTION = 'line_crossing_detection'
ALARM_TRIGGERS = (MOTION_DETECTION, LINE_DETECTION)
DETECTION_REGEX = r'(<\/?eventType>(VMD|linedetection)?){2}'

SWITCH_MAP = {MOTION_DETECTION: {'method': 'MotionDetection',
                                 'name': 'Motion Detection',
                                 'event_name': 'VMD'},
              LINE_DETECTION: {
                  'method': 'LineDetection',
                  'name': 'Line Crossing Detection',
                  'event_name': 'linedetection'}}

SWITCH_ENABLED_XML = r'<enabled>{0}</enabled>'
XML_HEADERS = {'Content-Type': 'application/xml'}
