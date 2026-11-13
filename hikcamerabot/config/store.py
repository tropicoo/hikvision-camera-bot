"""Save settings changed from the bot menu back to `configs/config.json`."""

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Final

from hikcamerabot.config.schemas.main_config import AlertSchema
from hikcamerabot.enums import ConfigFile

CONFIGS_DIR_PATH: Final[Path] = Path(__file__).parent.parent.parent / 'configs'

_DEFAULT_INDENT: Final[int] = 2
_INDENT_REGEX: Final[re.Pattern] = re.compile(r'^( +)\S', re.MULTILINE)


class ConfigStore:
    """Atomically update parts of the main config file.

    Only the changed section is replaced, everything else (credentials,
    streams etc.) is written back as it was. A copy of the previous file
    is kept as `config.json.bak`.
    """

    def __init__(self, path: Path = CONFIGS_DIR_PATH / ConfigFile.MAIN) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._path = path
        self._lock = asyncio.Lock()

    async def save_camera_alert(self, cam_id: str, alert: AlertSchema) -> None:
        async with self._lock:
            await asyncio.to_thread(self._save_camera_alert, cam_id, alert)

    def _save_camera_alert(self, cam_id: str, alert: AlertSchema) -> None:
        text = self._path.read_text(encoding='utf-8')
        data = json.loads(text)
        data['camera_list'][cam_id]['alert'] = alert.model_dump(mode='json')
        self._write(json.dumps(data, indent=_detect_indent(text), ensure_ascii=False))
        self._log.info('[%s] Alert settings saved to "%s"', cam_id, self._path)

    def _write(self, text: str) -> None:
        stat = self._path.stat()
        shutil.copy2(self._path, self._path.with_name(f'{self._path.name}.bak'))

        tmp_path = self._path.with_name(f'{self._path.name}.tmp')
        tmp_path.write_text(f'{text}\n', encoding='utf-8')
        # Keep file owner and mode: the bot runs as root inside Docker.
        tmp_path.chmod(stat.st_mode)
        with contextlib.suppress(AttributeError, PermissionError):
            os.chown(tmp_path, stat.st_uid, stat.st_gid)
        try:
            tmp_path.replace(self._path)
        except OSError:
            # Config file itself is bind-mounted, it can't be replaced.
            self._path.write_text(f'{text}\n', encoding='utf-8')
            tmp_path.unlink(missing_ok=True)


def _detect_indent(text: str) -> int:
    match = _INDENT_REGEX.search(text)
    return len(match.group(1)) if match else _DEFAULT_INDENT
