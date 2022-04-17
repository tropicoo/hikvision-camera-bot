"""Hikvision camera API client module."""
import abc
import logging
from typing import Any
from urllib.parse import urljoin

import httpx
from addict import Dict
from tenacity import retry, wait_fixed

from hikcamerabot.clients.hikvision.auth import DigestAuthCached
from hikcamerabot.constants import CONN_TIMEOUT, Http
from hikcamerabot.exceptions import APIBadResponseCodeError, APIRequestError


class AbstractHikvisionAPIClient(metaclass=abc.ABCMeta):

    def __init__(self, conf: Dict) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._conf = conf
        self.host: str = self._conf.host

    @abc.abstractmethod
    async def request(
            self,
            endpoint: str,
            data: Any = None,
            headers: dict = None,
            method: str = Http.GET,
            timeout: float = CONN_TIMEOUT,
    ) -> Any:
        pass


class HikvisionAPIClient(AbstractHikvisionAPIClient):
    """Hikvision API Class."""

    def __init__(self, conf: Dict) -> None:
        super().__init__(conf)
        self.session = httpx.AsyncClient(
            auth=DigestAuthCached(
                username=self._conf.auth.user,
                password=self._conf.auth.password,
            ),
            transport=httpx.AsyncHTTPTransport(verify=False, retries=3),
        )

    @retry(wait=wait_fixed(0.5))
    async def request(self,
                      endpoint: str,
                      data: Any = None,
                      headers: dict = None,
                      method: str = Http.GET,
                      timeout: float = CONN_TIMEOUT,
                      ) -> httpx.Response:
        url = urljoin(self.host, endpoint)
        self._log.debug('Request: %s - %s - %s', method, endpoint, data)
        try:
            response = await self.session.request(
                method,
                url=url,
                data=data,
                headers=headers,
                timeout=timeout,
            )
        except Exception as err:
            err_msg = f'API encountered an unknown error for method {method}, ' \
                      f'endpoint {endpoint}, data {data}'
            self._log.exception(err_msg)
            raise APIRequestError(f'{err_msg}: {err}') from err
        self._verify_status_code(response.status_code)
        return response

    def _verify_status_code(self, status_code: int) -> None:
        if httpx.codes.is_error(status_code):
            err_msg = f'Error during API call: Bad response code {status_code}'
            self._log.error(err_msg)
            raise APIBadResponseCodeError(err_msg)
