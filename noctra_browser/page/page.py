from __future__ import annotations

import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from noctra_browser.cdp.domains import (
    DomDomain,
    EmulationDomain,
    LogDomain,
    PageDomain,
    RuntimeDomain,
    TargetDomain,
)
from noctra_browser.cdp.session import CdpSession
from noctra_browser.cdp.types import CdpEvent
from noctra_browser.cookies.manager import CookieManager
from noctra_browser.input.keyboard import Keyboard
from noctra_browser.input.mouse import Mouse
from noctra_browser.network.manager import NetworkManager
from noctra_browser.page.element import ElementHandle
from noctra_browser.page.lifecycle import normalize_load_state, normalize_selector_state
from noctra_browser.page.locator import Locator
from noctra_browser.runtime.evaluator import RuntimeEvaluator
from noctra_browser.runtime.serialization import remote_object_to_python
from noctra_browser.screenshot.service import ScreenshotService
from noctra_browser.selectors.engine import SelectorEngine
from noctra_browser.stealth.config import StealthConfig
from noctra_browser.stealth.manager import StealthManager
from noctra_browser.types.public import (
    ConsoleMessage,
    Cookie,
    LoadState,
    ScreenshotType,
    SelectorState,
    Viewport,
)
from noctra_browser.utils.async_utils import wait_for_condition
from noctra_browser.utils.errors import CdpError, NoctraError, TargetClosedError
from noctra_browser.utils.events import EventEmitter, EventHandler

if TYPE_CHECKING:
    from noctra_browser.browser.browser import Browser

# Seconds of network quiet before "networkidle" is considered reached (Playwright parity).
_NETWORK_IDLE_SECONDS = 0.5


