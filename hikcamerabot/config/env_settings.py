from pydantic_settings import BaseSettings

from hikcamerabot.config.schemas.types_ import TimezoneType


class Settings(BaseSettings):
    tz: TimezoneType


settings = Settings()
