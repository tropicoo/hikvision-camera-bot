import logging
import re
from typing import Optional

import xmltodict

from hikcamerabot.clients.hikvision.constants import Endpoints
from hikcamerabot.constants import DETECTION_SWITCH_MAP, Http
from hikcamerabot.exceptions import APIRequestError, HikvisionAPIError


class CameraConfigSwitch:
    SWITCH_ENABLED_XML = r'<enabled>{0}</enabled>'
    XML_HEADERS = {'Content-Type': 'application/xml'}

    def __init__(self, api: 'HikvisionAPI'):
        self._log = logging.getLogger(self.__class__.__name__)
        self._api = api

    async def switch_state(self, trigger: str, enable: bool) -> Optional[str]:
        endpoint = Endpoints[trigger.upper()].value
        full_name = DETECTION_SWITCH_MAP[trigger]['name']
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

        xml = self._prepare_xml(xml, enable)
        try:
            response_xml = await self._api._request(
                endpoint,
                headers=self.XML_HEADERS,
                data=xml,
                method=Http.PUT)
            response_xml = response_xml.text
        except APIRequestError:
            err_msg = 'Failed to {0} {1}.'.format(
                'enable' if enable else 'disable', full_name)
            self._log.error(err_msg)
            raise

        self._parse_response_xml(response_xml)
        return None

    async def _get_switch_state(self, name: str, endpoint: str) -> tuple[
        bool, str]:
        response = await self._api._request(endpoint, method=Http.GET)
        xml = response.text
        xml_dict = xmltodict.parse(xml)
        state = xml_dict[DETECTION_SWITCH_MAP[name]['method']]['enabled']
        return state == 'true', xml

    def _parse_response_xml(self, response_xml: str) -> None:
        try:
            xml_dict = xmltodict.parse(response_xml)['ResponseStatus']
            if xml_dict['statusCode'] != 1 and xml_dict[
                'statusString'] != 'OK':
                err_msg = 'Camera returned failed errored XML'
                self._log.error(err_msg)
                raise HikvisionAPIError(err_msg)
        except KeyError as err:
            err_msg = f'Failed to parse response XML: {err}'
            self._log.error(err)
            raise HikvisionAPIError(err_msg)

    def _prepare_xml(self, xml: str, enable: bool) -> str:
        regex = self.SWITCH_ENABLED_XML.format(r'[a-z]+')
        replace_with = self.SWITCH_ENABLED_XML.format('true' if enable else 'false')
        return re.sub(regex, replace_with, xml)
