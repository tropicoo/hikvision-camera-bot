"""Bot Errors Module."""


class ConfigError(Exception):
    pass


class UserAuthError(Exception):
    pass


class HomeCamError(Exception):
    pass


class DirectoryWatcherError(Exception):
    pass


class APIError(Exception):
    pass


class APIMotionDetectionSwitchError(APIError):
    pass


class APITakeSnapshotError(APIError):
    pass


class APIGetAlertStreamError(APIError):
    pass
