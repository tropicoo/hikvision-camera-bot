"""Registry module."""

import logging


class CameraMetaRegistry:
    """Registry class with camera meta information."""

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        self._registry = {}

    def __repr__(self):
        return str(self._registry)

    def add(self, cam_id, commands, conf):
        """Add metadata to teh registry."""
        self._registry[cam_id] = {'conf': conf, 'cmds': commands}

    def get_conf(self, cam_id):
        """Get camera config."""
        return self._registry[cam_id]['conf']

    def get_commands(self, cam_id):
        """Get camera commands."""
        return self._registry[cam_id]['cmds']

    def get_all(self):
        """Return raw registry metadata dict."""
        return self._registry

    def get_count(self):
        """Get cameras count."""
        return len(self._registry)
