"""Hikvision camera API client module."""

import logging
from typing import Any, ClassVar, Final
from urllib.parse import urljoin

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from hikcamerabot.clients.hikvision.auth import DigestAuthCached
from hikcamerabot.clients.hikvision.enums import AuthType, EndpointAddr
from hikcamerabot.config.schemas.main_config import CamAPISchema
from hikcamerabot.constants import CONN_TIMEOUT
from hikcamerabot.exceptions import APIBadResponseCodeError, APIRequestError

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

    def __init__(self, conf: CamAPISchema) -> None:
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
            err_msg = (
                f'API encountered an unknown error for method {method}, '
                f'url {url}, data {data}'
            )
            self._log.exception(err_msg)
            raise APIRequestError(f'{err_msg}: {err}') from err
        self._validate_response(response)
        return response

    def _validate_response(self, response: httpx.Response) -> None:
        if httpx.codes.is_error(response.status_code):
            err_msg = f'Error during API call: Bad response code {response.status_code}'
            self._log.error(err_msg)
            self._log.debug(
                'Error response data: %s - %s', response.headers, response.text
            )
            raise APIBadResponseCodeError(err_msg)
