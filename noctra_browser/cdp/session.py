from __future__ import annotations

from noctra_browser.cdp.client import CdpClient
from noctra_browser.cdp.types import JsonObject
from noctra_browser.utils.errors import TargetClosedError
from noctra_browser.utils.events import EventHandler


class CdpSession:
    def __init__(self, client: CdpClient, session_id: str) -> None:
        self._client = client
        self.session_id = session_id
        self._closed = False

    @property
    def client(self) -> CdpClient:
        return self._client

    async def send(
        self,
        method: str,
        params: JsonObject | None = None,
        *,
        timeout: float = 30.0,
    ) -> JsonObject:
        if self._closed:
            raise TargetClosedError("CDP session is closed")
        return await self._client.send(method, params, session_id=self.session_id, timeout=timeout)

    def on_event(self, method: str, handler: EventHandler) -> None:
        self._client.on(method, handler)

    def off_event(self, method: str, handler: EventHandler) -> None:
        self._client.off(method, handler)

    def mark_closed(self) -> None:
        self._closed = True

    def is_closed(self) -> bool:
        return self._closed
