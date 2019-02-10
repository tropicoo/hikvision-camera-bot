"""Bot constants"""

CONFIG_FILE = 'config.json'
IMG_SIZE = (1280, 724)
IMG_FORMAT = 'JPEG'
IMG_QUALITY = 90
LOG_LEVELS_STR = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']
BAD_RESPONSE_CODES = {401: 'Got 401: Unauthorized. Wrong credentials?',
                      403: 'Got 403: Forbidden. Wrong URL?\n{0}',
                      404: 'Got 404: URL Not Found\n{0}'}
