"""Bot Errors Module"""


class ConfigError(Exception):
    pass


class UserAuthError(Exception):
    pass


class HomeCamError(Exception):
    pass


class CameraResponseError(Exception):
    pass


class DirectoryWatcherError(Exception):
    pass
