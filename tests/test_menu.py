import inspect
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.conftest import requires_config

pytestmark = requires_config

TELEGRAM_CALLBACK_DATA_LIMIT = 64


def _visibility(**overrides):
    values = dict.fromkeys(
        (
            'general',
            'infrared',
            'motion_detection',
            'line_detection',
            'intrusion_detection',
            'alert_service',
            'stream_youtube',
            'stream_telegram',
            'stream_icecast',
        ),
        True,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def _detection(enabled=False):
    return {
        'enabled': enabled,
        'sendpic': True,
        'fullpic': False,
        'send_videogif': True,
        'send_text': True,
    }


def _alert(**overrides):
    from hikcamerabot.config.schemas.main_config import AlertSchema

    data = {
        'delay': 15,
        'motion_detection': _detection(),
        'line_crossing_detection': _detection(enabled=True),
        'intrusion_detection': _detection(),
    }
    data.update(overrides)
    return AlertSchema.model_validate(data)


class FakeAlarm:
    def __init__(self, started=False):
        self.started = started
        self.trigger_switch = AsyncMock(return_value=None)

    async def start(self):
        self.started = True

    async def stop(self):
        self.started = False


class FakeCam:
    def __init__(self, cam_id='cam_1', started=False, **visibility):
        self.id = cam_id
        self.description = 'Front door'
        self.conf = SimpleNamespace(
            command_sections_visibility=_visibility(**visibility), alert=_alert()
        )
        self.services = SimpleNamespace(alarm=FakeAlarm(started=started))
        self.set_ircut_filter = AsyncMock()
        self.bot = _bot(self)

    def update_alert_conf(self, alert):
        self.conf.alert = alert


def _bot(*cams):
    registry = MagicMock()
    registry.get_instances.side_effect = lambda: list(cams)
    if cams:
        registry.get_instance.return_value = cams[0]
    return SimpleNamespace(chat_users=[1], cam_registry=registry, started_at=0)


def _callback_data(markup) -> list[str]:
    return [btn.callback_data for row in markup.inline_keyboard for btn in row]


def _actions(markup) -> set[str]:
    from hikcamerabot.menu import parse_callback_data

    return {
        parse_callback_data(data)[0].split(':')[0] for data in _callback_data(markup)
    }


def _query(data: str, user_id: int = 1, chat_id: int = 1):
    query = MagicMock()
    query.data = data
    query.from_user = SimpleNamespace(id=user_id)
    query.message = MagicMock()
    query.message.chat = SimpleNamespace(id=chat_id)
    query.message.edit_text = AsyncMock()
    query.message.reply_text = AsyncMock()
    query.message.delete = AsyncMock()
    query.answer = AsyncMock()
    return query


@pytest.fixture
def store(monkeypatch):
    import hikcamerabot.menu as menu

    fake_store = SimpleNamespace(save_camera_alert=AsyncMock())
    monkeypatch.setattr(menu, '_config_store', fake_store)
    monkeypatch.setattr(menu, '_ir_modes', {})
    monkeypatch.setattr(menu, '_panels', {})
    return fake_store


async def _press(cam, *data_parts):
    import hikcamerabot.menu as menu

    query = _query(menu.make_callback_data(data_parts[0], cam.id, *data_parts[1:]))
    await menu.on_menu_callback(cam.bot, query)
    return query


def test_callback_data_roundtrip():
    from hikcamerabot.menu import make_callback_data, parse_callback_data

    assert parse_callback_data(make_callback_data('pic', 'cam_12')) == (
        'pic',
        'cam_12',
    )
    assert parse_callback_data(make_callback_data('opt', 'cam_1', 'md', 'pic')) == (
        'opt:md:pic',
        'cam_1',
    )
    assert parse_callback_data('something|else') is None
    assert parse_callback_data('other|pic|cam_1') is None


def test_camera_keyboard_respects_visibility():
    from hikcamerabot.menu import build_camera_keyboard

    actions = _actions(build_camera_keyboard(FakeCam()))
    assert {'pic', 'video', 'alert', 'ir', 'settings', 'cams', 'status'} <= actions

    limited = _actions(
        build_camera_keyboard(
            FakeCam(
                infrared=False,
                alert_service=False,
                motion_detection=False,
                line_detection=False,
                intrusion_detection=False,
            ),
            show_back=False,
        )
    )
    assert not {'ir', 'alert', 'settings', 'cams'} & limited


def test_all_keyboards_fit_callback_data_limit():
    from hikcamerabot import menu

    cam = FakeCam(cam_id='cam_123456')
    markups = [
        menu.build_cameras_keyboard(cam.bot),
        menu.build_camera_keyboard(cam),
        menu.build_settings_keyboard(cam),
        *(menu.build_detection_keyboard(cam, code) for code in menu._DETECTIONS),
    ]
    for markup in markups:
        for data in _callback_data(markup):
            assert len(data.encode()) <= TELEGRAM_CALLBACK_DATA_LIMIT


def test_toggle_labels_show_state():
    from hikcamerabot.menu import build_camera_keyboard, build_settings_keyboard

    labels = [
        btn.text
        for row in build_camera_keyboard(FakeCam(started=True)).inline_keyboard
        for btn in row
    ]
    assert '🔔 Оповещения ✅' in labels

    labels = [
        btn.text
        for row in build_settings_keyboard(FakeCam()).inline_keyboard
        for btn in row
    ]
    assert '〰️ Линия ✅' in labels
    assert '🏃 Движение ❌' in labels


def test_all_menu_actions_are_known_callbacks():
    from hikcamerabot.menu import _CAMERA_ACTIONS

    for callback, _ in _CAMERA_ACTIONS.values():
        params = inspect.signature(inspect.unwrap(callback)).parameters
        assert list(params) == ['bot', 'message', 'cam']


async def test_menu_callback_rejects_unknown_user():
    from hikcamerabot.menu import make_callback_data, on_menu_callback

    bot = _bot()
    query = _query(make_callback_data('pic', 'cam_1'), user_id=2, chat_id=2)
    await on_menu_callback(bot, query)
    query.answer.assert_awaited_once()
    assert 'Нет доступа' in query.answer.await_args.args[0]
    bot.cam_registry.get_instance.assert_not_called()


async def test_menu_callback_runs_camera_action(monkeypatch):
    import hikcamerabot.menu as menu

    called = {}

    async def fake_getpic(bot, message, cam):
        called['cam'] = cam

    monkeypatch.setitem(menu._CAMERA_ACTIONS, 'pic', (fake_getpic, 'ok'))
    cam = FakeCam()
    query = await _press(cam, 'pic')

    assert called['cam'] is cam
    query.answer.assert_awaited_once_with('ok')


@pytest.mark.parametrize('action', ['unknown', 'pic'])
async def test_menu_callback_unknown_camera_or_action(action):
    import hikcamerabot.menu as menu

    cam = FakeCam()
    if action == 'pic':
        cam.bot.cam_registry.get_instance.side_effect = KeyError
    query = _query(menu.make_callback_data(action, 'cam_9'))

    await menu.on_menu_callback(cam.bot, query)

    assert query.answer.await_args.kwargs.get('show_alert') is True


async def test_alert_toggle_edits_panel_and_saves_config(store):
    cam = FakeCam(started=True)

    query = await _press(cam, 'alert')

    assert cam.services.alarm.started is False
    assert cam.conf.alert.enabled is False
    store.save_camera_alert.assert_awaited_once_with('cam_1', cam.conf.alert)
    # Panel is edited in place, nothing new is sent to the chat.
    query.message.edit_text.assert_awaited_once()
    query.message.reply_text.assert_not_called()
    assert 'выключены' in query.answer.await_args.args[0]

    query = await _press(cam, 'alert')
    assert cam.services.alarm.started is True
    assert cam.conf.alert.enabled is True


async def test_detection_toggle_switches_camera_and_saves(store):
    from hikcamerabot.enums import DetectionType

    cam = FakeCam()

    await _press(cam, 'dett', 'md')

    cam.services.alarm.trigger_switch.assert_awaited_once_with(
        trigger=DetectionType.MOTION, state=True
    )
    assert cam.conf.alert.motion_detection.enabled is True
    # Other settings are kept.
    assert cam.conf.alert.line_crossing_detection.enabled is True
    assert cam.conf.alert.delay == 15
    store.save_camera_alert.assert_awaited_once()


async def test_detection_toggle_camera_error_does_not_save(store):
    from hikcamerabot.exceptions import ServiceRuntimeError

    cam = FakeCam()
    cam.services.alarm.trigger_switch.side_effect = ServiceRuntimeError('offline')

    query = await _press(cam, 'dett', 'md')

    assert cam.conf.alert.motion_detection.enabled is False
    store.save_camera_alert.assert_not_called()
    assert 'offline' in query.answer.await_args.args[0]


async def test_option_toggle_and_delay(store):
    from hikcamerabot.menu import ALERT_DELAY_STEP

    cam = FakeCam()

    await _press(cam, 'opt', 'ld', 'full')
    assert cam.conf.alert.line_crossing_detection.fullpic is True

    await _press(cam, 'delay', '+')
    assert cam.conf.alert.delay == 15 + ALERT_DELAY_STEP

    for _ in range(5):
        await _press(cam, 'delay', '-')
    assert cam.conf.alert.delay == 0
    # The last press hits the limit and saves nothing.
    assert store.save_camera_alert.await_count == 6


async def test_save_failure_is_reported(store):
    store.save_camera_alert.side_effect = OSError('read-only')
    cam = FakeCam()

    query = await _press(cam, 'opt', 'ld', 'txt')

    # Applied for the current run even if the file couldn't be written.
    assert cam.conf.alert.line_crossing_detection.send_text is False
    assert 'не сохранено' in query.answer.await_args.args[0]


async def test_ir_mode_is_marked(store):
    from hikcamerabot.clients.hikvision.enums import IrcutFilterType
    from hikcamerabot.menu import build_camera_keyboard

    cam = FakeCam()

    await _press(cam, 'ir', 'night')

    cam.set_ircut_filter.assert_awaited_once_with(IrcutFilterType.NIGHT)
    labels = [
        btn.text for row in build_camera_keyboard(cam).inline_keyboard for btn in row
    ]
    assert '• 🌙 Ночь •' in labels


async def test_cmd_menu_keeps_single_panel(store):
    import hikcamerabot.menu as menu

    cam = FakeCam()
    bot = cam.bot
    bot.send_message = AsyncMock(
        side_effect=[SimpleNamespace(id=10), SimpleNamespace(id=11)]
    )
    bot.delete_messages = AsyncMock()

    for _ in range(2):
        message = MagicMock()
        message.chat = MagicMock(id=1, last_name=None)
        message.delete = AsyncMock()
        await menu.cmd_menu(bot, message)
        message.delete.assert_awaited_once()

    bot.delete_messages.assert_awaited_once_with(1, 10)
    assert menu._panels == {1: 11}


def test_config_store_keeps_other_settings(tmp_path):
    from hikcamerabot.config.store import ConfigStore

    path = tmp_path / 'config.json'
    original = {
        'telegram': {'token': 'secret'},
        'camera_list': {'cam_1': {'description': 'Кухня', 'alert': {'delay': 1}}},
    }
    path.write_text(json.dumps(original, indent=4, ensure_ascii=False))

    alert = _alert(enabled=False)
    ConfigStore(path)._save_camera_alert('cam_1', alert)

    text = path.read_text(encoding='utf-8')
    saved = json.loads(text)
    assert saved['telegram'] == {'token': 'secret'}
    assert saved['camera_list']['cam_1']['description'] == 'Кухня'
    assert saved['camera_list']['cam_1']['alert'] == alert.model_dump(mode='json')
    assert '\n    "telegram"' in text
    assert json.loads((tmp_path / 'config.json.bak').read_text()) == original
    assert not (tmp_path / 'config.json.tmp').exists()


def test_alert_enabled_defaults_to_true_for_old_configs():
    from hikcamerabot.config.schemas.main_config import AlertSchema

    data = _alert().model_dump()
    data.pop('enabled')
    assert AlertSchema.model_validate(data).enabled is True


def test_status_text_with_fake_bot(tmp_path):
    from hikcamerabot.health import build_status_text

    service = SimpleNamespace(
        NAME=SimpleNamespace(value='Alarm'), started=True, enabled_in_conf=True
    )
    cam = SimpleNamespace(
        id='cam_1',
        description='Front door',
        snapshots_taken=3,
        conf=MagicMock(),
        service_manager=SimpleNamespace(get_all=lambda: [service]),
    )
    cam.conf.livestream.dvr.enabled = False
    cam.conf.timelapse = []
    cam.conf.video_gif.on_demand.tmp_storage = str(tmp_path)
    cam.conf.video_gif.on_alert.tmp_storage = str(tmp_path)
    bot = SimpleNamespace(cam_registry=SimpleNamespace(get_instances=lambda: [cam]))

    text = build_status_text(bot, started_at=0)
    assert 'Состояние бота' in text
    assert 'cam_1' in text
    assert 'снимков сделано: 3' in text
    assert 'Оповещения ✅' in text
