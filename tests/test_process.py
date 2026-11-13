import asyncio
import shlex
import signal
from urllib.parse import unquote, urlsplit

import pytest

from hikcamerabot.constants import (
    FFMPEG_CAM_VIDEO_SRC,
    FFMPEG_CMD_TRANSCODE_ICECAST,
    FFMPEG_CMD_VIDEO_GIF,
)
from hikcamerabot.utils.process import kill_proc, mask_secrets, start_process
from hikcamerabot.utils.url import url_credential
from tests.conftest import requires_linux

TRICKY_PASSWORDS = [
    'simple123',
    'p@ss:word/1',
    'with space',
    'quote"inside',
    "single'quote",
    '$HOME`id`;rm -rf /',
    'braces{0}}',
    'percent%41#hash?q',
    'кириллица',
]


@pytest.mark.parametrize('password', TRICKY_PASSWORDS)
def test_url_credential_roundtrip(password):
    encoded = url_credential(password)
    assert unquote(encoded) == password
    for char in '@:/ "\'`$;{}#?':
        assert char not in encoded


def test_url_credential_keeps_plain_password():
    assert url_credential('Admin12345') == 'Admin12345'


def _build_videogif_cmd(user: str, password: str) -> str:
    video_source = FFMPEG_CAM_VIDEO_SRC.format(
        user=url_credential(user),
        pw=url_credential(password),
        host='192.168.1.10',
        rtsp_port=554,
        channel=101,
    )
    return FFMPEG_CMD_VIDEO_GIF.format(
        loglevel='error',
        rtsp_transport='-rtsp_transport tcp',
        video_source=video_source,
        rec_time=10,
        filepath='/tmp/my videos/cam_1.mp4',
    )


@pytest.mark.parametrize('password', TRICKY_PASSWORDS)
def test_ffmpeg_cmd_keeps_rtsp_url_as_single_argument(password):
    args = shlex.split(_build_videogif_cmd('admin', password))
    url = args[args.index('-i') + 1]
    parts = urlsplit(url)
    assert parts.scheme == 'rtsp'
    assert parts.hostname == '192.168.1.10'
    assert parts.port == 554
    assert unquote(parts.password) == password
    assert args[-1] == '/tmp/my videos/cam_1.mp4'


def test_mask_secrets_hides_url_password():
    cmd = _build_videogif_cmd('admin', 'p@ss:word')
    masked = mask_secrets(cmd)
    assert 'p%40ss' not in masked
    assert 'rtsp://admin:***@192.168.1.10:554' in masked


def test_mask_secrets_hides_icecast_password():
    args = FFMPEG_CMD_TRANSCODE_ICECAST.format(
        ice_genre='g',
        ice_name='n',
        ice_description='d',
        ice_public=0,
        password='SuperSecret',
        content_type='video/webm',
    )
    masked = mask_secrets(args)
    assert 'SuperSecret' not in masked
    assert '-password "***"' in masked


def test_mask_secrets_hides_stream_keys():
    masked = mask_secrets(
        'ffmpeg -f flv "rtmps://dc4-1.rtmp.t.me/s/123456:SecretKey" '
        'rtmp://a.rtmp.youtube.com/live2/abcd-efgh-ijkl'
    )
    assert 'SecretKey' not in masked
    assert 'abcd-efgh' not in masked
    assert '"rtmps://dc4-1.rtmp.t.me/s/***"' in masked
    assert 'rtmp://a.rtmp.youtube.com/live2/***' in masked


def test_mask_secrets_keeps_local_srs_urls():
    text = (
        'rtmp://172.18.0.3/live/livestream_101_cam_1 '
        'rtmp://hikvision_srs_server/live/livestream_101_cam_2'
    )
    assert mask_secrets(text) == text


def test_mask_secrets_keeps_text_without_secrets():
    text = 'ffmpeg -i rtmp://127.0.0.1/live/livestream_101_cam_1 -c copy out.mp4'
    assert mask_secrets(text) == text


@requires_linux
async def test_start_process_does_not_use_shell():
    proc = await start_process('echo "$HOME" `id`', stdout=asyncio.subprocess.PIPE)
    stdout, _ = await proc.communicate()
    assert stdout.decode().strip() == '$HOME `id`'


@requires_linux
async def test_kill_proc_stops_process_and_waits():
    proc = await start_process('sleep 30')
    await kill_proc(proc, signal.SIGINT, wait_timeout=5)
    assert proc.returncode is not None


@requires_linux
async def test_kill_proc_falls_back_to_sigkill():
    # Process ignores SIGINT, so SIGKILL must be used after timeout.
    proc = await start_process('sh -c \'trap "" INT; sleep 30\'')
    await asyncio.sleep(0.2)
    await kill_proc(proc, signal.SIGINT, wait_timeout=0.5)
    assert proc.returncode == -signal.SIGKILL
