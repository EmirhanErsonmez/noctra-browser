from __future__ import annotations

from noctra_browser.browser.browser import Browser
from noctra_browser.browser.launcher import BrowserLauncher, LaunchOptions
from noctra_browser.cdp.client import CdpClient
from noctra_browser.stealth.config import StealthConfig
from noctra_browser.types.public import Viewport


def _resolve_stealth(stealth: StealthConfig | bool | None) -> StealthConfig | None:
    if stealth is None or stealth is False:
        return None
    if stealth is True:
        return StealthConfig()
    return stealth


async def launch(
    *,
    headless: bool = True,
    executable_path: str | None = None,
    user_data_dir: str | None = None,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    timeout: float = 30.0,
    viewport: Viewport | None = None,
    stealth: StealthConfig | bool | None = True,
) -> Browser:
    stealth_config = _resolve_stealth(stealth)
    options = LaunchOptions(
        headless=headless,
        executable_path=executable_path,
        user_data_dir=user_data_dir,
        args=args,
        env=env,
        timeout=timeout,
        viewport=viewport,
        stealth=stealth_config is not None,
    )
    launched = await BrowserLauncher().launch(options)
    client = CdpClient(launched.websocket_url, timeout=timeout)
    try:
        await client.connect()
        browser = Browser(
            client,
            process=launched.process,
            viewport=viewport,
            stealth=stealth_config,
        )
        await browser.initialize()
        return browser
    except Exception:
        await client.close()
        await launched.process.close()
        raise


async def connect(
    websocket_url: str,
    *,
    timeout: float = 30.0,
    stealth: StealthConfig | bool | None = None,
) -> Browser:
    stealth_config = _resolve_stealth(stealth)
    client = CdpClient(websocket_url, timeout=timeout)
    await client.connect()
    browser = Browser(client, stealth=stealth_config)
    await browser.initialize()
    return browser
