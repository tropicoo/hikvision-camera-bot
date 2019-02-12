"""Home Camera Module"""

import logging
import requests
import re
from datetime import datetime
from io import BytesIO
from PIL import Image
from requests.auth import HTTPDigestAuth

from camerabot.constants import (BAD_RESPONSE_CODES, IMG_SIZE, IMG_FORMAT,
                                                               IMG_QUALITY)
from camerabot.errors import HomeCamError, CameraResponseError


class HomeCam:
    """Camera class."""

    def __init__(self, cam_data):
        self._log = logging.getLogger(self.__class__.__name__)
        self.description = cam_data['description']
        self._log.debug('Initializing {0}'.format(self.description))

        self._api_conf = cam_data['api']
        self._auth = HTTPDigestAuth(self._api_conf['auth']['user'],
                                    self._api_conf['auth']['password'])
        self.snapshots_taken = 0

    def take_snapshot(self, resize=False):
        """Takes and returns full or resized snapshot from the camera."""
        url = '{0}{1}'.format(self._api_conf['host'],
                              self._api_conf['endpoints']['picture'])
        self._log.debug('Taking snapshot from {0}'.format(url))
        response = self._query_api(url=url, stream=True, method='GET')
        snapshot_timestamp = int(datetime.now().timestamp())
        self.snapshots_taken += 1
        snapshot = self._resize_snapshot(response.raw) if resize else response.raw
        return snapshot, snapshot_timestamp

    def motion_detection_switch(self, enable=True):
        """Motion Detection Switch."""
        try:
            url = '{0}{1}'.format(self._api_conf['host'],
                                  self._api_conf['endpoints']['motion_detection'])
            headers = {'Content-Type': 'application/xml'}
            xml = self._query_api(url=url, method='GET').text

            string = r'<enabled>{0}</enabled>'
            regex = string.format(r'[a-z]+')
            replace_with = string.format('true' if enable else 'false')
            xml = re.sub(regex, replace_with, xml)
            self._log.debug('{} Motion Detection'.format('Enabling' if enable
                                                         else 'Disabling'))

            self._query_api(url, headers=headers, data=xml, method='PUT')
        except HomeCamError:
            raise
        except Exception as err:
            err_msg = 'Motion Detection Switch encountered an error.'
            self._log.exception(err_msg)
            raise HomeCamError(err_msg) from err

    def _query_api(self, url, data=None, headers=None,
                   stream=False, method='GET'):
        try:
            if method == 'GET':
                response = requests.get(url=url, auth=self._auth, stream=stream)
            elif method == 'POST':
                response = requests.post(url=url, auth=self._auth,
                                         data=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url=url, auth=self._auth, data=data,
                                        headers=headers)
            self._verify_status_code(response)
            return response
        except CameraResponseError as err:
            self._log.error(str(err))
            raise HomeCamError(str(err)) from err
        except Exception as err:
            err_msg = 'Connection to {0} failed.'.format(self.description)
            self._log.error(err_msg)
            raise HomeCamError(err_msg)

    def _resize_snapshot(self, raw_snapshot):
        """Resizes and returns JPEG snapshot."""
        snapshot = Image.open(raw_snapshot)
        resized_snapshot = BytesIO()

        snapshot.resize(IMG_SIZE, Image.ANTIALIAS)
        snapshot.save(resized_snapshot, IMG_FORMAT, quality=IMG_QUALITY)
        resized_snapshot.seek(0)

        self._log.debug("Raw snapshot: {0}, {1}, {2}".format(snapshot.format,
                                                             snapshot.mode,
                                                             snapshot.size))
        self._log.debug("Resized snapshot: {0}".format(IMG_SIZE))
        return resized_snapshot

    def _verify_status_code(self, response):
        if not response:
            code = response.status_code
            unhandled_code = 'Unhandled response code: {0}'
            raise CameraResponseError(BAD_RESPONSE_CODES.get(code,
                             unhandled_code.format(code)).format(response.url))
