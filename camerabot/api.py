"""HikVision camera API module."""
import logging
import os
import re

import requests
import xmltodict
from requests.auth import HTTPDigestAuth

from camerabot.constants import BAD_RESPONSE_CODES, CONN_TIMEOUT, SWITCH_MAP
from camerabot.exceptions import (APIError,
                                  APITakeSnapshotError,
                                  APIMotionDetectionSwitchError,
                                  APIGetAlertStreamError)


class API:
    def __init__(self, conf):
        self._log = logging.getLogger(self.__class__.__name__)
        self._host = conf['host']
        self._auth = HTTPDigestAuth(conf['auth']['user'],
                                    conf['auth']['password'])
        self._endpoints = conf['endpoints']
        self._stream_timeout = conf['stream_timeout']
        self._xml_headers = {'Content-Type': 'application/xml'}
        self._sess = requests.Session()

    def take_snapshot(self):
        endpoint = self._endpoints['picture']
        try:
            response = self._query_api(endpoint, stream=True)
        except APIError as err:
            err_msg = 'Failed to take snapshot'
            self._log.error(err_msg)
            raise APITakeSnapshotError(err_msg) from err
        return response

    def get_alert_stream(self):
        endpoint = self._endpoints['alert_stream']
        try:
            response = self._query_api(endpoint, stream=True,
                                       timeout=self._stream_timeout)
        except APIError as err:
            err_msg = 'Failed to get Alert Stream'
            self._log.error(err_msg)
            raise APIGetAlertStreamError(err_msg) from err
        return response

    def switch(self, _type, enable):
        msg = ''
        endpoint = self._endpoints[_type]
        name = SWITCH_MAP[_type]['name']
        try:
            is_enabled, xml = self._get_switch_state(_type, name, endpoint)
            if is_enabled and enable:
                return '{0} already enabled'.format(name)
            if not is_enabled and not enable:
                return '{0} already disabled'.format(name)

            string = r'<enabled>{0}</enabled>'
            regex = string.format(r'[a-z]+')
            replace_with = string.format('true' if enable else 'false')
            xml = re.sub(regex, replace_with, xml)
            response_xml = self._query_api(endpoint, headers=self._xml_headers,
                                           data=xml, method='PUT').text
            xml_dict = xmltodict.parse(response_xml)['ResponseStatus']
            if xml_dict['statusCode'] != 1 and xml_dict['statusString'] != 'OK':
                err_msg = 'Camera returned failed errored XML.'
                self._log.error(err_msg)
                raise APIError(err_msg)

        except APIError as err:
            err_msg = 'Failed to {0} {1}.'.format(
                'enable' if enable else 'disable', name)
            raise APIMotionDetectionSwitchError(err_msg) from err
        except Exception as err:
            err_msg = 'Failed to {0} {1}.'.format(
                'enable' if enable else 'disable', name)
            self._log.exception(err_msg)
            raise APIMotionDetectionSwitchError(err_msg) from err
        return msg

    def _get_switch_state(self, _type, name, endpoint):
        try:
            xml = self._query_api(endpoint, method='GET').text
            state = xmltodict.parse(xml)[SWITCH_MAP[_type]['method']]['enabled']
            is_enabled = state == 'true'
        except APIError:
            self._log.error('Failed to get {0} state.'.format(name))
            raise
        except KeyError as err:
            err_msg = 'Failed to verify camera response.'
            self._log.exception(err_msg)
            raise APIError(err_msg) from err
        return is_enabled, xml

    def _query_api(self, endpoint, data=None, headers=None, stream=False,
                   method='GET', timeout=CONN_TIMEOUT):
        url = '{0}'.format(os.path.join(self._host, endpoint))
        try:
            response = self._sess.request(method, url=url, auth=self._auth,
                                          data=data,
                                          headers=headers,
                                          stream=stream,
                                          timeout=timeout)
            self._verify_status_code(response)
        except APIError:
            raise
        except Exception as err:
            err_msg = 'API encountered an unknown error.'
            self._log.error(err_msg)
            raise APIError(err_msg) from err
        return response

    def _verify_status_code(self, response):
        if not response:
            code = response.status_code
            unhandled_code = 'Unhandled response code: {0}'.format(code)
            err_msg = BAD_RESPONSE_CODES.get(code, unhandled_code).format(
                response.url)
            self._log.error(err_msg)
            raise APIError(err_msg)
