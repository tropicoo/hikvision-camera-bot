from urllib.parse import quote


def url_credential(value: str) -> str:
    """Percent-encode username/password for use inside a URL (e.g. RTSP).

    Without it, passwords with `@`, `:`, `/`, `#`, `{`, `"` etc. break the URL
    or the ffmpeg command. FFmpeg URL-decodes credentials before authentication,
    so plain alphanumeric passwords stay exactly the same.
    """
    return quote(value, safe='')
