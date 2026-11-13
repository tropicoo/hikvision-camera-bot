"""Tell the user when a camera goes offline and when it is back."""

import logging
import time
from typing import TYPE_CHECKING, Final

from hikcamerabot.utils.errors import describe_error
from hikcamerabot.utils.system import format_duration

if TYPE_CHECKING:
    from hikcamerabot.camerabot import CameraBot

# Short hiccups (camera reboot, Wi-Fi reconnect) are not worth a message.
OFFLINE_NOTIFY_AFTER: Final[float] = 60.0


class CameraLinkNotifier:
    """Send one message when the alert stream is lost and one when it is back.

    The alert stream reconnects by itself (`retry_forever`); without these
    messages the user learns about a dead camera only from missing alerts.
    """

    def __init__(
        self,
        bot: 'CameraBot',
        title: str,
        notify_after: float = OFFLINE_NOTIFY_AFTER,
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._bot = bot
        self._title = title
        self._notify_after = notify_after
        self._failing_since: float | None = None
        self._notified = False

    async def on_failure(self, err: BaseException) -> None:
        """Register a failed connection attempt or a dropped stream."""
        now = time.monotonic()
        if self._failing_since is None:
            self._failing_since = now
        if self._notified or now - self._failing_since < self._notify_after:
            return
        self._notified = True
        self._log.warning('%s is offline, notifying users', self._title)
        await self._send(
            f'📡 <b>Нет связи с камерой</b> — {self._title}\n'
            f'{describe_error(err)}\n\n'
            'Тревоги с неё пока не приходят. Бот продолжает попытки и сообщит, '
            'когда связь вернётся.'
        )

    async def on_success(self) -> None:
        """Register that data from the camera is flowing again."""
        if self._failing_since is None:
            return
        downtime = time.monotonic() - self._failing_since
        self._failing_since = None
        if not self._notified:
            return
        self._notified = False
        self._log.info('%s is back online', self._title)
        await self._send(
            f'✅ <b>Камера снова на связи</b> — {self._title}\n'
            f'Связи не было {format_duration(downtime)}.'
        )

    async def _send(self, text: str) -> None:
        try:
            await self._bot.send_alert_message(text)
        except Exception:
            self._log.exception('Failed to send camera link notification')
