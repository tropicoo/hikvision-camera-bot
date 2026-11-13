"""Bot health: status report, heartbeat file and low disk / overheat alerts."""

import asyncio
import contextlib
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Final

from hikcamerabot.utils.system import (
    DiskUsage,
    format_duration,
    get_cpu_temperature,
    get_disk_usage,
    get_load_average,
    get_memory_usage,
    unique_filesystems,
)

if TYPE_CHECKING:
    from hikcamerabot.camerabot import CameraBot
    from hikcamerabot.services.abstract import AbstractService

# Docker HEALTHCHECK checks that this file is fresh.
HEARTBEAT_PATH: Final[Path] = Path('/tmp/hikcamerabot.heartbeat')  # noqa: S108
HEARTBEAT_PERIOD: Final[int] = 30
CHECK_PERIOD: Final[int] = 300

DISK_LOW_PERCENT: Final[float] = 10.0
DISK_LOW_GIB: Final[float] = 2.0
DISK_RECOVERED_PERCENT: Final[float] = 15.0
DISK_RECOVERED_GIB: Final[float] = 3.0

CPU_HOT_CELSIUS: Final[float] = 80.0
CPU_RECOVERED_CELSIUS: Final[float] = 70.0

_ROOT_PATH: Final[Path] = Path('/')

# Stream names (DVR, SRS, YOUTUBE...) are shown as is.
_SERVICE_NAMES_RU: Final[dict[str, str]] = {
    'Alarm': 'Оповещения',
    'Timelapse': 'Таймлапс',
}


def get_storage_paths(bot: 'CameraBot') -> list[Path]:
    """Return storage paths used by enabled features + root filesystem."""
    paths: list[Path] = []
    for cam in bot.cam_registry.get_instances():
        conf = cam.conf
        if conf.livestream.dvr.enabled:
            paths.append(Path(conf.livestream.dvr.local_storage_path))
        for timelapse in conf.timelapse:
            if timelapse.enabled:
                paths.extend((Path(timelapse.storage), Path(timelapse.tmp_storage)))
        paths.extend(
            (
                Path(conf.video_gif.on_demand.tmp_storage),
                Path(conf.video_gif.on_alert.tmp_storage),
            )
        )
    paths.append(_ROOT_PATH)
    return unique_filesystems(paths)


def is_disk_low(usage: DiskUsage) -> bool:
    return usage.free_percent < DISK_LOW_PERCENT or usage.free_gib < DISK_LOW_GIB


def is_disk_recovered(usage: DiskUsage) -> bool:
    return (
        usage.free_percent >= DISK_RECOVERED_PERCENT
        and usage.free_gib >= DISK_RECOVERED_GIB
    )


def _format_disk(usage: DiskUsage) -> str:
    warn = ' ⚠️' if is_disk_low(usage) else ''
    return (
        f'{usage.path}: свободно {usage.free_gib:.1f} из {usage.total_gib:.1f} ГБ '
        f'({usage.free_percent:.0f}%){warn}'
    )


def _service_name(service: 'AbstractService') -> str:
    if service.NAME is not None:
        name = str(service.NAME.value)
    else:
        name = service.__class__.__name__.removesuffix('Service')
    return _SERVICE_NAMES_RU.get(name, name)


def build_status_text(bot: 'CameraBot', started_at: float) -> str:
    lines = [
        '<b>🤖 Состояние бота</b>',
        f'Работает: {format_duration(time.time() - started_at)}',
    ]

    host: list[str] = []
    if (temp := get_cpu_temperature()) is not None:
        host.append(f'процессор {temp:.1f}°C{" 🔥" if temp >= CPU_HOT_CELSIUS else ""}')
    if load := get_load_average():
        host.append(f'нагрузка {load[0]:.2f} {load[1]:.2f} {load[2]:.2f}')
    if memory := get_memory_usage():
        host.append(f'память {memory.used_gib:.1f}/{memory.total_gib:.1f} ГБ')
    if host:
        lines.append(' · '.join(host))

    disks = [
        usage
        for path in get_storage_paths(bot)
        if (usage := get_disk_usage(path)) is not None
    ]
    if disks:
        lines.append('\n<b>💾 Диск</b>')
        lines.extend(_format_disk(usage) for usage in disks)

    lines.append('\n<b>📷 Камеры</b>')
    for cam in bot.cam_registry.get_instances():
        services = [
            f'{_service_name(svc)} {"✅" if svc.started else "⛔"}'
            for svc in cam.service_manager.get_all()
            if svc.started or svc.enabled_in_conf
        ]
        services_text = ', '.join(services) if services else 'службы не включены'
        lines.append(
            f'<b>{cam.id}</b> {cam.description}: {services_text}; '
            f'снимков сделано: {cam.snapshots_taken}'
        )
    return '\n'.join(lines)


class HealthWatchdog:
    """Write heartbeat file and alert about low disk space or CPU overheating.

    Every alert is sent once and repeated only after the problem was resolved,
    so a full SD card doesn't flood the chat.
    """

    def __init__(self, bot: 'CameraBot') -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._bot = bot
        self._low_disks: set[Path] = set()
        self._cpu_hot = False

    async def run(self) -> None:
        last_check = 0.0
        while True:
            self._write_heartbeat()
            if time.monotonic() - last_check >= CHECK_PERIOD:
                last_check = time.monotonic()
                try:
                    await self._check()
                except Exception:
                    self._log.exception('Health check failed')
            await asyncio.sleep(HEARTBEAT_PERIOD)

    def _write_heartbeat(self) -> None:
        with contextlib.suppress(OSError):
            HEARTBEAT_PATH.write_text(str(int(time.time())))

    async def _check(self) -> None:
        for path in await asyncio.to_thread(get_storage_paths, self._bot):
            usage = await asyncio.to_thread(get_disk_usage, path)
            if usage is not None:
                await self._check_disk(usage)
        await self._check_cpu_temperature()

    async def _check_disk(self, usage: DiskUsage) -> None:
        if usage.path not in self._low_disks and is_disk_low(usage):
            self._low_disks.add(usage.path)
            self._log.warning('Low disk space: %s', _format_disk(usage))
            await self._bot.send_alert_message(
                f'⚠️ <b>Мало места на диске</b>\n{_format_disk(usage)}\n'
                'Удалите старые записи, иначе новые видео не сохранятся.'
            )
        elif usage.path in self._low_disks and is_disk_recovered(usage):
            self._low_disks.discard(usage.path)
            await self._bot.send_alert_message(
                f'✅ <b>Места на диске снова достаточно</b>\n{_format_disk(usage)}'
            )

    async def _check_cpu_temperature(self) -> None:
        temp = get_cpu_temperature()
        if temp is None:
            return
        if not self._cpu_hot and temp >= CPU_HOT_CELSIUS:
            self._cpu_hot = True
            self._log.warning('CPU temperature is high: %.1f°C', temp)
            await self._bot.send_alert_message(
                f'🔥 <b>Процессор перегревается: {temp:.1f}°C</b>\n'
                'Проверьте охлаждение устройства. Raspberry Pi снижает скорость '
                'работы при 80–85°C.'
            )
        elif self._cpu_hot and temp <= CPU_RECOVERED_CELSIUS:
            self._cpu_hot = False
            await self._bot.send_alert_message(
                f'✅ <b>Температура процессора в норме: {temp:.1f}°C</b>'
            )
