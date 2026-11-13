import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

from tests.conftest import requires_config

# Service modules load configs on import.
pytestmark = requires_config


def _service(name: str, start: AsyncMock, enabled: bool = True):
    return SimpleNamespace(
        TYPE='stream',
        NAME=name,
        cam=SimpleNamespace(id='cam_2'),
        enabled_in_conf=enabled,
        start=start,
    )


async def test_start_all_continues_after_failing_service():
    from hikcamerabot.services.manager import ServiceManager

    failing = _service('alarm', AsyncMock(side_effect=RuntimeError('403')))
    disabled = _service('dvr', AsyncMock(), enabled=False)
    working = _service('srs', AsyncMock())
    manager = ServiceManager()
    manager.register([failing, disabled, working])

    await manager.start_all(only_conf_enabled=True)

    failing.start.assert_awaited_once()
    disabled.start.assert_not_called()
    working.start.assert_awaited_once()


async def test_alarm_continues_when_camera_does_not_support_trigger():
    from hikcamerabot.enums import DetectionType
    from hikcamerabot.exceptions import ServiceRuntimeError
    from hikcamerabot.services.alarm.camera.alarm import AlarmService

    enabled = {
        'motion_detection': False,
        'line_crossing_detection': True,
        'intrusion_detection': True,
    }
    service = AlarmService.__new__(AlarmService)
    service._log = logging.getLogger('test')
    service.cam = SimpleNamespace(id='cam_2')
    service._conf = SimpleNamespace(
        get_detection_schema_by_type=lambda type_: SimpleNamespace(
            enabled=enabled[type_]
        )
    )

    async def trigger_switch(trigger, state):
        if trigger is DetectionType.LINE:
            raise ServiceRuntimeError('Line Crossing Detection: 403')
        return 'ok'

    service.trigger_switch = AsyncMock(side_effect=trigger_switch)

    await service._enable_triggers_on_camera()

    called = {call.kwargs['trigger'] for call in service.trigger_switch.await_args_list}
    assert called == {DetectionType.LINE, DetectionType.INTRUSION}
