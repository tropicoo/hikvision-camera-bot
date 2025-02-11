"""Service managers module."""

import logging
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from hikcamerabot.enums import ServiceType, StreamType
from hikcamerabot.services.abstract import AbstractService


class ServiceManager:
    """Service Manager Class. Manages camera abstracted services."""

    def __init__(self) -> None:
        # service type as key e.g. {'stream': {'youtube': <instance>}}
        self._services: defaultdict[Any, dict[Any, AbstractService]] = defaultdict(dict)
        self._log = logging.getLogger(self.__class__.__name__)

    def __repr__(self) -> str:
        return f'<Registered services: {self._services}>'

    def register(self, service_instances: Iterable[AbstractService]) -> None:
        """Register service instances."""
        for svc in service_instances:
            self._services[svc.TYPE][svc.NAME] = svc

    def unregister(self, service_instance: AbstractService) -> None:
        self._services[service_instance.TYPE].pop(service_instance.NAME, None)

    async def start_all(self, only_conf_enabled: bool = False) -> None:
        for service_type_dict in self._services.values():
            for service in service_type_dict.values():
                if only_conf_enabled:
                    if service.enabled_in_conf:
                        await service.start()
                    else:
                        self._log.info(
                            '[%s] Do not start service "%s" - disabled by default',
                            service.cam.id,
                            service,
                        )
                else:
                    await service.start()

    async def stop_all(self) -> None:
        for service_type_dict in self._services.values():
            for service in service_type_dict.values():
                try:
                    await service.stop()
                except Exception as err:
                    self._log.warning(
                        '[%s] Warning while stopping service "%s": %s',
                        service.cam.id,
                        service.NAME.value,
                        err,
                    )

    async def stop(self, service_type: str, service_name: str) -> None:
        await self._services[service_type][service_name].stop()

    async def start(self, service_type: ServiceType, service_name: StreamType) -> None:
        await self._services[service_type][service_name].start()

    def get(
        self, service_type: ServiceType, service_name: StreamType
    ) -> AbstractService:
        return self._services[service_type][service_name]

    def get_all(self) -> list[AbstractService]:
        services = []
        for service_type_dict in self._services.values():
            services.extend(service_type_dict.values())
        return services

    def count(self, stream_type: str | None = None) -> int:
        try:
            return len(self._services[stream_type])
        except KeyError:
            count = 0
            for service_names_dict in self._services.values():
                count += len(service_names_dict)
            return count

    def get_count_per_type(self) -> dict:
        return {name: len(val) for name, val in self._services.items()}
