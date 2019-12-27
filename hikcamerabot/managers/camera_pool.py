class CameraPoolManager:
    """Pool class for containing all camera instances."""

    def __init__(self):
        self._instances = {}

    def __repr__(self):
        return '<{0} id={1}>: {2}'.format(self.__class__.__name__, id(self),
                                          repr(self._instances))

    def __str__(self):
        return str(self._instances)

    def add(self, cam_id, commands, instance):
        self._instances[cam_id] = {'instance': instance,
                                   'commands': commands}

    def get_instance(self, cam_id):
        return self._instances[cam_id]['instance']

    def get_instances(self):
        return [x['instance'] for x in self._instances.values()]

    def get_commands(self, cam_id):
        return self._instances[cam_id]['commands']

    def get_all(self):
        return self._instances

    def get_count(self):
        return len(self._instances)
