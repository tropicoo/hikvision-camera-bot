from pydantic_settings import BaseSettings

from hikcamerabot.config._types import TimezoneType


class Settings(BaseSettings):
    tz: TimezoneType


settings = Settings()
