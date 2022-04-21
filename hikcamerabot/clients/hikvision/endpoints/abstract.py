import abc
import logging
from typing import Optional

import httpx
import xmltodict
from addict import Dict

from hikcamerabot.clients.hikvision.api_client import (
    AbstractHikvisionAPIClient,
)
from hikcamerabot.clients.hikvision.constants import Endpoint
from hikcamerabot.constants import Http
from hikcamerabot.exceptions import HikvisionAPIError


class AbstractEndpoint(metaclass=abc.ABCMeta):
    _XML_PAYLOAD_TPL: Optional[str] = None
    _XML_HEADERS = {'Content-Type': 'application/xml'}

    def __init__(self, api_client: AbstractHikvisionAPIClient) -> None:
        self._api_client = api_client
        self._log = logging.getLogger(self.__class__.__name__)

    @abc.abstractmethod
    async def __call__(self, *args, **kwargs):
        pass

    async def _get_channel_capabilities(self) -> Dict:
        response_xml = await self._api_client.request(
            endpoint=Endpoint.CHANNEL_CAPABILITIES.value,
            headers=self._XML_HEADERS,
            method=Http.GET,
        )
        return Dict(xmltodict.parse(response_xml.text))

    def _validate_response_xml(self, response_xml: httpx.Response) -> None:
        xml_text = response_xml.text
        try:
            xml_dict = xmltodict.parse(xml_text)['ResponseStatus']
            if xml_dict['statusCode'] != 1 and xml_dict['statusString'] != 'OK':
                err_msg = 'Camera returned failed errored XML'
                self._log.error(err_msg)
                self._log.debug(xml_dict)
                raise HikvisionAPIError(err_msg)
        except KeyError as err:
            err_msg = f'Failed to parse response XML: {err}'
            self._log.error(err)
            self._log.debug(xml_text)
            raise HikvisionAPIError(err_msg)
