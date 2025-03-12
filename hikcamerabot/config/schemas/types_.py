from typing import Annotated, Literal

from pydantic import AfterValidator

from hikcamerabot.config.schemas.validators_ import (
    int_min_0,
    int_min_1,
    int_min_minus_1,
    validate_ffmpeg_loglevel,
    validate_python_log_level,
    validate_timezone,
)

IntMin1 = Annotated[int, AfterValidator(int_min_1)]
IntMin0 = Annotated[int, AfterValidator(int_min_0)]
IntMinus1 = Annotated[int, AfterValidator(int_min_minus_1)]

FfmpegLogLevel = Annotated[str, AfterValidator(validate_ffmpeg_loglevel)]
PythonLogLevel = Annotated[str, AfterValidator(validate_python_log_level)]
TimezoneType = Annotated[str, AfterValidator(validate_timezone)]

type DvrStorageType = Literal['telegram']
