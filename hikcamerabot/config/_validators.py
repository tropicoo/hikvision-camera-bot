from zoneinfo import available_timezones


def validate_timezone(value: str) -> str:
    if value not in available_timezones():
        raise ValueError(f'Invalid timezone: {value}')
    return value
