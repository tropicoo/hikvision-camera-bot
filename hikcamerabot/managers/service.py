"""Service Manager Module."""

import logging
from collections import defaultdict

from hikcamerabot.exceptions import HikvisionCamError


class ServiceManager:
    """Service Manager Class."""

    def __init__(self):
        # service type as key e.g. {'stream': {'youtube': <instance>}}
        self._log = logging.getLogger(self.__class__.__name__)
        self._services = defaultdict(dict)

    def __repr__(self):
        return f'<Registered services: {self._services}>'

    def register_services(self, service_instances):
        """Register service instances."""
        for svc in service_instances:
            self._services[svc.type][svc.name] = svc

    def unregister_service(self, service_instance):
        self._services[service_instance.type].pop(service_instance.name, None)

    def start_services(self, enabled_in_conf=False):
        for service_type_dict in self._services.values():
            for service in service_type_dict.values():
                if enabled_in_conf:
                    if service.is_enabled_in_conf():
                        service.start()
                    else:
                        self._log.info('Do not starting service "%s" - '
                                       'disabled by default', service)
                else:
                    service.start()

    def stop_services(self):
        for service_type_dict in self._services.values():
            for service in service_type_dict.values():
                try:
                    service.stop()
                except Exception as err:
                    self._log.warning('Warning while stopping service "%s": '
                                      '%s', service.name, err)

    def stop_service(self, service_type, service_name):
        self._services[service_type][service_name].stop()

    def start_service(self, service_type, service_name):
        self._services[service_type][service_name].start()

    def get_service(self, service_type, service_name):
        return self._services[service_type][service_name]

    def get_services(self):
        services = []
        for service_type_dict in self._services.values():
            services.extend(service_type_dict.values())
        return services

    def get_count(self, stream_type=None):
        try:
            return len(self._services[stream_type])
        except KeyError:
            count = 0
            for service_names_dict in self._services.values():
                count += len(service_names_dict)
            return count

    def get_count_per_type(self):
        return {name: len(val) for name, val in self._services.items()}
