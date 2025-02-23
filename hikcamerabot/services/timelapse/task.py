import asyncio
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Literal
from zoneinfo import ZoneInfo

from tenacity import retry, retry_if_exception_type, wait_fixed

from hikcamerabot.common.video.tasks.abstract import AbstractFfBinaryTask
from hikcamerabot.config.env_settings import settings
from hikcamerabot.config.schemas.main_config import TimelapseSchema
from hikcamerabot.constants import FFMPEG_BIN, TIMELAPSE_STILL_EXT
from hikcamerabot.enums import ServiceType
from hikcamerabot.exceptions import HikvisionCamError
from hikcamerabot.services.abstract import AbstractServiceTask
from hikcamerabot.utils.file import awaitable_shutil_copyfileobj, awaitable_shutil_move
from hikcamerabot.utils.process import get_stdout_stderr
from hikcamerabot.utils.shared import shallow_sleep_async
from hikcamerabot.utils.task import create_task

if TYPE_CHECKING:
    from hikcamerabot.services.timelapse.timelapse import TimelapseService


class MakeTimelapseVideoTask(AbstractFfBinaryTask):
    _CMD = (
        f'{FFMPEG_BIN} -loglevel {{loglevel}} '
        f'-framerate {{img_num}}/{{video_length}} '
        f'-i {{pattern_path}} '
        f'-c:v {{video_codec}} '
        f'-crf {{image_quality}} '
        f'-pix_fmt {{pix_fmt}} '
        f'-r {{framerate}} '
        f'{{custom_ffmpeg_args}} '
        f'"{{timelapse_video_path}}"'
    )
    _CMD_TIMEOUT: int = 600
    _TIMELAPSE_DIR: str = 'timelapse_stills'

    def __init__(
        self,
        *args,
        img_num: int,
        conf: TimelapseSchema,
        pattern_path: Path,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._img_num = img_num
        self._conf = conf
        self._pattern_path = pattern_path
        self._current_tmp_dir = self._file_path.parent

    async def run(self) -> None:
        try:
            return await self._make_timelapse()
        finally:
            await self._post_process()

    async def _make_timelapse(self) -> None:
        command = self._create_command()
        proc = await self._run_proc(cmd=command)
        if not proc:
            return

        stdout, stderr = await get_stdout_stderr(proc)
        self._log.debug(
            'Process "%s" returncode: %d, stdout: %s, stderr: %s',
            command,
            proc.returncode,
            stdout,
            stderr,
        )
        if proc.returncode:
            self._log.error('Failed to make timelapse for "%s"', self._file_path)
            self._log.error(stderr)

    def _create_command(self) -> str:
        if self._conf.threads is None:
            custom_ffmpeg_args = self._conf.custom_ffmpeg_args
        else:
            custom_ffmpeg_args = (
                f'-threads {self._conf.threads} {self._conf.custom_ffmpeg_args}'
            )

        command = self._CMD.format(
            loglevel=self._conf.ffmpeg_log_level,
            img_num=self._img_num,
            video_length=self._conf.video_length,
            pattern_path=self._pattern_path,
            video_codec=self._conf.video_codec.value,
            image_quality=self._conf.image_quality,
            pix_fmt=self._conf.pix_fmt,
            framerate=self._conf.video_framerate,
            custom_ffmpeg_args=custom_ffmpeg_args,
            timelapse_video_path=self._file_path,
        )

        if self._conf.nice_value is not None:
            command = f'nice -n {self._conf.nice_value} {command}'
        return command

    async def _post_process(self) -> None:
        if self._conf.keep_stills:
            await self._move_stills_to_storage()
            return
        await asyncio.to_thread(self._cleanup)

    async def _move_stills_to_storage(self) -> None:
        timelapse_stills_dir = self._conf.storage / self._TIMELAPSE_DIR
        dest_timelapse_dir = timelapse_stills_dir / self._file_path.stem

        self._log.info(
            'Moving timelapse stills from "%s" to "%s"',
            self._current_tmp_dir,
            dest_timelapse_dir,
        )
        try:
            await awaitable_shutil_move(
                self._current_tmp_dir.as_posix(), dest_timelapse_dir.as_posix()
            )
        except Exception as err:
            self._log.error(
                'Failed to move directory "%s": %s', self._current_tmp_dir, err
            )

    def _cleanup(self) -> None:
        files = list(self._current_tmp_dir.glob(f'*.{TIMELAPSE_STILL_EXT}'))
        self._log.info('Removing timelapse JPG files %s', files)
        for file_ in files:
            file_.unlink()


class TimelapseTask(AbstractServiceTask):
    TYPE: Literal[ServiceType.TIMELAPSE] = ServiceType.TIMELAPSE
    service: 'TimelapseService'

    server_tz = ZoneInfo(settings.tz)

    def __init__(self, *args, conf: TimelapseSchema, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._conf = conf
        self._local_tz = ZoneInfo(self._conf.timezone)
        self._tmp_storage = self._conf.tmp_storage

        self._full_tmp_path: Path | None = None

    @retry(retry=retry_if_exception_type(Exception), wait=wait_fixed(1))
    async def run(self) -> None:
        self._log.info(
            '[%s] Starting timelapse task "%s" for "%s"',
            self._cam.id,
            self._conf.name,
            self._cam.description,
        )
        prefix = f'tmp_timelapse_dir-{self._cam.id}-'
        with TemporaryDirectory(prefix=prefix, dir=self._tmp_storage) as tmp_dir:
            self._full_tmp_path = Path(tmp_dir)
            self._log.debug(
                '[%s] Created temporary directory "%s"',
                self._cam.id,
                self._full_tmp_path,
            )
            try:
                await self._run()
            finally:
                self._log.info(
                    '[%s] Exiting timelapse task for "%s"',
                    self._cam.id,
                    self._cam.description,
                )

    async def _run(self) -> None:  # noqa: C901
        sleep_time = self._conf.snapshot_period
        start_hour = self._conf.start_hour
        end_hour = self._conf.end_hour
        img_num: int = 0
        timelapse_started: bool = False
        default_sleep: float = 1

        async def _make_snapshot() -> None:
            nonlocal img_num
            nonlocal timelapse_started
            nonlocal default_sleep

            await self._take_picture(img_num=img_num)
            await shallow_sleep_async(sleep_time)
            timelapse_started = True
            img_num += 1
            default_sleep = 0

        async def _create_timelapse() -> None:
            nonlocal img_num
            nonlocal timelapse_started
            nonlocal default_sleep

            _ = await self._create_timelapse_video(img_num=img_num)
            timelapse_started = False
            img_num = 0
            default_sleep = 1

        try:
            local_tz = self._local_tz
            while self.service.started and not self._should_exit():
                curr_hour = datetime.now(local_tz).hour
                if start_hour < end_hour:
                    # Period within the same day (e.g., 07:00 to 18:00)
                    if start_hour <= curr_hour < end_hour:
                        await _make_snapshot()
                    elif timelapse_started and curr_hour >= end_hour:
                        await _create_timelapse()

                # Spanning across midnight (e.g., 22:00 to 04:00)
                elif curr_hour >= start_hour or curr_hour < end_hour:
                    await _make_snapshot()
                elif timelapse_started and (
                    curr_hour < start_hour or curr_hour >= end_hour
                ):
                    await _create_timelapse()

                await shallow_sleep_async(default_sleep)
        except HikvisionCamError as err:
            self._log.error(err)
            raise
        except Exception:
            self._log.exception('[%s] Unexpected error in timelapse task', self._cam.id)
            raise

    async def _take_picture(self, img_num: int) -> None:
        img, taken_at = await self._cam.take_snapshot(channel=self._conf.channel)
        filepath = (
            self._full_tmp_path / f'img_{str(img_num).zfill(2)}.{TIMELAPSE_STILL_EXT}'
        )
        self._log.info('[%s] Saving timelapse image "%s"', self._cam.id, filepath)
        with filepath.open('wb') as fd_out:
            await awaitable_shutil_copyfileobj(img, fd_out)

    async def _create_timelapse_video(self, img_num: int) -> Path:
        task_name = f'{self._cam.id} timelapse video task'
        timestamp = datetime.now(tz=self.server_tz).strftime('%Y-%m-%d_%H-%M-%S')
        filepath = self._conf.storage / f'{self._cam.id}-timelapse-{timestamp}.mp4'
        task = MakeTimelapseVideoTask(
            img_num=img_num,
            conf=self._conf,
            pattern_path=self._full_tmp_path / f'img_%2d.{TIMELAPSE_STILL_EXT}',
            file_path=filepath,
        ).run()
        await create_task(
            coroutine=task,
            task_name=task_name,
            logger=self._log,
            exception_message='Task %s raised an exception',
            exception_message_args=(task_name,),
        )
        return filepath

    def _should_exit(self) -> bool:
        return not self.service.started
