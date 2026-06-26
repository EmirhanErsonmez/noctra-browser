from __future__ import annotations

from typing import Any

from noctra_browser.cdp.domains import PageDomain, RuntimeDomain
from noctra_browser.cdp.session import CdpSession
from noctra_browser.runtime.serialization import json_argument, remote_object_to_python
from noctra_browser.utils.errors import CdpError
from noctra_browser.utils.json import json_dumps

_ISOLATED_WORLD_NAME = "__noctra_world__"


class RuntimeEvaluator:
    def __init__(self, session: CdpSession, *, isolated: bool = True) -> None:
        self._session = session
        self._isolated = isolated
        self._context_id: int | None = None
        self._frame_id: str | None = None

    @property
    def isolated(self) -> bool:
        return self._isolated

    def reset_context(self) -> None:
        self._context_id = None

    def set_frame(self, frame_id: str) -> None:
        if frame_id != self._frame_id:
            self._frame_id = frame_id
            self._context_id = None

    async def execution_context_id(self) -> int | None:
        if not self._isolated:
            return None
        return await self._ensure_context()

    async def evaluate(self, expression_or_function: str, *args: Any) -> Any:
        expression = self._wrap_expression(expression_or_function, args)
        params: dict[str, Any] = {
            "expression": expression,
            "awaitPromise": True,
            "returnByValue": True,
            "userGesture": True,
        }
        if self._isolated:
            params["contextId"] = await self._ensure_context()
        result = await self._session.send(RuntimeDomain.EVALUATE, params)
        self._raise_for_exception_details(RuntimeDomain.EVALUATE, result)
        remote_object = result.get("result")
        if not isinstance(remote_object, dict):
            raise CdpError(
                RuntimeDomain.EVALUATE, -32000, "CDP response missing 'result' field", None
            )
        return remote_object_to_python(remote_object)

    async def call_function_on(self, object_id: str, function_declaration: str, *args: Any) -> Any:
        result = await self._session.send(
            RuntimeDomain.CALL_FUNCTION_ON,
            {
                "objectId": object_id,
                "functionDeclaration": function_declaration,
                "arguments": [json_argument(arg) for arg in args],
                "awaitPromise": True,
                "returnByValue": True,
                "userGesture": True,
            },
        )
        self._raise_for_exception_details(RuntimeDomain.CALL_FUNCTION_ON, result)
        remote_object = result.get("result")
        if not isinstance(remote_object, dict):
            raise CdpError(
                RuntimeDomain.CALL_FUNCTION_ON, -32000, "CDP response missing 'result' field", None
            )
        return remote_object_to_python(remote_object)

    async def _ensure_context(self) -> int:
        if self._context_id is not None:
            return self._context_id
        frame_id = self._frame_id or await self._main_frame_id()
        result = await self._session.send(
            PageDomain.CREATE_ISOLATED_WORLD,
            {
                "frameId": frame_id,
                "worldName": _ISOLATED_WORLD_NAME,
                "grantUniversalAccess": True,
            },
        )
        context_id = result.get("executionContextId")
        if not isinstance(context_id, int):
            raise CdpError(
                PageDomain.CREATE_ISOLATED_WORLD,
                -32000,
                "Could not create isolated execution context",
                None,
            )
        self._context_id = context_id
        self._frame_id = frame_id
        return context_id

    async def _main_frame_id(self) -> str:
        result = await self._session.send(PageDomain.GET_FRAME_TREE)
        frame_tree = result.get("frameTree", {})
        frame = frame_tree.get("frame", {}) if isinstance(frame_tree, dict) else {}
        frame_id = frame.get("id") if isinstance(frame, dict) else None
        if not isinstance(frame_id, str):
            raise CdpError(
                PageDomain.GET_FRAME_TREE, -32000, "Could not resolve main frame id", None
            )
        return frame_id

    def _wrap_expression(self, expression_or_function: str, args: tuple[Any, ...]) -> str:
        source = expression_or_function.strip()
        if not args and not self._looks_like_function(source):
            return source
        # Evaluate the source once, then invoke it with the args only if it turns
        # out to be callable. This matches the page.evaluate(fn, ...args) contract
        # while leaving already-invoked IIFEs and plain expressions untouched.
        encoded_args = json_dumps(list(args))
        return (
            "(async () => {"
            f"const __noctra_v = ({source});"
            f"return await (typeof __noctra_v === 'function'"
            f" ? __noctra_v(...{encoded_args}) : __noctra_v);"
            "})()"
        )

    def _looks_like_function(self, source: str) -> bool:
        if source.startswith(("function", "async function")):
            return True
        return source.startswith(("(", "async (", "async(")) and "=>" in source

    def _raise_for_exception_details(self, method: str, result: dict[str, Any]) -> None:
        exception = result.get("exceptionDetails")
        if not isinstance(exception, dict):
            return
        raw_exception = exception.get("exception", {})
        exception_description = (
            raw_exception.get("description") if isinstance(raw_exception, dict) else None
        )
        text = exception.get("text") or exception_description
        raise CdpError(method, -32000, str(text or "JavaScript evaluation failed"), exception)
