"""Registry module."""

import logging
from typing import Iterator, Union

from addict import Addict

from hikcamerabot.camera import HikvisionCam

RegistryValue = dict[str, Union[Addict, dict]]


class CameraRegistry:
    """Registry class with camera meta information."""

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        self._registry: dict[str, RegistryValue] = {}

    def __repr__(self) -> str:
        return str(self._registry)

    def add(self, cam_id: str, cam, commands: dict) -> None:
        """Add metadata to teh registry."""
        self._registry[cam_id] = {'cam': cam, 'cmds': commands}

    def get_commands(self, cam_id: str) -> dict:
        """Get camera commands."""
        return self._registry[cam_id]['cmds']

    def get_instance(self, cam_id: str):
        return self._registry[cam_id]['cam']

    def get_meta(self, cam_id: str) -> dict[
        str, Union[Addict, HikvisionCam, str]]:
        return self._registry[cam_id]

    def get_instances(self) -> Iterator[HikvisionCam]:
        return (v['cam'] for v in self._registry.values())

    def get_all(self) -> dict:
        """Return raw registry metadata dict."""
        return self._registry

    def get_count(self) -> int:
        """Get cameras count."""
        return len(self._registry)
