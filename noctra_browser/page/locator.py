from __future__ import annotations

from typing import Protocol

from noctra_browser.page.element import ElementHandle
from noctra_browser.utils.async_utils import wait_for_condition
from noctra_browser.utils.errors import SelectorError


class _PageLike(Protocol):
    async def query(self, selector: str) -> ElementHandle | None: ...

    async def query_all(self, selector: str) -> list[ElementHandle]: ...

    def is_closed(self) -> bool: ...


class Locator:
    def __init__(self, page: _PageLike, selector: str) -> None:
        self._page = page
        self.selector = selector

    async def click(self, timeout: float = 30.0) -> None:
        element = await self._resolve(timeout=timeout)
        await element.click(timeout=timeout)

    async def type(self, text: str, delay: float = 0, timeout: float = 30.0) -> None:
        element = await self._resolve(timeout=timeout)
        await element.type(text, delay=delay, timeout=timeout)

    async def press(self, key: str, timeout: float = 30.0) -> None:
        element = await self._resolve(timeout=timeout)
        await element.press(key, timeout=timeout)

    async def text(self, timeout: float = 30.0) -> str:
        element = await self._resolve(timeout=timeout)
        return await element.text()

    async def html(self, timeout: float = 30.0) -> str:
        element = await self._resolve(timeout=timeout)
        return await element.html()

    async def attribute(self, name: str, timeout: float = 30.0) -> str | None:
        element = await self._resolve(timeout=timeout)
        return await element.attribute(name)

    async def exists(self) -> bool:
        element = await self._page.query(self.selector)
        return element is not None and await element.exists()

    async def count(self) -> int:
        elements = await self._page.query_all(self.selector)
        return len(elements)

    async def first(self, timeout: float = 30.0) -> ElementHandle:
        return await self._resolve(timeout=timeout, index=0)

    async def nth(self, index: int, timeout: float = 30.0) -> ElementHandle:
        if index < 0:
            raise SelectorError("Locator index must be greater than or equal to zero")
        return await self._resolve(timeout=timeout, index=index)

    async def _resolve(self, *, timeout: float, index: int = 0) -> ElementHandle:
        async def find_element() -> ElementHandle | None:
            elements = await self._page.query_all(self.selector)
            if len(elements) > index:
                return elements[index]
            return None

        return await wait_for_condition(
            find_element,
            timeout=timeout,
            timeout_message=(
                f"Timed out after {timeout:.1f}s while waiting for selector {self.selector!r}"
            ),
            closed_check=self._page.is_closed,
        )
