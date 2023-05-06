"""Registry module."""

import logging
from collections import defaultdict
from typing import Iterator, Literal

from hikcamerabot.camera import HikvisionCam

CamRegistryValue = dict[
    Literal['cam', 'cmds', 'cmds_presentation'], HikvisionCam | dict | str
]
CamRegistryType = dict[str, CamRegistryValue]
GroupRegistryValue = dict[str, str | list[HikvisionCam]]
GroupRegistryType = dict[str, GroupRegistryValue]


class CameraRegistry:
    """Registry class with camera meta information."""

    def __init__(self) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._cam_registry: CamRegistryType = {}
        self._group_registry = defaultdict(dict)
        self._group_command_alias: dict[str, str] = {}

    def __repr__(self) -> str:
        return str(self._cam_registry)

    def add(
        self, cam: HikvisionCam, commands: dict, commands_presentation: str
    ) -> None:
        """Add metadata to teh registry."""
        self._cam_registry[cam.id] = {
            'cam': cam,
            'cmds': commands,
            'cmds_presentation': commands_presentation,
        }
        self._add_to_group_registry(cam)

    def _add_to_group_registry(self, cam: HikvisionCam) -> None:
        try:
            key = self._group_command_alias[cam.group]
        except KeyError:
            # Key as group command name.
            key = f'group_{len(self._group_registry) + 1}'

        try:
            self._group_registry[key]['cams'].append(cam)
        except KeyError:
            self._group_command_alias[cam.group] = key
            self._group_registry[key] = {'name': cam.group, 'cams': [cam]}

    def get_commands(self, cam_id: str) -> dict:
        """Get camera commands."""
        return self._cam_registry[cam_id]['cmds']

    def get_commands_presentation(self, cam_id: str) -> dict:
        """Get camera commands presentation string."""
        return self._cam_registry[cam_id]['cmds_presentation']

    def get_instance(self, cam_id: str) -> HikvisionCam:
        return self._cam_registry[cam_id]['cam']

    def get_meta(self, cam_id: str) -> CamRegistryValue:
        return self._cam_registry[cam_id]

    def get_instances(self) -> Iterator[HikvisionCam]:
        return (v['cam'] for v in self._cam_registry.values())

    def get_all(self) -> CamRegistryType:
        """Return raw registry metadata dict."""
        return self._cam_registry

    def count(self) -> int:
        """Get cameras count."""
        return len(self._cam_registry)

    def get_nvr_cameras(self) -> defaultdict[str, list[HikvisionCam]]:
        nvr_cameras: defaultdict[str, list[HikvisionCam]] = defaultdict(list)
        cam: HikvisionCam
        for cam_dict in self._cam_registry.values():
            cam = cam_dict['cam']
            if cam.is_behind_nvr:
                nvr_cameras[cam.host].append(cam)
        return nvr_cameras

    def get_instances_by_group(self, group_name: str) -> list[HikvisionCam]:
        return self._group_registry.get(group_name, [])

    def get_groups_registry(self) -> GroupRegistryType:
        return self._group_registry

    def get_group(self, group_id: str) -> GroupRegistryValue:
        return self._group_registry[group_id]
