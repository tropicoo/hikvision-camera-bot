import logging

from hikcamerabot.clients.hikvision.api_client import AbstractHikvisionAPIClient
from hikcamerabot.clients.hikvision.endpoints.endpoints import (
    AlertStreamEndpoint,
    ExposureEndpoint,
    IrcutFilterEndpoint,
    SwitchEndpoint,
    TakeSnapshotEndpoint,
)


class HikvisionAPI:
    """Hikvision API Wrapper. API methods are Endpoint instances."""

    def __init__(self, api_client: AbstractHikvisionAPIClient) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._api_client = api_client

        self.alert_stream = AlertStreamEndpoint(self._api_client)
        self.take_snapshot = TakeSnapshotEndpoint(self._api_client)
        self.set_ircut_filter = IrcutFilterEndpoint(self._api_client)
        self.set_exposure = ExposureEndpoint(self._api_client)
        self.switch = SwitchEndpoint(self._api_client)
