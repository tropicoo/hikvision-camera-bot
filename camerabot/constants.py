"""Constants module."""

from collections import namedtuple

IMG = namedtuple('IMG', ('SIZE', 'FORMAT', 'QUALITY'))((1280, 724),
                                                       'JPEG', 90)
BAD_RESPONSE_CODES = {401: 'Got 401: Unauthorized. Wrong credentials?',
                      403: 'Got 403: Forbidden. Wrong URL?\n{0}',
                      404: 'Got 404: URL Not Found\n{0}'}
CONN_TIMEOUT = 5
SEND_TIMEOUT = 300

_STREAMS_ARGS = ('YOUTUBE', 'ICECAST', 'TWITCH')
STREAMS = namedtuple('STREAMS',
                     ('SERVICE_TYPE',) + _STREAMS_ARGS)('stream', *map(lambda x: x.lower(), _STREAMS_ARGS))

ALARMS = namedtuple('ALARM_MAP', ('SERVICE_TYPE', 'ALARM'))('alarm', 'alarm')


# Livestream constants
_ENC_ARGS = ('X264', 'VP9', 'DIRECT')
VIDEO_ENCODERS = namedtuple('ENCODERS', _ENC_ARGS)(*map(lambda x: x.lower(), _ENC_ARGS))
FFMPEG_CMD = 'ffmpeg -loglevel {loglevel} ' \
             '{filter} ' \
             '-rtsp_transport {rtsp_transport_type} ' \
             '-i rtsp://{user}:{pw}@{host}/Streaming/Channels/{channel}/ ' \
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

FFMPEG_CMD_TRANSCODE = {VIDEO_ENCODERS.X264: '-preset {preset} -tune {tune}',
                        VIDEO_ENCODERS.VP9: '-deadline {deadline} -speed {speed}'}

FFMPEG_CMD_TRANSCODE_ICECAST = '-ice_genre "{ice_genre}" -ice_name "{ice_name}" ' \
                               '-ice_description "{ice_description}" ' \
                               '-ice_public {ice_public} -password "{password}" ' \
                               '-content_type "{content_type}"'

FFMPEG_CMD_SCALE_FILTER = '-vf scale={width}:{height},format={format}'
FFMPEG_CMD_NULL_AUDIO = {'filter': '-f lavfi -i anullsrc='
                                   'channel_layout=mono:sample_rate=8000',
                         'map': '-map 0:a -map 1:v',
                         'bitrate': '-b:a 5k'}

# Alert (alarm) constants
DETECTIONS = namedtuple('DETECTIONS', ('MOTION', 'LINE'))('motion_detection',
                                                          'line_crossing_detection')
ALARM_TRIGGERS = (DETECTIONS.MOTION, DETECTIONS.LINE)
DETECTION_REGEX = r'(<\/?eventType>(VMD|linedetection)?){2}'

SWITCH_MAP = {DETECTIONS.MOTION: {'method': 'MotionDetection',
                                  'name': 'Motion Detection',
                                  'event_name': 'VMD'},
              DETECTIONS.LINE: {
                  'method': 'LineDetection',
                  'name': 'Line Crossing Detection',
                  'event_name': 'linedetection'}}

SWITCH_ENABLED_XML = r'<enabled>{0}</enabled>'
XML_HEADERS = {'Content-Type': 'application/xml'}
