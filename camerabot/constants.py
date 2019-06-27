"""Constants module."""

IMG_SIZE = (1280, 724)
IMG_FORMAT = 'JPEG'
IMG_QUALITY = 90
LOG_LEVELS_STR = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']
BAD_RESPONSE_CODES = {401: 'Got 401: Unauthorized. Wrong credentials?',
                      403: 'Got 403: Forbidden. Wrong URL?\n{0}',
                      404: 'Got 404: URL Not Found\n{0}'}
CONN_TIMEOUT = 5
SEND_TIMEOUT = 300

# Livestream constants
CMD_YT_FFMPEG_CMD = 'ffmpeg -loglevel {{loglevel}} {{filter}} -rtsp_transport tcp -i ' \
    'rtsp://{{user}}:{{pw}}@{{host}}/Streaming/Channels/{{channel}}/ {{map}} ' \
    '{inner_cmd} -c:a aac {{bitrate}} ' \
    '-f flv {{url}}/{{key}}'
_CMD_YT_DIRECT_FFMPEG = '-c:v copy'
_CMD_YT_TRANSCODE_FFMPEG = '-c:v libx264 -pix_fmt {pix_fmt} -preset {preset} ' \
                           '-maxrate {maxrate} -bufsize {bufsize} ' \
                           '-tune {tune} {scale} -r {framerate} -g {group}'
FFMPEG_SCALE_FILTER = '-vf scale={width}:{height},format={format}'
FFMPEG_NULL_AUDIO = {'filter': '-f lavfi -i anullsrc='
                               'channel_layout=mono:sample_rate=8000',
                     'map': '-map 0:a -map 1:v',
                     'bitrate': '-b:a 5k'}
LIVESTREAM_DIRECT = 'direct'
LIVESTREAM_TRANSCODE = 'transcode'
LIVESTREAM_YT_CMD_MAP = {LIVESTREAM_DIRECT: _CMD_YT_DIRECT_FFMPEG,
                         LIVESTREAM_TRANSCODE: _CMD_YT_TRANSCODE_FFMPEG}


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
