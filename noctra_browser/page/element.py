from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from noctra_browser.cdp.domains import DomDomain, RuntimeDomain
from noctra_browser.utils.errors import CdpError, SelectorError

if TYPE_CHECKING:
    from noctra_browser.page.page import Page


class ElementHandle:
    def __init__(self, page: Page, node_id: int) -> None:
        self._page = page
        self.node_id = node_id

    async def click(self, timeout: float = 30.0) -> None:
        self._page._raise_if_closed()
        await self._call_js(
            "function() { this.scrollIntoView({block: 'center', inline: 'center'}); return null; }"
        )
        x, y = await self._box_center()
        await self._page._mouse.click(x, y)

    async def type(
        self, text: str, delay: float = 0, timeout: float = 30.0, human: bool = False
    ) -> None:
        await self.click(timeout=timeout)
        await self._page._keyboard.type_text(text, delay=delay, human=human)

    async def fill(self, text: str, timeout: float = 30.0) -> None:
        await self.click(timeout=timeout)
        await self._call_js("function() { this.value = ''; }")
        await self._page._keyboard.insert_text(text)

    async def press(self, key: str, timeout: float = 30.0) -> None:
        await self.click(timeout=timeout)
        await self._page._keyboard.press(key)

    async def text(self) -> str:
        value = await self._call_js("function() { return this.textContent || ''; }")
        return str(value)

    async def html(self) -> str:
        value = await self._call_js("function() { return this.outerHTML || ''; }")
        return str(value)

    async def attribute(self, name: str) -> str | None:
        value = await self._call_js("function(name) { return this.getAttribute(name); }", name)
        return str(value) if value is not None else None

    async def exists(self) -> bool:
        try:
            await self._page._session.send(DomDomain.DESCRIBE_NODE, {"nodeId": self.node_id})
        except CdpError as exc:
            if "node" in exc.message.lower():
                return False
            raise
        return True

    async def evaluate(self, expression_or_function: str, *args: Any) -> Any:
        object_id = await self._remote_object_id()
        source = expression_or_function.strip()
        if "=>" in source or source.startswith(("function", "async function", "async (")):
            declaration = (
                "async function(...args) {"
                f"const __noctra_fn = {source};"
                "return await __noctra_fn(this, ...args);"
                "}"
            )
        else:
            declaration = (
                "async function(...args) {"
                f"return await (async function() {{ return ({source}); }}).call(this);"
                "}"
            )
        try:
            return await self._page._evaluator.call_function_on(object_id, declaration, *args)
        finally:
            await self._release_object(object_id)

    async def is_visible(self) -> bool:
        try:
            value = await self._call_js(
                """
                function() {
                    let el = this;
                    while (el && el !== document.documentElement) {
                        const style = window.getComputedStyle(el);
                        if (
                            style.display === 'none'
                            || style.visibility === 'hidden'
                            || parseFloat(style.opacity) === 0
                        ) {
                            return false;
                        }
                        el = el.parentElement;
                    }
                    const rect = this.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                }
                """
            )
        except CdpError as exc:
            if "node" in exc.message.lower():
                return False
            raise
        return bool(value)

    async def _call_js(self, function_declaration: str, *args: Any) -> Any:
        object_id = await self._remote_object_id()
        try:
            return await self._page._evaluator.call_function_on(
                object_id,
                function_declaration,
                *args,
            )
        finally:
            await self._release_object(object_id)

    async def _remote_object_id(self) -> str:
        self._page._raise_if_closed()
        params: dict[str, Any] = {"nodeId": self.node_id}
        context_id = await self._page._evaluator.execution_context_id()
        if context_id is not None:
            params["executionContextId"] = context_id
        result = await self._page._session.send(DomDomain.RESOLVE_NODE, params)
        remote_object = result.get("object", {})
        object_id = remote_object.get("objectId") if isinstance(remote_object, dict) else None
        if not isinstance(object_id, str):
            raise SelectorError("Could not resolve element handle")
        return object_id

    async def _release_object(self, object_id: str) -> None:
        with contextlib.suppress(CdpError):
            await self._page._session.send(RuntimeDomain.RELEASE_OBJECT, {"objectId": object_id})

    async def _box_center(self) -> tuple[float, float]:
        result = await self._page._session.send(DomDomain.GET_BOX_MODEL, {"nodeId": self.node_id})
        model = result.get("model", {})
        if not isinstance(model, dict):
            raise SelectorError("Element does not have a box model")
        content = model.get("content", [])
        if not isinstance(content, list) or len(content) < 8:
            raise SelectorError("Element is not visible")
        x = sum(float(content[index]) for index in range(0, 8, 2)) / 4
        y = sum(float(content[index]) for index in range(1, 8, 2)) / 4
        return x, y
