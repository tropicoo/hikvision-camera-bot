"""Image processing module."""

import logging
from io import BytesIO

from PIL import Image, ImageFile

from hikcamerabot.constants import Img
from hikcamerabot.utils.shared import Singleton


class ImageProcessor(metaclass=Singleton):
    """Image Processor Class. Process raw images taken from Hikvision camera."""

    def __init__(self) -> None:
        self._log = logging.getLogger(self.__class__.__name__)

    def resize(self, raw_snapshot: BytesIO) -> BytesIO:
        """Return resized JPEG snapshot."""
        self._log.debug('Resizing snapshot')
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        raw_snapshot_image = Image.open(raw_snapshot)
        resized_snapshot = BytesIO()

        size = self._calculate_size(raw_snapshot_image)
        snapshot: Image.Image = raw_snapshot_image.resize(size, Image.LANCZOS)
        snapshot.save(
            resized_snapshot,
            Img.FORMAT,
            quality=Img.QUALITY,
            optimize=True,
        )
        resized_snapshot.seek(0)

        self._log.debug(
            'Raw snapshot: %s, %s, %s',
            raw_snapshot_image.format,
            raw_snapshot_image.mode,
            raw_snapshot_image.size,
        )
        self._log.debug('Resized snapshot: %s', size)
        return resized_snapshot

    def _calculate_size(self, raw_snapshot_image: Image.Image) -> tuple[int, int]:
        """Make it work correctly for 4x3 cameras by JulyIghor.

        https://github.com/tropicoo/hikvision-camera-bot/issues/122.
        """
        # Calculate new size maintaining aspect ratio
        target_width, target_height = Img.SIZE
        aspect_ratio = raw_snapshot_image.width / raw_snapshot_image.height

        # Decide if the image should be scaled based on the target width or height
        if (
            raw_snapshot_image.width / target_width
            < raw_snapshot_image.height / target_height
        ):
            return int(target_height * aspect_ratio), target_height
        return target_width, int(target_width / aspect_ratio)
