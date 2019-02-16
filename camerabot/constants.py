"""Bot constants"""

CONFIG_FILE = 'config.json'
IMG_SIZE = (1280, 724)
IMG_FORMAT = 'JPEG'
IMG_QUALITY = 90
LOG_LEVELS_STR = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']
BAD_RESPONSE_CODES = {401: 'Got 401: Unauthorized. Wrong credentials?',
                      403: 'Got 403: Forbidden. Wrong URL?\n{0}',
                      404: 'Got 404: URL Not Found\n{0}'}

COMMANDS = {'getpic': 'getpic_{0}',
            'getfullpic': 'getfullpic_{0}',
            'md_on': 'mdetection_on_{0}',
            'md_off': 'mdetection_off_{0}',
            'alert_on': 'alert_on_{0}',
            'alert_off': 'alert_off_{0}'}

TIMEOUT = 5
