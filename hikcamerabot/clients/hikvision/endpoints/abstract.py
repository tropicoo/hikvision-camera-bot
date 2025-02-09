import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx
import xmltodict

from hikcamerabot.clients.hikvision import HikvisionAPIClient
from hikcamerabot.clients.hikvision.enums import EndpointAddr
from hikcamerabot.constants import XML_HEADERS
from hikcamerabot.exceptions import HikvisionAPIError


class AbstractEndpoint(ABC):
    """API Endpoint class.

    Used to decompose API methods since they are too complex to store in one API class.
    """

    _XML_PAYLOAD_TPL: str | None = None

    def __init__(self, api_client: HikvisionAPIClient) -> None:
        self._api_client = api_client
        self._log = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def __call__(self, *args, **kwargs) -> Any:
        """Real API call starts here."""

    async def _get_channel_capabilities(self) -> dict[str, Any]:
        response = await self._api_client.request(
            method='GET',
            endpoint=EndpointAddr.CHANNEL_CAPABILITIES,
            headers=XML_HEADERS,
        )
        return xmltodict.parse(response.text)

    def _validate_xml_response(self, response: httpx.Response) -> None:
        xml_text = response.text
        try:
            xml_dict = xmltodict.parse(xml_text)['ResponseStatus']
            is_err = xml_dict['statusCode'] != 1 and xml_dict['statusString'] != 'OK'
        except KeyError as err:
            err_msg = f'Failed to parse response XML: {err}'
            self._log.error(err)
            self._log.debug(xml_text)
            raise HikvisionAPIError(err_msg) from err
        if is_err:
            err_msg = 'Camera returned failed errored XML'
            self._log.error(err_msg)
            self._log.debug(xml_dict)
            raise HikvisionAPIError(err_msg)
