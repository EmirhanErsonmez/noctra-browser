from __future__ import annotations

import contextlib
from types import TracebackType
from typing import TYPE_CHECKING, Any

from noctra_browser.browser.launcher import BrowserProcess
from noctra_browser.browser.target import TargetInfo
from noctra_browser.cdp.client import CdpClient
from noctra_browser.cdp.domains import BrowserDomain, TargetDomain
from noctra_browser.cdp.session import CdpSession
from noctra_browser.cdp.types import CdpEvent
from noctra_browser.stealth.config import StealthConfig
from noctra_browser.types.public import Viewport
from noctra_browser.utils.events import EventEmitter, EventHandler

if TYPE_CHECKING:
    from noctra_browser.page.page import Page


class Browser:
    def __init__(
        self,
        client: CdpClient,
        *,
        process: BrowserProcess | None = None,
        viewport: Viewport | None = None,
        stealth: StealthConfig | None = None,
    ) -> None:
        self._client = client
        self._process = process
        self._viewport = viewport
        self._stealth = stealth
        self._emitter = EventEmitter()
        self._pages: dict[str, Page] = {}
        self._closed = False
        self._client.on("Target.targetDestroyed", self._handle_target_destroyed)
        self._client.on("Target.detachedFromTarget", self._handle_detached_from_target)
        self._client.on("disconnected", self._handle_disconnected)

    async def __aenter__(self) -> Browser:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def initialize(self) -> None:
        await self._client.send(TargetDomain.SET_DISCOVER_TARGETS, {"discover": True})

    async def new_page(self) -> Page:
        result = await self._client.send(TargetDomain.CREATE_TARGET, {"url": "about:blank"})
        target_id = str(result.get("targetId", ""))
        page = await self._attach_page(target_id)
        await self._emitter.emit("page", page)
        return page

    async def pages(self) -> list[Page]:
        result = await self._client.send(TargetDomain.GET_TARGETS)
        raw_targets = result.get("targetInfos", [])
        if not isinstance(raw_targets, list):
            return list(self._pages.values())

        pages: list[Page] = []
        for raw_target in raw_targets:
            if not isinstance(raw_target, dict):
                continue
            target = TargetInfo.from_cdp(raw_target)
            if target.type != "page" or not target.target_id:
                continue
            existing = self._pages.get(target.target_id)
            if existing is not None and not existing.is_closed():
                pages.append(existing)
            else:
                page = await self._attach_page(target.target_id)
                pages.append(page)
        return pages

    async def version(self) -> dict[str, Any]:
        return await self._client.send(BrowserDomain.GET_VERSION)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True

        for page in list(self._pages.values()):
            await page._mark_closed()
        self._pages.clear()

        if self._process is not None:
            await self._process.close()
        else:
            with contextlib.suppress(Exception):
                await self._client.send(BrowserDomain.CLOSE, timeout=2.0)

        await self._client.close()
        await self._emitter.emit("close", self)
        await self._emitter.emit("disconnected", self)

    def is_connected(self) -> bool:
        return not self._closed and self._client.is_connected()

    def on(self, event: str, handler: EventHandler) -> None:
        self._emitter.on(event, handler)

    def off(self, event: str, handler: EventHandler) -> None:
        self._emitter.off(event, handler)

    def once(self, event: str, handler: EventHandler) -> None:
        self._emitter.once(event, handler)

    async def emit(self, event: str, payload: object = None) -> None:
        await self._emitter.emit(event, payload)

    @property
    def client(self) -> CdpClient:
        return self._client

    async def _attach_page(self, target_id: str) -> Page:
        existing = self._pages.get(target_id)
        if existing is not None and not existing.is_closed():
            return existing

        from noctra_browser.page.page import Page

        result = await self._client.send(
            TargetDomain.ATTACH_TO_TARGET,
            {"targetId": target_id, "flatten": True},
        )
        session_id = str(result.get("sessionId", ""))
        session = CdpSession(self._client, session_id)
        page = Page(
            self,
            target_id=target_id,
            session=session,
            viewport=self._viewport,
            stealth=self._stealth,
        )
        try:
            await page.initialize()
        except Exception:
            session.mark_closed()
            raise
        self._pages[target_id] = page
        return page

    def _forget_page(self, target_id: str) -> None:
        self._pages.pop(target_id, None)

    async def _handle_target_destroyed(self, payload: object) -> None:
        if not isinstance(payload, CdpEvent):
            return
        target_id = payload.params.get("targetId")
        if not isinstance(target_id, str):
            return
        page = self._pages.pop(target_id, None)
        if page is not None:
            await page._mark_closed()

    async def _handle_detached_from_target(self, payload: object) -> None:
        if not isinstance(payload, CdpEvent):
            return
        session_id = payload.params.get("sessionId")
        if not isinstance(session_id, str):
            return
        for target_id, page in list(self._pages.items()):
            if page.session_id == session_id:
                self._pages.pop(target_id, None)
                await page._mark_closed()
                break

    async def _handle_disconnected(self, payload: object) -> None:
        self._closed = True
        for page in list(self._pages.values()):
            await page._mark_closed()
        self._pages.clear()
        await self._emitter.emit("disconnected", payload)
