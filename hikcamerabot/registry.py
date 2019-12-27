import logging


class CameraRegistry:
    """Registry class with camera meta information."""

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        self._registry = {}

    def __repr__(self):
        return str(self._registry)

    def add(self, cam_id, commands, conf):
        self._registry[cam_id] = {'conf': conf,
                                  'cmds': commands}

    def get_conf(self, cam_id):
        return self._registry[cam_id]['conf']

    def get_commands(self, cam_id):
        return self._registry[cam_id]['cmds']

    def get_all(self):
        return self._registry

    def get_count(self):
        return len(self._registry)
