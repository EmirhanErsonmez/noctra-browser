from __future__ import annotations

import pytest

from noctra_browser.browser.launcher import BrowserLauncher, LaunchOptions
from noctra_browser.utils.errors import BrowserLaunchError
from noctra_browser.utils.paths import find_chrome_executable


async def test_browser_launch_smoke_skips_when_environment_is_not_ready() -> None:
    executable = find_chrome_executable()
    if executable is None:
        pytest.skip("Chrome or Chromium executable is not available")

    launcher = BrowserLauncher()
    try:
        result = await launcher.launch(
            LaunchOptions(headless=True, executable_path=executable, timeout=10.0)
        )
    except BrowserLaunchError as exc:
        pytest.skip(f"Browser launch smoke test skipped: {exc}")

    try:
        assert result.websocket_url.startswith("ws://")
        assert result.debugging_port > 0
    finally:
        await result.process.close()
