"""Host system information (CPU temperature, memory, disk), Raspberry Pi friendly."""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Final

_THERMAL_ZONE_PATH: Final[Path] = Path('/sys/class/thermal/thermal_zone0/temp')
_MEMINFO_PATH: Final[Path] = Path('/proc/meminfo')
_GIB: Final[int] = 1024**3


@dataclass(frozen=True)
class DiskUsage:
    path: Path
    total: int
    free: int

    @property
    def free_percent(self) -> float:
        return self.free / self.total * 100 if self.total else 0.0

    @property
    def free_gib(self) -> float:
        return self.free / _GIB

    @property
    def total_gib(self) -> float:
        return self.total / _GIB


@dataclass(frozen=True)
class MemoryUsage:
    total: int
    available: int

    @property
    def used_gib(self) -> float:
        return (self.total - self.available) / _GIB

    @property
    def total_gib(self) -> float:
        return self.total / _GIB


def get_cpu_temperature(path: Path = _THERMAL_ZONE_PATH) -> float | None:
    """Return CPU temperature in Celsius or None if not available."""
    try:
        return int(path.read_text().strip()) / 1000
    except (OSError, ValueError):
        return None


def get_memory_usage(path: Path = _MEMINFO_PATH) -> MemoryUsage | None:
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return None
    values: dict[str, int] = {}
    for line in lines:
        key, _, rest = line.partition(':')
        parts = rest.split()
        if parts and parts[0].isdigit():
            values[key] = int(parts[0]) * 1024
    if 'MemTotal' not in values or 'MemAvailable' not in values:
        return None
    return MemoryUsage(total=values['MemTotal'], available=values['MemAvailable'])


def get_load_average() -> tuple[float, float, float] | None:
    try:
        return os.getloadavg()
    except (OSError, AttributeError):
        return None


def get_disk_usage(path: Path) -> DiskUsage | None:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return None
    return DiskUsage(path=path, total=usage.total, free=usage.free)


def unique_filesystems(paths: list[Path]) -> list[Path]:
    """Keep one existing path per filesystem to avoid duplicate disk reports."""
    seen_devices: set[int] = set()
    result: list[Path] = []
    for path in paths:
        try:
            device = path.stat().st_dev
        except OSError:
            continue
        if device not in seen_devices:
            seen_devices.add(device)
            result.append(path)
    return result


def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60
    if days:
        return f'{days} д {hours} ч {minutes} мин'
    if hours:
        return f'{hours} ч {minutes} мин'
    return f'{minutes} мин'
