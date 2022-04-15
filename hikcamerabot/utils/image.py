"""Image processing module."""

import logging
from io import BytesIO

from PIL import Image

from hikcamerabot.constants import ImgType
from hikcamerabot.utils.utils import Singleton


class ImageProcessor(metaclass=Singleton):
    """Image Processor Class.

    Process raw images taken from Hikvision camera.
    """

    def __init__(self) -> None:
        """Constructor."""
        self._log = logging.getLogger(self.__class__.__name__)

    def resize(self, raw_snapshot: BytesIO) -> BytesIO:
        """Return resized JPEG snapshot."""
        self._log.debug('Resizing snapshot')
        raw_snapshot = Image.open(raw_snapshot)
        resized_snapshot = BytesIO()

        snapshot: Image.Image = raw_snapshot.resize(ImgType.SIZE, Image.ANTIALIAS)
        snapshot.save(resized_snapshot, ImgType.FORMAT, quality=ImgType.QUALITY,
                      optimize=True)
        resized_snapshot.seek(0)

        self._log.debug('Raw snapshot: %s, %s, %s', raw_snapshot.format,
                        raw_snapshot.mode, raw_snapshot.size)
        self._log.debug('Resized snapshot: %s', ImgType.SIZE)
        return resized_snapshot
