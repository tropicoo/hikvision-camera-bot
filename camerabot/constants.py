"""Constants module."""

BAD_RESPONSE_CODES = {401: 'Got 401: Unauthorized. Wrong credentials?',
                      403: 'Got 403: Forbidden. Wrong URL?\n{0}',
                      404: 'Got 404: URL Not Found\n{0}'}
CONF_CAM_ID_REGEX = r'^cam_[0-9]+$'
CMD_CAM_ID_REGEX = r'^.*(?=cam_)'
CONN_TIMEOUT = 5
SEND_TIMEOUT = 300

_STREAMS_ARGS = ('YOUTUBE', 'ICECAST', 'TWITCH')


class _HTTPMethods:
    __slots__ = ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')

    def __init__(self):
        for method in self.__slots__:
            setattr(self, method, method)


class _Alarms:
    __slots__ = ('SERVICE_TYPE', 'ALARM')

    def __init__(self):
        self.SERVICE_TYPE = self.ALARM = 'alarm'


class _Detections:
    __slots__ = ('MOTION', 'LINE')

    def __init__(self):
        self.MOTION = 'motion_detection'
        self.LINE = 'line_crossing_detection'


class _Image:
    __slots__ = ('SIZE', 'FORMAT', 'QUALITY')

    def __init__(self):
        self.SIZE = (1280, 724)
        self.FORMAT = 'JPEG'
        self.QUALITY = 90


class _Streams:
    __slots__ = ('SERVICE_TYPE',) + _STREAMS_ARGS

    def __init__(self):
        self.SERVICE_TYPE = 'stream'
        for arg in _STREAMS_ARGS:
            setattr(self, arg, arg.lower())


class _Encoders:
    __slots__ = ('X264', 'VP9', 'DIRECT')

    def __init__(self):
        for arg in self.__slots__:
            setattr(self, arg, arg.lower())


HTTPMETHODS = _HTTPMethods()
ALARMS = _Alarms()
DETECTIONS = _Detections()
IMG = _Image()
STREAMS = _Streams()
VIDEO_ENCODERS = _Encoders()

# Livestream constants
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
