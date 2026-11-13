"""Camera `ResponseStatus` XML check."""

from typing import Any


def is_ok_status(response_status: dict[str, Any]) -> bool:
    """Check parsed `ResponseStatus`: OK is `statusCode` 1 or `statusString` "OK".

    XML values are strings, so `statusCode` must not be compared with int `1`.
    Raise `KeyError` when the camera returned something unexpected.
    """
    status_code = str(response_status['statusCode']).strip()
    status_string = str(response_status['statusString']).strip()
    return status_code == '1' or status_string.upper() == 'OK'
