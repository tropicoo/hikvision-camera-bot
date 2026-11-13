"""Hikvision camera API client module."""

import logging
from typing import TYPE_CHECKING, Any, ClassVar, Final
from urllib.parse import urljoin

import httpx
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from hikcamerabot.clients.hikvision.auth import DigestAuthCached
from hikcamerabot.clients.hikvision.enums import AuthType, EndpointAddr
from hikcamerabot.constants import CONN_TIMEOUT
from hikcamerabot.exceptions import (
    APIAuthError,
    APIBadResponseCodeError,
    APIConnectionError,
    APIRequestError,
)

if TYPE_CHECKING:
    # Runtime import causes circular import: config schemas import this package.
    from hikcamerabot.config.schemas.main_config import CamAPISchema

_RETRY_WAIT: Final[float] = 0.5
_RETRY_STOP_AFTER_ATTEMPT: Final[int] = 3


class HikvisionAPIClient:
    """Hikvision API Class."""

    AUTH_CLS: ClassVar[
        dict[AuthType, type[httpx.BasicAuth | httpx.DigestAuth | DigestAuthCached]]
    ] = {
        AuthType.BASIC: httpx.BasicAuth,
        AuthType.DIGEST: httpx.DigestAuth,
        AuthType.DIGEST_CACHED: DigestAuthCached,
    }

    def __init__(self, conf: 'CamAPISchema') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._conf = conf
        self.host = self._conf.host
        self.port = self._conf.port
        self.session = httpx.AsyncClient(
            auth=self.AUTH_CLS[AuthType(self._conf.auth.type)](
                username=self._conf.auth.user,
                password=self._conf.auth.password,
            ),
            transport=httpx.AsyncHTTPTransport(verify=False, retries=3),
        )

    @retry(
        wait=wait_fixed(_RETRY_WAIT),
        stop=stop_after_attempt(_RETRY_STOP_AFTER_ATTEMPT),
        # Repeating a wrong password only gets the user locked on the camera.
        retry=retry_if_not_exception_type(APIAuthError),
        reraise=True,
    )
    async def request(
        self,
        endpoint: EndpointAddr | str,
        data: Any | None = None,
        headers: dict | None = None,
        method: str = 'GET',
        timeout: float = CONN_TIMEOUT,  # noqa: ASYNC109
    ) -> httpx.Response:
        url = urljoin(f'{self.host}:{self.port}', endpoint)
        self._log.debug('Request: %s - %s - %s', method, url, data)
        try:
            response = await self.session.request(
                method,
                url=url,
                data=data,
                headers=headers,
                timeout=timeout,
            )
        except Exception as err:
            is_conn_err = isinstance(err, httpx.TransportError)
            err_msg = (
                f'Camera is unreachable: {method} {url}'
                if is_conn_err
                else f'API request failed: {method} {url}'
            )
            # One line per attempt; full traceback only on DEBUG level.
            self._log.warning('%s: %s: %s', err_msg, err.__class__.__name__, err)
            self._log.debug('Request error traceback, data %s', data, exc_info=True)
            exc_cls = APIConnectionError if is_conn_err else APIRequestError
            raise exc_cls(f'{err_msg}: {err}') from err
        self._validate_response(response)
        return response

    def _validate_response(self, response: httpx.Response) -> None:
        status_code = response.status_code
        if httpx.codes.is_error(status_code):
            err_msg = f'Error during API call: Bad response code {status_code}'
            self._log.error(err_msg)
            self._log.debug(
                'Error response data: %s - %s', response.headers, response.text
            )
            self.raise_for_status_code(status_code)

    @staticmethod
    def raise_for_status_code(status_code: int) -> None:
        """Raise auth error for 401/403 and bad response error for other 4xx/5xx."""
        if not httpx.codes.is_error(status_code):
            return
        exc_cls = (
            APIAuthError
            if status_code in (httpx.codes.UNAUTHORIZED, httpx.codes.FORBIDDEN)
            else APIBadResponseCodeError
        )
        raise exc_cls(
            f'Error during API call: Bad response code {status_code}',
            status_code=status_code,
        )
