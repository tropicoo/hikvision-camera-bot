from pathlib import Path

from hikcamerabot.common.video.tasks.abstract import AbstractFfBinaryTask
from hikcamerabot.utils.process import get_stdout_stderr


class MakeThumbnailTask(AbstractFfBinaryTask):
    _CMD = 'ffmpeg -y -loglevel error -i {filepath} -vframes 1 -q:v 31 {thumbpath}'

    def __init__(self, thumbnail_path: Path, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._thumbnail_path = thumbnail_path

    async def run(self) -> bool:
        return await self._make_thumbnail()

    async def _make_thumbnail(self) -> bool:
        cmd = self._CMD.format(filepath=self._file_path, thumbpath=self._thumbnail_path)
        proc = await self._run_proc(cmd)
        if not proc:
            return False

        stdout, stderr = await get_stdout_stderr(proc)
        self._log.debug(
            'Process "%s" returncode: %d, stdout: %s, stderr: %s',
            cmd,
            proc.returncode,
            stdout,
            stderr,
        )
        if proc.returncode:
            self._log.error('Failed to make thumbnail for %s', self._file_path)
            self._err_cleanup()
            return False
        return True

    def _err_cleanup(self) -> None:
        """Cleanup errored thumbnail if any.

        For example, zero-size thumbnail could be created when no space left on device.
        """
        if self._thumbnail_path.exists():
            return

        self._log.info('Cleaning up errored "%s"', self._thumbnail_path)
        try:
            self._thumbnail_path.unlink()
        except Exception:
            self._log.exception('Cleanup failed for errored "%s"', self._thumbnail_path)
