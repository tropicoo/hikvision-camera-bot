"""Registry module."""

import logging
from typing import Iterator, Union

from hikcamerabot.camera import HikvisionCam

RegistryValue = dict[str, Union[HikvisionCam, dict, str]]
CamRegistryType = dict[str, RegistryValue]


class CameraRegistry:
    """Registry class with camera meta information."""

    def __init__(self) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._registry: CamRegistryType = {}

    def __repr__(self) -> str:
        return str(self._registry)

    def add(self, cam: HikvisionCam, commands: dict, commands_presentation: str) -> None:
        """Add metadata to teh registry."""
        self._registry[cam.id] = {'cam': cam, 'cmds': commands,
                                  'cmds_presentation': commands_presentation}

    def get_commands(self, cam_id: str) -> dict:
        """Get camera commands."""
        return self._registry[cam_id]['cmds']

    def get_commands_presentation(self, cam_id: str) -> dict:
        """Get camera commands presentation string."""
        return self._registry[cam_id]['cmds_presentation']

    def get_instance(self, cam_id: str) -> HikvisionCam:
        return self._registry[cam_id]['cam']

    def get_meta(self, cam_id: str) -> RegistryValue:
        return self._registry[cam_id]

    def get_instances(self) -> Iterator[HikvisionCam]:
        return (v['cam'] for v in self._registry.values())

    def get_all(self) -> CamRegistryType:
        """Return raw registry metadata dict."""
        return self._registry

    def get_count(self) -> int:
        """Get cameras count."""
        return len(self._registry)
