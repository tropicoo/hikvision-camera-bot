"""Human-readable (Russian) explanations of errors shown to Telegram users."""

from collections.abc import Iterator
from typing import Final

import httpx

from hikcamerabot.exceptions import (
    APIAuthError,
    APIBadResponseCodeError,
    APIConnectionError,
    HikvisionAPIError,
)

# Texts are also used as callback query answers: Telegram limits them to 200 chars.
ERR_UNREACHABLE: Final[str] = (
    '📡 Камера не отвечает. Проверьте питание камеры, сеть (кабель или Wi-Fi) '
    'и IP-адрес камеры в config.json.'
)
ERR_AUTH: Final[str] = (
    '🔑 Камера отклонила логин или пароль. Проверьте user и password в '
    'config.json и права этого пользователя на камере.'
)
ERR_CAMERA: Final[str] = (
    '⚠️ Камера вернула ошибку{code}. Возможно, функция не поддерживается '
    'камерой или выключена в её веб-интерфейсе.'
)
ERR_UNKNOWN: Final[str] = (
    '❌ Не получилось выполнить. Подробности в логах: '
    'docker compose logs --tail 100 hikvision-camera-bot'
)


def _error_chain(err: BaseException) -> Iterator[BaseException]:
    seen: set[int] = set()
    current: BaseException | None = err
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def describe_error(err: BaseException) -> str:
    """Tell the user what went wrong and what to do: no link / password / camera."""
    chain = list(_error_chain(err))
    for exc in chain:
        if isinstance(exc, APIConnectionError | httpx.TransportError):
            return ERR_UNREACHABLE
    for exc in chain:
        if isinstance(exc, APIAuthError):
            return ERR_AUTH
        if isinstance(exc, APIBadResponseCodeError):
            code = f' (код {exc.status_code})' if exc.status_code else ''
            return ERR_CAMERA.format(code=code)
    if any(isinstance(exc, HikvisionAPIError) for exc in chain):
        return ERR_CAMERA.format(code='')
    return ERR_UNKNOWN
