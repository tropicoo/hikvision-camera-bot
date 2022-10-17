from io import BytesIO
from typing import AsyncGenerator, Optional
from urllib.parse import urljoin

import httpx
from addict import Dict

from hikcamerabot.clients.hikvision.endpoints.abstract import AbstractEndpoint
from hikcamerabot.clients.hikvision.endpoints.config_switch import CameraConfigSwitch
from hikcamerabot.clients.hikvision.enums import (
    EndpointAddr,
    ExposureType,
    IrcutFilterType,
    OverexposeSuppressEnabledType,
    OverexposeSuppressType,
)
from hikcamerabot.constants import CONN_TIMEOUT, Detection
from hikcamerabot.exceptions import APIRequestError


class IrcutFilterEndpoint(AbstractEndpoint):
    _XML_PAYLOAD_TPL = (
        '<IrcutFilter>'
        '<IrcutFilterType>{filter_type}</IrcutFilterType>'
        '<nightToDayFilterLevel>{night_to_day_filter_level}</nightToDayFilterLevel>'
        '<nightToDayFilterTime>{night_to_day_filter_time}</nightToDayFilterTime>'
        '</IrcutFilter>'
    )

    async def __call__(self, filter_type: IrcutFilterType) -> None:
        current_capabilities = await self._get_channel_capabilities()
        try:
            response = await self._api_client.request(
                endpoint=EndpointAddr.IRCUT_FILTER,
                headers=self._XML_HEADERS,
                data=self._build_payload(filter_type, current_capabilities),
                method='PUT',
            )
        except APIRequestError:
            self._log.error(
                'Failed to set \'%s\' IrcutFilterType (Day/Night)', filter_type.value
            )
            raise
        self._validate_xml_response(response)

    def _build_payload(
        self, filter_type: IrcutFilterType, current_capabilities: Dict
    ) -> str:
        level: str = (
            current_capabilities.ImageChannel.IrcutFilter.nightToDayFilterLevel['#text']
        )
        time: str = current_capabilities.ImageChannel.IrcutFilter.nightToDayFilterTime[
            '#text'
        ]
        return self._XML_PAYLOAD_TPL.format(
            filter_type=filter_type.value,
            night_to_day_filter_level=level,
            night_to_day_filter_time=time,
        )


class ExposureEndpoint(AbstractEndpoint):
    _XML_PAYLOAD_TPL = (
        '<Exposure>'
        '<ExposureType>{exposure_type}</ExposureType>'
        '<OverexposeSuppress>'
        '<enabled>{overexposure_enabled}</enabled>'
        '<Type>{overexposure_suppress_type}</Type>'
        '<DistanceLevel>{distance_level}</DistanceLevel>'
        '</OverexposeSuppress>'
        '</Exposure>'
    )

    async def __call__(
        self,
        exposure_type: ExposureType = None,
        overexpose_suppress_enabled: OverexposeSuppressEnabledType = None,
        overexposure_suppress_type: OverexposeSuppressType = None,
        distance_level: int = None,
    ) -> None:
        kwargs = {
            'exposure_type': exposure_type,
            'overexpose_suppress_enabled': overexpose_suppress_enabled,
            'overexposure_suppress_type': overexposure_suppress_type,
            'distance_level': distance_level,
        }
        kwargs_len = len(kwargs)
        filtered_kwargs = Dict({k: v for k, v in kwargs if v is not None})

        current_capabilities = None
        if len(filtered_kwargs) != kwargs_len:
            current_capabilities = await self._get_channel_capabilities()
        try:
            response = await self._api_client.request(
                endpoint=EndpointAddr.IRCUT_FILTER,
                headers=self._XML_HEADERS,
                data=self._build_payload(filtered_kwargs, current_capabilities),
                method='PUT',
            )
        except APIRequestError:
            self._log.error('Failed to set Exposure')
            raise
        self._validate_xml_response(response)

    def _build_payload(self, kwargs: Dict, current_capabilities: Optional[Dict]) -> str:
        return self._XML_PAYLOAD_TPL.format(
            exposure_type=kwargs.get(
                'exposure_type',
                current_capabilities.exposure_type,
            ),
            overexpose_suppress_enabled=kwargs.get(
                'overexpose_suppress_enabled',
                current_capabilities.overexpose_suppress_enabled,
            ),
            overexposure_suppress_type=kwargs.get(
                'overexposure_suppress_type',
                current_capabilities.overexposure_suppress_type,
            ),
            distance_level=kwargs.get(
                'distance_level',
                current_capabilities.distance_level,
            ),
        )


class TakeSnapshotEndpoint(AbstractEndpoint):
    async def __call__(self, channel: int) -> BytesIO:
        endpoint_str: str = EndpointAddr.PICTURE.value.format(channel=channel)
        response = await self._api_client.request(endpoint=endpoint_str)
        return self._response_to_bytes(response)

    def _response_to_bytes(self, response: httpx.Response) -> BytesIO:
        file_ = BytesIO(response.content)
        file_.seek(0)
        return file_


class AlertStreamEndpoint(AbstractEndpoint):
    async def __call__(self) -> AsyncGenerator[str, None]:
        # TODO: Rewrite this.
        method = 'GET'
        url = urljoin(
            f'{self._api_client.host}:{self._api_client.port}',
            EndpointAddr.ALERT_STREAM.value,
        )
        timeout = httpx.Timeout(CONN_TIMEOUT, read=300)
        response: httpx.Response
        self._log.debug('Alert Stream Request: %s - %s', method, url)
        async with self._api_client.session.stream(
            method, url, timeout=timeout
        ) as response:
            chunk: str
            async for chunk in response.aiter_text():
                yield chunk


class SwitchEndpoint(AbstractEndpoint):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._switch = CameraConfigSwitch(api_client=self._api_client)

    async def __call__(self, trigger: Detection, state: bool) -> Optional[str]:
        """Switch method to enable/disable Hikvision functions.

        :param state: Boolean value indicating on/off switch state.
        """
        return await self._switch.switch_enabled_state(trigger, state)
