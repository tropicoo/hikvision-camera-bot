"""Home Camera Module"""

import logging
import requests
from datetime import datetime
from io import BytesIO
from PIL import Image
from requests.auth import HTTPDigestAuth

from camerabot.constants import (BAD_RESPONSE_CODES, IMG_SIZE, IMG_FORMAT,
                                                               IMG_QUALITY)
from camerabot.errors import HomeCamError, CameraResponseError


class HomeCam:
    """Camera class."""

    def __init__(self, api, user, password, description):
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.debug('Initializing {0}'.format(description))

        self._api = api
        self._user = user
        self._password = password
        self.description = description
        self.snapshots_taken = 0

    def take_snapshot(self, resize=False):
        """Takes and returns full or resized snapshot from the camera."""
        self._log.debug('Taking snapshot from {0}'.format(self._api))
        try:
            auth = HTTPDigestAuth(self._user, self._password)
            response = requests.get(self._api, auth=auth, stream=True)
            self._verify_status_code(response)
        except requests.exceptions.ConnectionError as err:
            err_msg = 'Connection to {0} failed.'.format(self.description)
            self._log.error(err_msg)
            raise HomeCamError(err_msg)
        except CameraResponseError as err:
            self._log.error(str(err))
            raise HomeCamError from err

        snapshot_timestamp = int(datetime.now().timestamp())
        self.snapshots_taken += 1
        snapshot = self._resize_snapshot(response.raw) if resize else response.raw

        return snapshot, snapshot_timestamp

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
            raise CameraResponseError(
                BAD_RESPONSE_CODES.get(code, unhandled_code.format(code)).
                format(response.url))
