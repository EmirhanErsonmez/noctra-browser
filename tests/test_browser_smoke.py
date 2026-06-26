from __future__ import annotations

from urllib.parse import quote

import pytest

from noctra_browser import Viewport, launch
from noctra_browser.utils.errors import BrowserLaunchError
from noctra_browser.utils.paths import find_chrome_executable


async def test_real_browser_page_flow_smoke() -> None:
    executable = find_chrome_executable()
    if executable is None:
        pytest.skip("Chrome or Chromium executable is not available")

    html = """
    <!doctype html>
    <html>
      <head><title>Noctra Smoke</title></head>
      <body>
        <h1 data-kind="main">Ready</h1>
        <input id="name">
      </body>
    </html>
    """
    url = "data:text/html," + quote(html)

    try:
        browser = await launch(
            headless=True,
            executable_path=executable,
            viewport=Viewport(width=800, height=600),
            timeout=15.0,
        )
    except BrowserLaunchError as exc:
        pytest.skip(f"Browser launch smoke test skipped: {exc}")

    async with browser:
        page = await browser.new_page()
        await page.goto(url, wait_until="load", timeout=10.0)

        assert await page.title() == "Noctra Smoke"
        assert await page.locator("h1").text() == "Ready"
        assert await page.locator("h1").attribute("data-kind") == "main"

        await page.type("#name", "noctra")
        assert await page.evaluate("document.querySelector('#name').value") == "noctra"
        assert await page.evaluate("(a, b) => a + b", 20, 22) == 42

        screenshot = await page.screenshot()
        assert screenshot.startswith(b"\x89PNG")
