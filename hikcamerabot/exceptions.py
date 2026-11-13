"""Bot exceptions module."""


class CameraBotError(Exception):
    pass


class ConfigError(Exception):
    pass


class UserAuthError(Exception):
    pass


class HikvisionCamError(Exception):
    pass


class HikvisionAPIError(Exception):
    pass


class APIRequestError(HikvisionAPIError):
    pass


class APIConnectionError(APIRequestError):
    """Camera is unreachable: no route, connection refused or timeout."""


class APIBadResponseCodeError(APIRequestError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class APIAuthError(APIBadResponseCodeError):
    """Camera rejected user/password or the user has no rights (401/403)."""


class ServiceError(Exception):
    pass


class ServiceRuntimeError(ServiceError):
    pass


class ServiceConfigError(ServiceError):
    pass


class AlarmEventChunkDetectorError(CameraBotError):
    pass


class ChunkLoopError(ServiceError):
    pass
