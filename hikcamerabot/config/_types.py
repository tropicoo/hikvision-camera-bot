from typing import Annotated

from pydantic import AfterValidator

from hikcamerabot.config._validators import validate_timezone

TimezoneType = Annotated[str, AfterValidator(validate_timezone)]
