from __future__ import annotations

import re

from noctra_browser.cdp.domains import (
    EmulationDomain,
    NetworkDomain,
    PageDomain,
    RuntimeDomain,
    TargetDomain,
)
from noctra_browser.cdp.session import CdpSession
from noctra_browser.cdp.types import CdpEvent
from noctra_browser.stealth.config import StealthConfig
from noctra_browser.stealth.evasions import build_evasion_scripts
from noctra_browser.utils.events import EventHandler

_HEADLESS_PATTERN = re.compile(r"HeadlessChrome", re.IGNORECASE)
_WORKER_TYPES = {"worker", "shared_worker", "service_worker"}
_WINDOW_REF = re.compile(r"\bwindow\b")


def _to_worker_scope(script: str) -> str:
    # Workers expose globals on `self`/`globalThis`, not `window`. Rewriting the
    # reference lets the same evasion source run in both scopes; evasions that
    # touch DOM-only globals already self-guard with `if (!proto) return`.
    return _WINDOW_REF.sub("globalThis", script)


class StealthManager:
    def __init__(self, session: CdpSession, config: StealthConfig) -> None:
        self._session = session
        self._config = config
        self._script_ids: list[str] = []
        self._scripts: list[str] = []
        self._worker_listener: EventHandler | None = None
        self._handled_workers: set[str] = set()

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def cleanup(self) -> None:
        # Called when the owning page closes so the browser-level worker listener
        # is not left attached for the lifetime of the connection.
        if self._worker_listener is not None:
            self._session.off_event(TargetDomain.ATTACHED_TO_TARGET, self._worker_listener)
            self._worker_listener = None
        self._handled_workers.clear()

    async def apply(self, user_agent: str | None) -> None:
        if not self._config.enabled:
            return
        if self._config.user_agent_override:
            await self._apply_user_agent(user_agent)
        self._scripts = build_evasion_scripts(self._config)
        for script in self._scripts:
            result = await self._session.send(
                PageDomain.ADD_SCRIPT_TO_EVALUATE_ON_NEW_DOCUMENT,
                {"source": script, "runImmediately": True},
            )
            identifier = result.get("identifier")
            if isinstance(identifier, str):
                self._script_ids.append(identifier)
        if self._config.spoof_workers:
            await self._enable_worker_spoofing()

    async def _enable_worker_spoofing(self) -> None:
        self._worker_listener = self._handle_attached_worker
        self._session.on_event(TargetDomain.ATTACHED_TO_TARGET, self._worker_listener)
        await self._session.send(
            TargetDomain.SET_AUTO_ATTACH,
            {"autoAttach": True, "waitForDebuggerOnStart": True, "flatten": True},
        )

    async def _handle_attached_worker(self, payload: object) -> None:
        if self._session.is_closed() or not isinstance(payload, CdpEvent):
            return
        target_info = payload.params.get("targetInfo")
        worker_session_id = payload.params.get("sessionId")
        if not isinstance(target_info, dict) or not isinstance(worker_session_id, str):
            return
        if target_info.get("type") not in _WORKER_TYPES:
            return
        # ATTACHED_TO_TARGET is dispatched on the shared client, so several pages'
        # managers see the same event; skip sessions already handled by this one.
        if worker_session_id in self._handled_workers:
            return
        self._handled_workers.add(worker_session_id)
        worker = CdpSession(self._session.client, worker_session_id)
        for script in self._scripts:
            await self._safe_evaluate(worker, _to_worker_scope(script))
        await self._safe_send(worker, RuntimeDomain.RUN_IF_WAITING_FOR_DEBUGGER, None)

    async def _safe_evaluate(self, worker: CdpSession, script: str) -> None:
        await self._safe_send(worker, RuntimeDomain.EVALUATE, {"expression": script})

    async def _safe_send(
        self, worker: CdpSession, method: str, params: dict[str, object] | None
    ) -> None:
        try:
            await worker.send(method, params)
        except Exception:
            # A dead or detached worker target must not break the page.
            return

    async def _apply_user_agent(self, user_agent: str | None) -> None:
        resolved = user_agent or await self._detect_user_agent()
        if resolved is None:
            return
        cleaned = _HEADLESS_PATTERN.sub("Chrome", resolved)
        override = {
            "userAgent": cleaned,
            "acceptLanguage": ",".join(self._config.languages),
            "platform": self._config.platform,
        }
        await self._session.send(NetworkDomain.SET_USER_AGENT_OVERRIDE, override)
        await self._session.send(EmulationDomain.SET_USER_AGENT_OVERRIDE, override)

    async def _detect_user_agent(self) -> str | None:
        result = await self._session.send("Browser.getVersion")
        user_agent = result.get("userAgent")
        return user_agent if isinstance(user_agent, str) else None
