import logging

from hikcamerabot.clients.hikvision import HikvisionAPIClient
from hikcamerabot.clients.hikvision.endpoints.endpoints import (
    AlertStreamEndpoint,
    ExposureEndpoint,
    IrcutFilterEndpoint,
    SwitchEndpoint,
    TakeSnapshotEndpoint,
)


class HikvisionAPI:
    """Hikvision API Wrapper. API methods are Endpoint instances."""

    def __init__(self, api_client: HikvisionAPIClient) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._api_client = api_client

        self.alert_stream = AlertStreamEndpoint(api_client)
        self.take_snapshot = TakeSnapshotEndpoint(api_client)
        self.set_ircut_filter = IrcutFilterEndpoint(api_client)
        self.set_exposure = ExposureEndpoint(api_client)
        self.switch = SwitchEndpoint(api_client)
