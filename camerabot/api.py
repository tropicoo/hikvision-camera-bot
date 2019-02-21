import logging
import re

import requests
import xmltodict
from requests.auth import HTTPDigestAuth

from camerabot.constants import BAD_RESPONSE_CODES, CONN_TIMEOUT
from camerabot.errors import (APIError,
                              APITakeSnapshotError,
                              APIMotionDetectionSwitchError,
                              APIGetAlertStreamError)


class API:
    def __init__(self, api_conf):
        self._log = logging.getLogger(self.__class__.__name__)
        self._host = api_conf['host']
        self._auth = HTTPDigestAuth(api_conf['auth']['user'],
                                    api_conf['auth']['password'])
        self._endpoints = api_conf['endpoints']
        self._stream_timeout = api_conf['stream_timeout']
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

    def motion_detection_switch(self, enable):
        msg = ''
        endpoint = self._endpoints['motion_detection']
        try:
            is_enabled, xml = self._get_motion_detection_state()
            if is_enabled and enable:
                return '<b>Motion Detection already enabled</b>'
            elif not is_enabled and not enable:
                return '<b>Motion Detection already disabled</b>'

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
            err_msg = 'Failed to {0} motion detection.'.format('enable' if
                                                         enable else 'disable')
            raise APIMotionDetectionSwitchError(err_msg) from err
        except Exception as err:
            err_msg = 'Failed to {0} motion detection.'.format('enable' if
                                                         enable else 'disable')
            self._log.exception(err_msg)
            raise APIMotionDetectionSwitchError(err_msg) from err
        return msg

    def _get_motion_detection_state(self):
        endpoint = self._endpoints['motion_detection']
        try:
            xml = self._query_api(endpoint, method='GET').text
            state = xmltodict.parse(xml)['MotionDetection']['enabled']
            is_enabled = True if state == 'true' else False
        except APIError:
            self._log.error('Failed to get motion detection state.')
            raise
        except KeyError as err:
            err_msg = 'Failed to verify camera response.'
            self._log.exception(err_msg)
            raise APIError(err_msg) from err
        return is_enabled, xml

    def _query_api(self, endpoint, data=None, headers=None, stream=False,
                   method='GET', timeout=CONN_TIMEOUT):
        url = '{0}{1}'.format(self._host, endpoint)
        try:
            response = self._sess.request(method, url=url, auth=self._auth,
                    data=data, headers=headers, stream=stream, timeout=timeout)
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
