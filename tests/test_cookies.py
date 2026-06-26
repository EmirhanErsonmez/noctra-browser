from __future__ import annotations

import pytest

from noctra_browser.cookies.manager import CookieManager
from noctra_browser.types.public import Cookie
from noctra_browser.utils.errors import NoctraError


def _manager(url: str) -> CookieManager:
    return CookieManager(session=None, current_url=lambda: url)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_to_cdp_uses_domain_when_present() -> None:
    manager = _manager("about:blank")
    cdp = await manager._to_cdp(Cookie(name="a", value="b", domain="example.com"))

    assert cdp["domain"] == "example.com"
    assert "url" not in cdp


@pytest.mark.asyncio
async def test_to_cdp_uses_current_url_when_no_domain() -> None:
    manager = _manager("https://example.com/path")
    cdp = await manager._to_cdp(Cookie(name="a", value="b"))

    assert cdp["url"] == "https://example.com/path"


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["", "about:blank", "data:text/html,x", "chrome://newtab"])
async def test_to_cdp_rejects_invalid_origin_without_domain(url: str) -> None:
    manager = _manager(url)
    with pytest.raises(NoctraError):
        await manager._to_cdp(Cookie(name="a", value="b"))
