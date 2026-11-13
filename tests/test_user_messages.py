"""What the user sees in Telegram when something goes wrong."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from hikcamerabot.clients.hikvision.xml_status import is_ok_status
from hikcamerabot.exceptions import (
    APIAuthError,
    APIBadResponseCodeError,
    APIConnectionError,
    HikvisionAPIError,
    HikvisionCamError,
    ServiceRuntimeError,
)
from hikcamerabot.services.alarm import link as link_module
from hikcamerabot.services.alarm.link import CameraLinkNotifier
from hikcamerabot.utils.errors import (
    ERR_AUTH,
    ERR_UNKNOWN,
    ERR_UNREACHABLE,
    describe_error,
)
from tests.conftest import requires_config

TELEGRAM_CALLBACK_ANSWER_LIMIT = 200


def _chained(outer: Exception, cause: Exception) -> Exception:
    outer.__cause__ = cause
    return outer


def test_describe_error_camera_unreachable():
    err = _chained(
        HikvisionCamError('Failed to take snapshot'),
        _chained(APIConnectionError('unreachable'), httpx.ConnectTimeout('timeout')),
    )
    assert describe_error(err) == ERR_UNREACHABLE
    assert describe_error(httpx.ConnectError('refused')) == ERR_UNREACHABLE


def test_describe_error_wrong_password():
    err = _chained(
        ServiceRuntimeError('Switch encountered an error'),
        APIAuthError('Bad response code 401', status_code=401),
    )
    assert describe_error(err) == ERR_AUTH


def test_describe_error_camera_returned_error():
    text = describe_error(APIBadResponseCodeError('Bad code', status_code=500))
    assert 'Камера вернула ошибку (код 500)' in text
    assert 'Камера вернула ошибку.' in describe_error(HikvisionAPIError('bad XML'))


def test_describe_error_unknown():
    assert describe_error(RuntimeError('boom')) == ERR_UNKNOWN


def test_error_texts_fit_callback_answer():
    for err in (
        httpx.ConnectError('x'),
        APIAuthError('x', status_code=401),
        APIBadResponseCodeError('x', status_code=500),
        RuntimeError('x'),
    ):
        assert len(describe_error(err)) <= TELEGRAM_CALLBACK_ANSWER_LIMIT


@pytest.mark.parametrize(
    ('status', 'expected'),
    [
        ({'statusCode': '1', 'statusString': 'OK'}, True),
        ({'statusCode': '1', 'statusString': 'Reboot Required'}, True),
        ({'statusCode': '4', 'statusString': 'Invalid Operation'}, False),
        ({'statusCode': '3', 'statusString': 'Device Error'}, False),
    ],
)
def test_is_ok_status_compares_strings(status, expected):
    assert is_ok_status(status) is expected


def test_is_ok_status_raises_on_unexpected_xml():
    with pytest.raises(KeyError):
        is_ok_status({'statusString': 'OK'})


def _bot():
    return SimpleNamespace(send_alert_message=AsyncMock())


async def test_link_notifier_sends_one_offline_and_one_online_message(monkeypatch):
    now = 1000.0
    monkeypatch.setattr(link_module.time, 'monotonic', lambda: now)
    bot = _bot()
    notifier = CameraLinkNotifier(bot=bot, title='Двор (cam_1)', notify_after=60)

    await notifier.on_failure(httpx.ConnectError('refused'))
    bot.send_alert_message.assert_not_awaited()  # may be a short hiccup

    now += 61
    await notifier.on_failure(httpx.ConnectError('refused'))
    now += 600
    await notifier.on_failure(httpx.ConnectError('refused'))
    assert bot.send_alert_message.await_count == 1
    offline_text = bot.send_alert_message.await_args.args[0]
    assert 'Нет связи с камерой' in offline_text
    assert 'Двор (cam_1)' in offline_text

    await notifier.on_success()
    await notifier.on_success()
    assert bot.send_alert_message.await_count == 2
    online_text = bot.send_alert_message.await_args.args[0]
    assert 'снова на связи' in online_text
    assert '11 мин' in online_text


async def test_link_notifier_is_silent_on_short_outage(monkeypatch):
    now = 1000.0
    monkeypatch.setattr(link_module.time, 'monotonic', lambda: now)
    bot = _bot()
    notifier = CameraLinkNotifier(bot=bot, title='Двор (cam_1)', notify_after=60)

    await notifier.on_failure(httpx.ReadTimeout('timeout'))
    now += 10
    await notifier.on_success()
    now += 300
    await notifier.on_failure(httpx.ReadTimeout('timeout'))

    bot.send_alert_message.assert_not_awaited()


async def test_link_notifier_survives_telegram_error():
    bot = SimpleNamespace(send_alert_message=AsyncMock(side_effect=RuntimeError))
    notifier = CameraLinkNotifier(bot=bot, title='Двор (cam_1)', notify_after=0)

    await notifier.on_failure(httpx.ConnectError('refused'))


def _api_client(handler):
    from hikcamerabot.clients.hikvision.api_client import HikvisionAPIClient

    client = HikvisionAPIClient.__new__(HikvisionAPIClient)
    client._log = SimpleNamespace(
        debug=lambda *_, **__: None,
        warning=lambda *_, **__: None,
        error=lambda *_, **__: None,
    )
    client.host = 'http://camera'
    client.port = 80
    client.session = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client


@requires_config
async def test_api_client_does_not_retry_wrong_password():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(401)

    with pytest.raises(APIAuthError) as exc_info:
        await _api_client(handler).request('/ISAPI/System/status')

    assert exc_info.value.status_code == 401
    assert len(calls) == 1  # repeated attempts lock the user on the camera


@requires_config
async def test_api_client_reports_unreachable_camera():
    def handler(request):
        raise httpx.ConnectError('refused', request=request)

    with pytest.raises(APIConnectionError) as exc_info:
        await _api_client(handler).request('/ISAPI/System/status')

    assert describe_error(exc_info.value) == ERR_UNREACHABLE


def _message(text='/ir_on_cam_1'):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(
            id=1, type=None, username='user', first_name='Name', last_name=None
        ),
        reply_text=AsyncMock(),
    )


@requires_config
async def test_failed_camera_command_is_answered():
    from hikcamerabot.decorators import camera_selection

    cam = SimpleNamespace(id='cam_1', description='Двор')
    bot = SimpleNamespace(
        cam_registry=SimpleNamespace(get_instance=lambda _cam_id: cam)
    )

    @camera_selection
    async def failing(bot, message, cam):
        raise ServiceRuntimeError('switch failed') from APIConnectionError('down')

    message = _message()
    await failing(bot, message)

    message.reply_text.assert_awaited_once()
    text = message.reply_text.await_args.args[0]
    assert 'Команда не выполнена' in text
    assert 'Двор (cam_1)' in text
    assert ERR_UNREACHABLE in text


@requires_config
async def test_unknown_command_is_answered_in_private_chat_only():
    from pyrogram.enums import ChatType

    from hikcamerabot import callbacks as cb

    bot = SimpleNamespace(me=SimpleNamespace(username='MyCamBot'))

    private = _message('/getpic_cam_9')
    private.chat.type = ChatType.PRIVATE
    await cb.cmd_unknown(bot, private)
    assert 'Не знаю такую команду' in private.reply_text.await_args.args[0]

    foreign = _message('/start@OtherBot')
    foreign.chat.type = ChatType.GROUP
    await cb.cmd_unknown(bot, foreign)
    foreign.reply_text.assert_not_awaited()

    addressed = _message('/oops@mycambot')
    addressed.chat.type = ChatType.GROUP
    await cb.cmd_unknown(bot, addressed)
    addressed.reply_text.assert_awaited_once()


@requires_config
async def test_version_command_answers_without_internet(monkeypatch):
    from hikcamerabot import callbacks as cb

    monkeypatch.setattr(
        cb.HikCameraBotVersionChecker,
        'get_latest_version',
        AsyncMock(side_effect=httpx.ConnectError('no internet')),
    )
    message = _message('/version')
    await cb.cmd_app_version(SimpleNamespace(chat_users=[1]), message)

    text = message.reply_text.await_args.args[0]
    assert 'Версия бота' in text
    assert 'Не удалось проверить обновления' in text


@requires_config
def test_plural_ru():
    from hikcamerabot.callbacks import plural_ru

    forms = ('камера', 'камеры', 'камер')
    assert [plural_ru(n, *forms) for n in (1, 2, 5, 11, 21, 112)] == [
        'камера',
        'камеры',
        'камер',
        'камер',
        'камера',
        'камер',
    ]


def test_version_regex_reads_version_file():
    from hikcamerabot.clients.github.version_checker import (
        _VERSION_REGEX,
        BotVersion,
    )

    assert _VERSION_REGEX.search("__version__ = '2.10.3'\n").group(1) == '2.10.3'
    assert BotVersion(current='2.0.1', latest='2.0.10').has_new_version()
    assert not BotVersion(current='2.0.1', latest='2.0.1').has_new_version()
