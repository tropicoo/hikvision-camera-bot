"""Constants module."""

CONFIG_FILE = 'config.json'
IMG_SIZE = (1280, 724)
IMG_FORMAT = 'JPEG'
IMG_QUALITY = 90
LOG_LEVELS_STR = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']
BAD_RESPONSE_CODES = {401: 'Got 401: Unauthorized. Wrong credentials?',
                      403: 'Got 403: Forbidden. Wrong URL?\n{0}',
                      404: 'Got 404: URL Not Found\n{0}'}

COMMANDS = {'cmds': 'cmds_{0}',
            'getpic': 'getpic_{0}',
            'getfullpic': 'getfullpic_{0}',
            'md_on': 'mdetection_on_{0}',
            'md_off': 'mdetection_off_{0}',
            'ld_on': 'lndetection_on_{0}',
            'ld_off': 'lndetection_off_{0}',
            'alert_on': 'alert_on_{0}',
            'alert_off': 'alert_off_{0}',
            'yt_on': 'yt_stream_on_{0}',
            'yt_off': 'yt_stream_off_{0}'}

CONN_TIMEOUT = 5
SEND_TIMEOUT = 300

CMD_YT_FFMPEG = 'ffmpeg -loglevel error {filter} -rtsp_transport tcp -i ' \
                'rtsp://{user}:{pw}@{host}/Streaming/Channels /{channel}/ ' \
                '{map} -c:v copy -c:a aac {bitrate} -f flv {url}/{key}'

FFMPEG_NULL_AUDIO = {'filter': '-f lavfi -i anullsrc='
                               'channel_layout=mono:sample_rate=8000',
                     'map': '-map 0:a -map 1:v',
                     'bitrate': '-b:a 5k'}

MOTION_DETECTION = 'motion_detection'
LINE_DETECTION = 'line_crossing_detection'
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