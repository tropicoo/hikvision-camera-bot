"""Base Service Module."""
import abc
import logging


class BaseService(metaclass=abc.ABCMeta):
    """Base Service class."""

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)

    @abc.abstractmethod
    def start(self):
        pass

    @abc.abstractmethod
    def stop(self):
        pass

    @abc.abstractmethod
    def is_started(self):
        pass

    @abc.abstractmethod
    def is_enabled_in_conf(self):
        pass


class ServiceController:
    """Service Controller class."""

    def __init__(self):
        self._services = []

    def __repr__(self):
        return '<Registered services: {0}>'.format(self._services)

    def register_service(self, service_instance):
        if service_instance not in self._services:
            self._services.append(service_instance)

    def unregister_service(self, service_instance):
        self._services.remove(service_instance)

    def start_services(self, enabled_in_conf=False):
        for service in self._services:
            if enabled_in_conf:
                if service.is_enabled_in_conf():
                    service.start()
            else:
                service.start()

    def stop_services(self):
        for service in self._services:
            service.stop()

    def get_services(self):
        return self._services

    def get_count(self):
        return len(self._services)
