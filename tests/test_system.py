from pathlib import Path

from hikcamerabot.health import is_disk_low, is_disk_recovered
from hikcamerabot.utils.system import (
    DiskUsage,
    format_duration,
    get_cpu_temperature,
    get_disk_usage,
    get_memory_usage,
    unique_filesystems,
)

GIB = 1024**3


def test_cpu_temperature(tmp_path):
    temp_file = tmp_path / 'temp'
    temp_file.write_text('52123\n')
    assert get_cpu_temperature(temp_file) == 52.123


def test_cpu_temperature_unavailable(tmp_path):
    assert get_cpu_temperature(tmp_path / 'missing') is None


def test_memory_usage(tmp_path):
    meminfo = tmp_path / 'meminfo'
    meminfo.write_text(
        'MemTotal:        3884404 kB\n'
        'MemFree:          123456 kB\n'
        'MemAvailable:    2884404 kB\n'
    )
    usage = get_memory_usage(meminfo)
    assert usage.total == 3884404 * 1024
    assert round(usage.used_gib, 2) == round(1000000 * 1024 / GIB, 2)


def test_memory_usage_unavailable(tmp_path):
    assert get_memory_usage(tmp_path / 'missing') is None


def test_disk_usage_and_unique_filesystems(tmp_path):
    usage = get_disk_usage(tmp_path)
    assert usage is not None
    assert usage.total > 0
    # Same filesystem reported once, missing paths ignored.
    assert unique_filesystems([tmp_path, tmp_path / '..', tmp_path / 'nope']) == [
        tmp_path
    ]


def test_disk_low_thresholds():
    path = Path('/data')
    assert is_disk_low(DiskUsage(path=path, total=64 * GIB, free=5 * GIB))  # < 10%
    assert is_disk_low(DiskUsage(path=path, total=10 * GIB, free=1.5 * GIB))  # < 2G
    assert not is_disk_low(DiskUsage(path=path, total=64 * GIB, free=20 * GIB))
    # Hysteresis: 12% is not low anymore, but not recovered yet.
    middle = DiskUsage(path=path, total=100 * GIB, free=12 * GIB)
    assert not is_disk_low(middle)
    assert not is_disk_recovered(middle)
    assert is_disk_recovered(DiskUsage(path=path, total=100 * GIB, free=20 * GIB))


def test_format_duration():
    assert format_duration(59) == '0 мин'
    assert format_duration(3 * 3600 + 120) == '3 ч 2 мин'
    assert format_duration(2 * 86400 + 3600 + 60) == '2 д 1 ч 1 мин'
