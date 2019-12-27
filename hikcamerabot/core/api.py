"""Hikvision camera API module."""

import logging
import re
import urllib.parse
from enum import Enum

import requests
import xmltodict

from hikcamerabot.constants import (BAD_RESPONSE_CODES, CONN_TIMEOUT, Http,
                                    DETECTION_SWITCH_MAP, XML_HEADERS,
                                    SWITCH_ENABLED_XML)
from hikcamerabot.decorators import retry
from hikcamerabot.exceptions import (APIError,
                                     APIRequestError,
                                     APIBadResponseCodeError)


class Endpoints(Enum):
    _ISAPI_PREFIX = 'ISAPI'

    PICTURE = "Streaming/channels/102/picture?snapShotImageType=JPEG"
    MOTION_DETECTION = f"{_ISAPI_PREFIX}/System/Video/inputs/channels/1/motionDetection"
    LINE_CROSSING_DETECTION = f"{_ISAPI_PREFIX}/Smart/LineDetection/1"
    INTRUSION_DETECTION = f"{_ISAPI_PREFIX}/Smart/FieldDetection/1"
    ALERT_STREAM = f"{_ISAPI_PREFIX}/Event/notification/alertStream"


class HeaderParsingErrorFilter:
    """Filter out urllib3 Header Parsing Errors due to a urllib3 bug."""

    def filter(self, record):
        """Filter out Header Parsing Errors."""
        return 'Failed to parse headers' not in record.getMessage()


class HikvisionAPI:
    """Hikvision API Class."""

    def __init__(self, conf):
        logging.getLogger('urllib3.connectionpool').addFilter(
            HeaderParsingErrorFilter())
        self._log = logging.getLogger(self.__class__.__name__)
        self._host = conf.host
        self._stream_timeout = conf.stream_timeout

        self._sess = requests.Session()
        self._sess.auth = requests.auth.HTTPDigestAuth(conf.auth.user,
                                                       conf.auth.password)

    def take_snapshot(self):
        """Take snapshot."""
        return self._request(Endpoints.PICTURE.value, stream=True)

    def get_alert_stream(self):
        """Get Alert Streams."""
        return self._request(Endpoints.ALERT_STREAM.value, stream=True,
                             timeout=self._stream_timeout)

    def switch(self, key, enable):
        """Switch method to enable/disable Hikvision functions."""
        endpoint = Endpoints[key.upper()].value
        full_name = DETECTION_SWITCH_MAP[key]['name']
        try:
            is_enabled, xml = self._get_switch_state(key, endpoint)
        except APIRequestError:
            err_msg = f'Failed to get {full_name} state.'
            self._log.error(err_msg)
            raise
        except KeyError as err:
            err_msg = f'Failed to verify API response for {full_name}: {err}'
            self._log.error(err_msg)
            raise APIError(err_msg)

        if is_enabled and enable:
            return f'{full_name} already enabled'
        if not is_enabled and not enable:
            return f'{full_name} already disabled'

        regex = SWITCH_ENABLED_XML.format(r'[a-z]+')
        replace_with = SWITCH_ENABLED_XML.format(
            'true' if enable else 'false')
        xml = re.sub(regex, replace_with, xml)

        try:
            response_xml = self._request(endpoint, headers=XML_HEADERS,
                                         data=xml, method=Http.PUT).text
        except APIRequestError:
            err_msg = 'Failed to {0} {1}.'.format(
                'enable' if enable else 'disable', full_name)
            self._log.error(err_msg)
            raise

        self._parse_response_xml(response_xml)
        return None

    def _parse_response_xml(self, response_xml):
        try:
            xml_dict = xmltodict.parse(response_xml)['ResponseStatus']
            if xml_dict['statusCode'] != 1 and xml_dict['statusString'] != 'OK':
                err_msg = 'Camera returned failed errored XML'
                self._log.error(err_msg)
                raise APIError(err_msg)
        except KeyError as err:
            err_msg = f'Failed to parse response XML: {err}'
            self._log.error(err)
            raise APIError(err_msg)

    def _get_switch_state(self, name, endpoint):
        xml = self._request(endpoint, method=Http.GET).text
        state = xmltodict.parse(xml)[DETECTION_SWITCH_MAP[name]['method']][
            'enabled']
        return state == 'true', xml

    @retry()
    def _request(self, endpoint, data=None, headers=None, stream=False,
                 method=Http.GET, timeout=CONN_TIMEOUT):
        url = urllib.parse.urljoin(self._host, endpoint)
        self._log.debug('%s %s', method, url)
        try:
            response = self._sess.request(method,
                                          url=url,
                                          data=data,
                                          headers=headers,
                                          stream=stream,
                                          timeout=timeout)
        except Exception as err:
            err_msg = 'API encountered an unknown error.'
            self._log.exception(err_msg)
            raise APIRequestError(f'{err_msg}: {err}')
        self._verify_status_code(response)
        return response

    def _verify_status_code(self, response):
        if not response:
            code = response.status_code
            unhandled_code = f'Unhandled response code: {code}'
            err_msg = 'Failed to query API: {0}'.format(
                BAD_RESPONSE_CODES.get(code, unhandled_code).format(response.url))
            self._log.error(err_msg)
            raise APIBadResponseCodeError(err_msg)
