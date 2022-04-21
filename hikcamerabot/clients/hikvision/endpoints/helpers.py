import logging
import re
from typing import Optional, TYPE_CHECKING

import xmltodict

from hikcamerabot.clients.hikvision.constants import Endpoint
from hikcamerabot.constants import Detection, DETECTION_SWITCH_MAP, Http
from hikcamerabot.exceptions import APIRequestError, HikvisionAPIError


if TYPE_CHECKING:
    from hikcamerabot.clients.hikvision.api_client import AbstractHikvisionAPIClient


class CameraConfigSwitch:
    SWITCH_ENABLED_XML = r'<enabled>{0}</enabled>'
    SWITCH_INFRARED_XML = (
        r'<IrcutFilter>'
        r'<IrcutFilterType>{filter_type}</IrcutFilterType>'
        r'<nightToDayFilterLevel>4</nightToDayFilterLevel>'
        r'<nightToDayFilterTime>5</nightToDayFilterTime>'
        r'</IrcutFilter>'
    )
    XML_HEADERS = {'Content-Type': 'application/xml'}

    def __init__(self, api: 'AbstractHikvisionAPIClient') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._api = api

    async def switch_enabled_state(
        self, trigger: Detection, enable: bool
    ) -> Optional[str]:
        endpoint = Endpoint[trigger.value.upper()].value
        full_name: str = DETECTION_SWITCH_MAP[trigger]['name'].value
        try:
            is_enabled, xml = await self._get_switch_state(trigger, endpoint)
        except APIRequestError:
            err_msg = f'Failed to get {full_name} state.'
            self._log.error(err_msg)
            raise
        except KeyError as err:
            err_msg = f'Failed to verify API response for {full_name}: {err}'
            self._log.error(err_msg)
            raise HikvisionAPIError(err_msg)

        if is_enabled and enable:
            return f'{full_name} already enabled'
        if not is_enabled and not enable:
            return f'{full_name} already disabled'

        xml_payload = self._prepare_xml_payload(xml, enable)
        try:
            response_xml = await self._api.request(
                endpoint, headers=self.XML_HEADERS, data=xml_payload, method=Http.PUT
            )
            response_xml = response_xml.text
        except APIRequestError:
            err_msg = 'Failed to {0} {1}.'.format(
                'enable' if enable else 'disable', full_name
            )
            self._log.error(err_msg)
            raise

        self._parse_response_xml(response_xml)
        return None

    async def _get_switch_state(
        self, name: Detection, endpoint: str
    ) -> tuple[bool, str]:
        response = await self._api.request(endpoint, method=Http.GET)
        xml = response.text
        xml_dict = xmltodict.parse(xml)
        state: str = xml_dict[DETECTION_SWITCH_MAP[name]['method'].value]['enabled']
        return state == 'true', xml

    def _parse_response_xml(self, response_xml: str) -> None:
        try:
            xml_dict = xmltodict.parse(response_xml)['ResponseStatus']
            if xml_dict['statusCode'] != 1 and xml_dict['statusString'] != 'OK':
                err_msg = 'Camera returned failed errored XML'
                self._log.error(err_msg)
                raise HikvisionAPIError(err_msg)
        except KeyError as err:
            err_msg = f'Failed to parse response XML: {err}'
            self._log.error(err)
            raise HikvisionAPIError(err_msg)

    def _prepare_xml_payload(self, xml: str, enable: bool) -> str:
        regex = self.SWITCH_ENABLED_XML.format(r'[a-z]+')
        replace_with = self.SWITCH_ENABLED_XML.format('true' if enable else 'false')
        return re.sub(regex, replace_with, xml)