class Page:
    def __init__(
        self,
        browser: Browser,
        *,
        target_id: str,
        session: CdpSession,
        viewport: Viewport | None = None,
        stealth: StealthConfig | None = None,
    ) -> None:
        self._browser = browser
        self._client = browser.client
        self._target_id = target_id
        self._session = session
        self._viewport = viewport
        self._stealth_config = stealth or StealthConfig.disabled()
        self._emitter = EventEmitter()
        self._selector_engine = SelectorEngine()
        self._evaluator = RuntimeEvaluator(session, isolated=self._stealth_config.enabled)
        self._keyboard = Keyboard(session)
        self._mouse = Mouse(session)
        self._network = NetworkManager(session)
        self._cookies = CookieManager(session, self.url)
        self._screenshot = ScreenshotService(session)
        self._stealth = StealthManager(session, self._stealth_config)
        self._closed = False
        self._load_states: set[LoadState] = set()
        self._inflight_requests: set[str] = set()
        self._last_network_activity = time.monotonic()
        self._client_handlers: list[tuple[str, EventHandler]] = [
            ("Page.loadEventFired", self._handle_load_event),
            ("Page.domContentEventFired", self._handle_domcontentloaded_event),
            ("Network.requestWillBeSent", self._handle_request_event),
            ("Network.responseReceived", self._handle_response_event),
            ("Network.loadingFinished", self._handle_network_done_event),
            ("Network.loadingFailed", self._handle_network_done_event),
            ("Runtime.consoleAPICalled", self._handle_console_event),
            ("Log.entryAdded", self._handle_log_entry_event),
        ]

    @property
    def session_id(self) -> str:
        return self._session.session_id

    async def initialize(self) -> None:
        for event, handler in self._client_handlers:
            self._client.on(event, handler)
        await self._session.send(PageDomain.ENABLE)
        if self._viewport is not None:
            await self._apply_viewport(self._viewport)
        if not self._stealth_config.enabled:
            await self._session.send(RuntimeDomain.ENABLE)
        await self._stealth.apply(None)
        await self._network.enable()
        await self._session.send(LogDomain.ENABLE)

    async def goto(
        self,
        url: str,
        wait_until: LoadState = "load",
        timeout: float = 30.0,
    ) -> None:
        self._raise_if_closed()
        self._reset_lifecycle()
        result = await self._session.send(PageDomain.NAVIGATE, {"url": url}, timeout=timeout)
        error_text = result.get("errorText")
        if isinstance(error_text, str) and error_text:
            raise NoctraError(f"Navigation to {url!r} failed: {error_text}")
        await self.wait_for_load_state(wait_until, timeout=timeout)

    async def reload(self, wait_until: LoadState = "load", timeout: float = 30.0) -> None:
        self._raise_if_closed()
        self._reset_lifecycle()
        await self._session.send(PageDomain.RELOAD, timeout=timeout)
        await self.wait_for_load_state(wait_until, timeout=timeout)

    async def title(self) -> str:
        return str(await self.evaluate("document.title"))

    async def url(self) -> str:
        return str(await self.evaluate("window.location.href"))

    async def content(self) -> str:
        return str(await self.evaluate("document.documentElement.outerHTML"))

    async def evaluate(self, expression_or_function: str, *args: Any) -> Any:
        self._raise_if_closed()
        return await self._evaluator.evaluate(expression_or_function, *args)

    def locator(self, selector: str) -> Locator:
        self._selector_engine.parse(selector)
        return Locator(self, selector)

    async def query(self, selector: str) -> ElementHandle | None:
        self._raise_if_closed()
        parsed = self._selector_engine.parse(selector)
        root_id = await self._document_node_id()
        result = await self._session.send(
            DomDomain.QUERY_SELECTOR,
            {"nodeId": root_id, "selector": parsed.value},
        )
        node_id = result.get("nodeId", 0)
        if not isinstance(node_id, int) or node_id == 0:
            return None
        return ElementHandle(self, node_id)

    async def query_all(self, selector: str) -> list[ElementHandle]:
        self._raise_if_closed()
        parsed = self._selector_engine.parse(selector)
        root_id = await self._document_node_id()
        result = await self._session.send(
            DomDomain.QUERY_SELECTOR_ALL,
            {"nodeId": root_id, "selector": parsed.value},
        )
        node_ids = result.get("nodeIds", [])
        if not isinstance(node_ids, list):
            return []
        return [ElementHandle(self, node_id) for node_id in node_ids if isinstance(node_id, int)]

    async def click(self, selector: str, timeout: float = 30.0) -> None:
        element = await self.wait_for_selector(selector, timeout=timeout, state="visible")
        if element is None:
            raise TargetClosedError("Target closed while waiting for clickable element")
        await element.click(timeout=timeout)

    async def type(self, selector: str, text: str, delay: float = 0, timeout: float = 30.0) -> None:
        element = await self.wait_for_selector(selector, timeout=timeout, state="visible")
        if element is None:
            raise TargetClosedError("Target closed while waiting for typeable element")
        await element.type(text, delay=delay, timeout=timeout)

    async def press(self, selector: str, key: str, timeout: float = 30.0) -> None:
        element = await self.wait_for_selector(selector, timeout=timeout, state="visible")
        if element is None:
            raise TargetClosedError("Target closed while waiting for press target")
        await element.press(key, timeout=timeout)

    async def wait_for_selector(
        self,
        selector: str,
        timeout: float = 30.0,
        state: SelectorState = "attached",
    ) -> ElementHandle | None:
        self._selector_engine.parse(selector)
        target_state = normalize_selector_state(state)

        if target_state == "attached":
            return await wait_for_condition(
                lambda: self.query(selector),
                timeout=timeout,
                timeout_message=(
                    f"Timed out after {timeout:.1f}s while waiting for selector {selector!r}"
                ),
                closed_check=self.is_closed,
            )
        if target_state == "visible":
            return await wait_for_condition(
                lambda: self._visible_element(selector),
                timeout=timeout,
                timeout_message=(
                    f"Timed out after {timeout:.1f}s while waiting for selector {selector!r}"
                ),
                closed_check=self.is_closed,
            )

        async def selector_absent_or_hidden() -> bool | None:
            return await self._selector_absent_or_hidden(selector, target_state)

        _selector_ready: bool = await wait_for_condition(
            selector_absent_or_hidden,
            timeout=timeout,
            timeout_message=(
                f"Timed out after {timeout:.1f}s while waiting for selector {selector!r}"
            ),
            closed_check=self.is_closed,
        )
        return None

    async def wait_for_load_state(self, state: LoadState = "load", timeout: float = 30.0) -> None:
        target_state = normalize_load_state(state)
        await wait_for_condition(
            lambda: self._has_load_state(target_state),
            timeout=timeout,
            timeout_message=(
                f"Timed out after {timeout:.1f}s while waiting for load state {target_state!r}"
            ),
            closed_check=self.is_closed,
        )

    async def screenshot(
        self,
        path: str | None = None,
        full_page: bool = False,
        type: ScreenshotType = "png",
    ) -> bytes:
        self._raise_if_closed()
        return await self._screenshot.capture(path=path, full_page=full_page, type=type)

    async def cookies(self) -> list[Cookie]:
        self._raise_if_closed()
        return await self._cookies.cookies()

    async def set_cookies(self, cookies: Sequence[Cookie]) -> None:
        self._raise_if_closed()
        await self._cookies.set_cookies(cookies)

    async def close(self) -> None:
        if self._closed:
            return
        try:
            await self._client.send(TargetDomain.CLOSE_TARGET, {"targetId": self._target_id})
        except CdpError as exc:
            if not self._is_already_closed_error(exc):
                raise
        finally:
            self._browser._forget_page(self._target_id)
            await self._mark_closed()

    def is_closed(self) -> bool:
        return self._closed

    def on(self, event: str, handler: EventHandler) -> None:
        self._emitter.on(event, handler)

    def off(self, event: str, handler: EventHandler) -> None:
        self._emitter.off(event, handler)

    def once(self, event: str, handler: EventHandler) -> None:
        self._emitter.once(event, handler)

    async def _document_node_id(self) -> int:
        result = await self._session.send(DomDomain.GET_DOCUMENT, {"pierce": True})
        root = result.get("root", {})
        node_id = root.get("nodeId") if isinstance(root, dict) else None
        if not isinstance(node_id, int):
            raise NoctraError("Could not resolve document root")
        return node_id

    async def _apply_viewport(self, viewport: Viewport) -> None:
        await self._session.send(
            EmulationDomain.SET_DEVICE_METRICS_OVERRIDE,
            {
                "width": viewport.width,
                "height": viewport.height,
                "deviceScaleFactor": viewport.device_scale_factor,
                "mobile": viewport.is_mobile,
            },
        )

    async def _visible_element(self, selector: str) -> ElementHandle | None:
        element = await self.query(selector)
        if element is None:
            return None
        return element if await element.is_visible() else None

    async def _selector_absent_or_hidden(self, selector: str, state: SelectorState) -> bool | None:
        element = await self.query(selector)
        if element is None:
            return True
        if state == "hidden" and not await element.is_visible():
            return True
        return None

    def _has_load_state(self, state: LoadState) -> bool | None:
        if state == "networkidle":
            idle_for = time.monotonic() - self._last_network_activity
            quiet = not self._inflight_requests and idle_for >= _NETWORK_IDLE_SECONDS
            return True if quiet else None
        return True if state in self._load_states else None

    def _reset_lifecycle(self) -> None:
        self._load_states.clear()
        self._inflight_requests.clear()
        self._last_network_activity = time.monotonic()
        self._evaluator.reset_context()

    async def _handle_load_event(self, payload: object) -> None:
        if not self._belongs_to_page(payload):
            return
        self._load_states.add("load")
        await self._emitter.emit("load", self)

    async def _handle_domcontentloaded_event(self, payload: object) -> None:
        if not self._belongs_to_page(payload):
            return
        self._load_states.add("domcontentloaded")
        await self._emitter.emit("domcontentloaded", self)

    async def _handle_request_event(self, payload: object) -> None:
        if not isinstance(payload, CdpEvent) or not self._belongs_to_page(payload):
            return
        request_id = payload.params.get("requestId")
        if isinstance(request_id, str):
            self._inflight_requests.add(request_id)
        self._last_network_activity = time.monotonic()
        await self._emitter.emit("request", self._network.request_from_event(payload.params))

    async def _handle_response_event(self, payload: object) -> None:
        if not isinstance(payload, CdpEvent) or not self._belongs_to_page(payload):
            return
        self._last_network_activity = time.monotonic()
        await self._emitter.emit("response", self._network.response_from_event(payload.params))

    async def _handle_network_done_event(self, payload: object) -> None:
        if not isinstance(payload, CdpEvent) or not self._belongs_to_page(payload):
            return
        request_id = payload.params.get("requestId")
        if isinstance(request_id, str):
            self._inflight_requests.discard(request_id)
        self._last_network_activity = time.monotonic()

    async def _handle_console_event(self, payload: object) -> None:
        if not isinstance(payload, CdpEvent) or not self._belongs_to_page(payload):
            return
        args = payload.params.get("args", [])
        parts: list[str] = []
        if isinstance(args, list):
            for arg in args:
                if isinstance(arg, dict):
                    parts.append(str(remote_object_to_python(arg)))
        location = {
            "url": payload.params.get("url", ""),
            "line_number": payload.params.get("lineNumber", 0),
            "column_number": payload.params.get("columnNumber", 0),
        }
        message = ConsoleMessage(
            type=str(payload.params.get("type", "log")),
            text=" ".join(parts),
            location=location,
        )
        await self._emitter.emit("console", message)

    async def _handle_log_entry_event(self, payload: object) -> None:
        if not isinstance(payload, CdpEvent) or not self._belongs_to_page(payload):
            return
        entry = payload.params.get("entry", {})
        if not isinstance(entry, dict):
            return
        message = ConsoleMessage(
            type=str(entry.get("level", "log")),
            text=str(entry.get("text", "")),
            location={"url": entry.get("url", ""), "line_number": entry.get("lineNumber", 0)},
        )
        await self._emitter.emit("console", message)

    def _belongs_to_page(self, payload: object) -> bool:
        return isinstance(payload, CdpEvent) and payload.session_id == self.session_id

    def _is_already_closed_error(self, error: CdpError) -> bool:
        message = error.message.lower()
        return (
            "no target" in message
            or "target closed" in message
            or "session closed" in message
            or "cannot find context" in message
        )

    async def _mark_closed(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._session.mark_closed()
        self._stealth.cleanup()
        for event, handler in self._client_handlers:
            self._client.off(event, handler)
        await self._emitter.emit("close", self)

    def _raise_if_closed(self) -> None:
        if self._closed:
            raise TargetClosedError("Page is closed")
