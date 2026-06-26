from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any, cast

from noctra_browser.cdp.domains import NetworkDomain
from noctra_browser.cdp.session import CdpSession
from noctra_browser.types.public import Cookie, SameSite
from noctra_browser.utils.async_utils import maybe_await
from noctra_browser.utils.errors import NoctraError


class CookieManager:
    def __init__(
        self,
        session: CdpSession,
        current_url: Callable[[], str | Awaitable[str]],
    ) -> None:
        self._session = session
        self._current_url = current_url

    async def cookies(self) -> list[Cookie]:
        result = await self._session.send(NetworkDomain.GET_COOKIES)
        raw_cookies = result.get("cookies", [])
        if not isinstance(raw_cookies, list):
            return []
        return [self._from_cdp(cookie) for cookie in raw_cookies if isinstance(cookie, dict)]

    async def set_cookies(self, cookies: Sequence[Cookie]) -> None:
        cdp_cookies = [await self._to_cdp(cookie) for cookie in cookies]
        await self._session.send(NetworkDomain.SET_COOKIES, {"cookies": cdp_cookies})

    def _from_cdp(self, cookie: dict[str, Any]) -> Cookie:
        expires = cookie.get("expires")
        return Cookie(
            name=str(cookie.get("name", "")),
            value=str(cookie.get("value", "")),
            domain=str(cookie.get("domain")) if cookie.get("domain") is not None else None,
            path=str(cookie.get("path", "/")),
            expires=float(expires) if isinstance(expires, int | float) and expires >= 0 else None,
            http_only=bool(cookie.get("httpOnly", False)),
            secure=bool(cookie.get("secure", False)),
            same_site=self._same_site(cookie.get("sameSite")),
        )

    async def _to_cdp(self, cookie: Cookie) -> dict[str, Any]:
        cdp_cookie: dict[str, Any] = {
            "name": cookie.name,
            "value": cookie.value,
            "path": cookie.path,
            "httpOnly": cookie.http_only,
            "secure": cookie.secure,
        }
        if cookie.domain is not None:
            cdp_cookie["domain"] = cookie.domain
        else:
            url = await maybe_await(self._current_url())
            if not url or url.startswith(("about:", "data:", "chrome:")):
                raise NoctraError(
                    f"Cannot set cookie {cookie.name!r}: provide a domain or navigate "
                    "to a page first (current URL is not a valid cookie origin)"
                )
            cdp_cookie["url"] = url
        if cookie.expires is not None:
            cdp_cookie["expires"] = cookie.expires
        if cookie.same_site is not None:
            cdp_cookie["sameSite"] = cookie.same_site
        return cdp_cookie

    def _same_site(self, value: object) -> SameSite | None:
        if value in {"Strict", "Lax", "None"}:
            return cast(SameSite, value)
        return None
