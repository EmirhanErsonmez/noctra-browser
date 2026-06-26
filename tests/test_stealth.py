from __future__ import annotations

import inspect

from noctra_browser.stealth.config import StealthConfig
from noctra_browser.stealth.evasions import build_evasion_scripts
from noctra_browser.stealth.manager import _to_worker_scope


def test_disabled_config_produces_no_scripts() -> None:
    assert build_evasion_scripts(StealthConfig.disabled()) == []


def test_enabled_config_includes_core_evasions() -> None:
    scripts = build_evasion_scripts(StealthConfig())
    joined = "\n".join(scripts)

    assert "__noctra" in joined
    assert "'webdriver'" in joined
    assert "PluginArray" in joined
    assert "window.chrome" in joined
    assert "Permissions.prototype" in joined
    assert "getParameter" in joined
    assert "getImageData" in joined
    assert "getFloatFrequencyData" in joined


def test_evasions_never_use_proxy() -> None:
    # Proxies are detectable through the prototype-chain ownKeys inspector leak,
    # so no evasion may construct one.
    joined = "\n".join(build_evasion_scripts(StealthConfig()))
    assert "new Proxy" not in joined


def test_navigator_overrides_reflect_config() -> None:
    config = StealthConfig(
        languages=("tr-TR", "tr"),
        vendor="Custom Vendor",
        platform="Linux x86_64",
        hardware_concurrency=16,
        device_memory=32,
    )
    joined = "\n".join(build_evasion_scripts(config))

    assert '["tr-TR","tr"]' in joined
    assert "Custom Vendor" in joined
    assert "Linux x86_64" in joined
    assert "'hardwareConcurrency', 16" in joined
    assert "'deviceMemory', 32" in joined


def test_selective_disable_removes_only_target_evasion() -> None:
    config = StealthConfig(webgl_vendor=False, window_chrome=False)
    joined = "\n".join(build_evasion_scripts(config))

    assert "window.chrome" not in joined
    assert "getParameter" not in joined
    assert "'webdriver'" in joined


def test_extra_evasions_are_appended() -> None:
    marker = "/* custom-evasion-marker */"
    config = StealthConfig(extra_evasions=(marker,))
    scripts = build_evasion_scripts(config)

    assert scripts[-1] == marker


def test_worker_scope_rewrites_window_to_globalthis() -> None:
    source = "const x = window['__noctra']; window.foo = 1;"
    rewritten = _to_worker_scope(source)

    assert "window" not in rewritten
    assert "globalThis['__noctra']" in rewritten
    assert "globalThis.foo = 1" in rewritten


def test_navigator_spoof_uses_runtime_prototype_for_worker_compatibility() -> None:
    # Resolving the prototype at runtime keeps the same evasion valid for both
    # Navigator.prototype (window) and WorkerNavigator.prototype (worker).
    joined = "\n".join(build_evasion_scripts(StealthConfig()))
    assert "Object.getPrototypeOf(navigator)" in joined


def test_isolated_world_uses_correct_cdp_parameter_name() -> None:
    # The CDP parameter is grantUniversalAccess; a typo silently drops the grant.
    from noctra_browser.runtime import evaluator

    source = inspect.getsource(evaluator)
    assert "grantUniversalAccess" in source
    assert "grantUniveralAccess" not in source


class _RecordingSession:
    def __init__(self) -> None:
        self.events: dict[str, list[object]] = {}
        self._closed = False
        self.session_id = "page-session"

    @property
    def client(self) -> object:
        return self

    def on_event(self, method: str, handler: object) -> None:
        self.events.setdefault(method, []).append(handler)

    def off_event(self, method: str, handler: object) -> None:
        if handler in self.events.get(method, []):
            self.events[method].remove(handler)

    def is_closed(self) -> bool:
        return self._closed


def test_cleanup_removes_worker_listener() -> None:
    from noctra_browser.cdp.domains import TargetDomain
    from noctra_browser.stealth.manager import StealthManager

    session = _RecordingSession()
    manager = StealthManager(session, StealthConfig())  # type: ignore[arg-type]
    manager._worker_listener = manager._handle_attached_worker
    session.on_event(TargetDomain.ATTACHED_TO_TARGET, manager._worker_listener)

    assert session.events[TargetDomain.ATTACHED_TO_TARGET] == [manager._handle_attached_worker]
    manager.cleanup()
    assert session.events[TargetDomain.ATTACHED_TO_TARGET] == []
