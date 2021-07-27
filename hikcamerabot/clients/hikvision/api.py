"""Hikvision camera API client module."""

import logging
from io import BytesIO
from typing import Any, AsyncGenerator, Optional
from urllib.parse import urljoin

import httpx
from addict import Addict
from tenacity import retry, wait_fixed

from hikcamerabot.clients.hikvision.auth import DigestAuthCached
from hikcamerabot.clients.hikvision.constants import Endpoints
from hikcamerabot.clients.hikvision.helpers import CameraConfigSwitch
from hikcamerabot.constants import CONN_TIMEOUT, Http
from hikcamerabot.exceptions import APIBadResponseCodeError, APIRequestError


class HikvisionAPI:
    """Hikvision API Class."""

    def __init__(self, conf: Addict):
        self._log = logging.getLogger(self.__class__.__name__)
        self.__conf = conf
        self._host = self.__conf.host
        self._stream_timeout = self.__conf.stream_timeout

        self._session = httpx.AsyncClient(
            auth=DigestAuthCached(
                username=self.__conf.auth.user,
                password=self.__conf.auth.password,
            ),
            transport=httpx.AsyncHTTPTransport(verify=False, retries=3),
        )
        self._switch = CameraConfigSwitch(self)

    async def take_snapshot(self) -> BytesIO:
        """Take snapshot."""
        response = await self._request(Endpoints.PICTURE.value)
        file_ = BytesIO(response.content)
        file_.seek(0)
        return file_

    async def alert_stream(self) -> AsyncGenerator:
        """Get Alert Stream text chunks."""
        url = urljoin(self._host, Endpoints.ALERT_STREAM.value)
        async with self._session.stream('GET', url, timeout=self._stream_timeout) \
                as response:
            async for chunk in response.aiter_text():
                yield chunk

    async def switch(self, trigger: str, enable: bool) -> Optional[str]:
        """Switch method to enable/disable Hikvision functions."""
        return await self._switch.switch_state(trigger, enable)

    @retry(wait=wait_fixed(0.5))
    async def _request(self,
                       endpoint: str,
                       data: Any = None,
                       headers: dict = None,
                       method: str = Http.GET,
                       timeout: float = CONN_TIMEOUT,
                       ) -> httpx.Response:
        url = urljoin(self._host, endpoint)
        try:
            response = await self._session.request(
                method,
                url=url,
                data=data,
                headers=headers,
                timeout=timeout,
            )
        except Exception as err:
            err_msg = 'API encountered an unknown error.'
            self._log.exception(err_msg)
            raise APIRequestError(f'{err_msg}: {err}') from err
        self._verify_status_code(response.status_code)
        return response

    def _verify_status_code(self, status_code: int) -> None:
        if httpx.codes.is_error(status_code):
            err_msg = f'Error during API call: Bad response code {status_code}'
            self._log.error(err_msg)
            raise APIBadResponseCodeError(err_msg)
