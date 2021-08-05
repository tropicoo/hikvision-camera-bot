"""Bot exceptions module."""


class CameraBotError(Exception):
    pass


class ConfigError(Exception):
    pass


class UserAuthError(Exception):
    pass


class HikvisionCamError(Exception):
    pass


class DirectoryWatcherError(Exception):
    pass


class HikvisionAPIError(Exception):
    pass


class APIRequestError(HikvisionAPIError):
    pass


class APIBadResponseCodeError(APIRequestError):
    pass


class ServiceError(Exception):
    pass


class ServiceRuntimeError(ServiceError):
    pass


class ServiceConfigError(ServiceError):
    pass


class ChunkDetectorError(CameraBotError):
    pass


class ChunkLoopError(ServiceError):
    pass
