"""HikVision camera API module."""

import logging
import os
import re

import requests
import xmltodict
from requests.auth import HTTPDigestAuth

from camerabot.constants import (BAD_RESPONSE_CODES, CONN_TIMEOUT, SWITCH_MAP,
                                 XML_HEADERS, SWITCH_ENABLED_XML)
from camerabot.exceptions import (APIError,
                                  APIRequestError,
                                  APIBadResponseCodeError)


class APIMethods:

    """RESTful API Methods."""

    GET = 'GET'
    PUT = 'PUT'
    POST = 'POST'
    PATCH = 'PATCH'
    DELETE = 'DELETE'


class API:

    """HikVision API class."""

    def __init__(self, conf):
        self._log = logging.getLogger(self.__class__.__name__)
        self._host = conf['host']
        self._auth = HTTPDigestAuth(conf['auth']['user'],
                                    conf['auth']['password'])
        self._endpoints = conf['endpoints']
        self._stream_timeout = conf['stream_timeout']
        self._xml_headers = XML_HEADERS
        self._sess = requests.Session()

    def take_snapshot(self):
        return self._get(self._endpoints['picture'], stream=True)

    def get_alert_stream(self):
        return self._get(self._endpoints['alert_stream'], stream=True,
                         timeout=self._stream_timeout)

    def switch(self, _type, enable):
        endpoint = self._endpoints[_type]
        name = SWITCH_MAP[_type]['name']

        try:
            is_enabled, xml = self._get_switch_state(_type, endpoint)
        except APIRequestError:
            err_msg = 'Failed to get {0} state.'.format(name)
            self._log.error(err_msg)
            raise
        except KeyError as err:
            err_msg = 'Failed to verify API response for {0}: {1}'.format(
                name, str(err))
            self._log.error(err_msg)
            raise APIError(err_msg)

        if is_enabled and enable:
            return '{0} already enabled'.format(name)
        if not is_enabled and not enable:
            return '{0} already disabled'.format(name)

        regex = SWITCH_ENABLED_XML.format(r'[a-z]+')
        replace_with = SWITCH_ENABLED_XML.format(
            'true' if enable else 'false')
        xml = re.sub(regex, replace_with, xml)

        try:
            response_xml = self._get(endpoint, headers=self._xml_headers,
                                     data=xml, method=APIMethods.PUT).text
        except APIRequestError:
            err_msg = 'Failed to {0} {1}.'.format(
                'enable' if enable else 'disable', name)
            self._log.error(err_msg)
            raise

        try:
            xml_dict = xmltodict.parse(response_xml)['ResponseStatus']
            if xml_dict['statusCode'] != 1 and xml_dict['statusString'] != 'OK':
                err_msg = 'Camera returned failed errored XML'
                self._log.error(err_msg)
                raise APIError(err_msg)
        except KeyError as err:
            err_msg = 'Failed to parse response XML: {0}'.format(str(err))
            self._log.error(err)
            raise APIError(err_msg)

        return None

    def _get_switch_state(self, _type, endpoint):
        xml = self._get(endpoint, method=APIMethods.GET).text
        state = xmltodict.parse(xml)[SWITCH_MAP[_type]['method']]['enabled']
        return state == 'true', xml

    def _get(self, endpoint, data=None, headers=None, stream=False,
             method=APIMethods.GET, timeout=CONN_TIMEOUT):
        url = os.path.join(self._host, endpoint)
        self._log.debug('{0} {1}'.format(method, url))
        try:
            response = self._sess.request(method, url=url, auth=self._auth,
                                          data=data,
                                          headers=headers,
                                          stream=stream,
                                          timeout=timeout)
        except Exception as err:
            err_msg = 'API encountered an unknown error.'
            self._log.exception(err_msg)
            raise APIRequestError('{0}: {1}'.format(err_msg, str(err)))
        self._verify_status_code(response)
        return response

    def _verify_status_code(self, response):
        if not response:
            code = response.status_code
            unhandled_code = 'Unhandled response code: {0}'.format(code)
            err_msg = 'Failed to query API: {0}'.format(
                BAD_RESPONSE_CODES.get(code, unhandled_code).format(response.url))
            self._log.error(err_msg)
            raise APIBadResponseCodeError(err_msg)
