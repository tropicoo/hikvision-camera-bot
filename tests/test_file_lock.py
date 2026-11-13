import os

from tests.conftest import requires_config, requires_linux

# `hikcamerabot.services.stream` package loads configs on import.
pytestmark = requires_config


def get_files_open_by_process(*args):
    from hikcamerabot.services.stream.dvr.tasks.file_lock_check import (
        get_files_open_by_process as func,
    )

    return func(*args)


def _make_proc(proc_dir, pid: str, comm: str, open_files: list[str]) -> None:
    pid_dir = proc_dir / pid
    (pid_dir / 'fd').mkdir(parents=True)
    (pid_dir / 'comm').write_text(f'{comm}\n')
    for idx, target in enumerate(open_files):
        os.symlink(target, pid_dir / 'fd' / str(idx))


@requires_linux
def test_get_files_open_by_ffmpeg(tmp_path):
    proc_dir = tmp_path / 'proc'
    _make_proc(proc_dir, '100', 'ffmpeg', ['/data/dvr/cam_1_101_600_2025.mp4'])
    _make_proc(proc_dir, '200', 'python', ['/data/dvr/cam_1_101_600_2024.mp4'])
    (proc_dir / 'self').mkdir()

    assert get_files_open_by_process('ffmpeg', proc_dir) == {
        '/data/dvr/cam_1_101_600_2025.mp4'
    }


def test_get_files_open_without_proc_returns_none(tmp_path):
    assert get_files_open_by_process('ffmpeg', tmp_path / 'missing') is None


@requires_linux
def test_real_proc_is_readable():
    assert isinstance(get_files_open_by_process('ffmpeg'), set)
