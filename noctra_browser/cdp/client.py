from __future__ import annotations

import asyncio
import contextlib
import itertools
from dataclasses import dataclass
from types import TracebackType
from typing import Any, cast

import websockets

from noctra_browser.cdp.types import CdpEvent, JsonObject
from noctra_browser.utils.errors import (
    BrowserConnectionError,
    CdpError,
    NoctraError,
    TargetClosedError,
)
from noctra_browser.utils.errors import (
    TimeoutError as NoctraTimeoutError,
)
from noctra_browser.utils.events import EventEmitter, EventHandler
from noctra_browser.utils.json import json_dumps, json_loads


@dataclass(slots=True)
class _PendingCommand:
    method: str
    session_id: str | None
    future: asyncio.Future[JsonObject]


class CdpClient:
    def __init__(self, websocket_url: str, *, timeout: float = 30.0) -> None:
        self.websocket_url = websocket_url
        self.timeout = timeout
        self._websocket: Any | None = None
        self._id_counter = itertools.count(1)
        self._pending: dict[int, _PendingCommand] = {}
        self._emitter = EventEmitter()
        self._reader_task: asyncio.Task[None] | None = None
        self._event_tasks: set[asyncio.Task[None]] = set()
        self._connected = False
        self._closing = False

    async def __aenter__(self) -> CdpClient:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def connect(self) -> None:
        if self._connected:
            return
        connect = cast(Any, websockets.connect)
        try:
            self._websocket = await connect(
                self.websocket_url,
                max_size=None,
                ping_interval=20,
                open_timeout=self.timeout,
            )
        except Exception as exc:
            raise BrowserConnectionError(
                f"Could not connect to CDP websocket {self.websocket_url!r}"
            ) from exc
        self._connected = True
        self._closing = False
        self._reader_task = asyncio.create_task(self._reader_loop())

    async def send(
        self,
        method: str,
        params: JsonObject | None = None,
        *,
        session_id: str | None = None,
        timeout: float = 30.0,
    ) -> JsonObject:
        if not self._connected or self._websocket is None:
            raise BrowserConnectionError("CDP client is not connected")

        command_id = next(self._id_counter)

        message: JsonObject = {"id": command_id, "method": method}
        if params:
            message["params"] = params
        if session_id is not None:
            message["sessionId"] = session_id

        loop = asyncio.get_running_loop()
        future: asyncio.Future[JsonObject] = loop.create_future()
        self._pending[command_id] = _PendingCommand(
            method=method,
            session_id=session_id,
            future=future,
        )

        try:
            await self._websocket.send(json_dumps(message))
            return await asyncio.wait_for(future, timeout=timeout)
        except TimeoutError as exc:
            self._pending.pop(command_id, None)
            raise NoctraTimeoutError(
                f"Timed out after {timeout:.1f}s while waiting for CDP command {method!r}"
            ) from exc
        except NoctraError:
            self._pending.pop(command_id, None)
            raise
        except Exception as exc:
            self._pending.pop(command_id, None)
            raise BrowserConnectionError(f"Failed to send CDP command {method!r}") from exc

    def on(self, event: str, handler: EventHandler) -> None:
        self._emitter.on(event, handler)

    def off(self, event: str, handler: EventHandler) -> None:
        self._emitter.off(event, handler)

    def is_connected(self) -> bool:
        return self._connected

    async def close(self) -> None:
        if self._closing:
            return
        self._closing = True
        websocket = self._websocket
        if websocket is not None:
            with contextlib.suppress(Exception):
                await websocket.close()

        current_task = asyncio.current_task()
        if self._reader_task is not None and self._reader_task is not current_task:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader_task

        for task in list(self._event_tasks):
            task.cancel()
        if self._event_tasks:
            await asyncio.gather(*self._event_tasks, return_exceptions=True)

        self._connected = False
        self._websocket = None
        self._fail_pending(BrowserConnectionError("CDP connection closed"))

    async def _reader_loop(self) -> None:
        disconnect_error: BrowserConnectionError | None = None
        try:
            websocket = self._websocket
            if websocket is None:
                raise BrowserConnectionError("CDP websocket is not available")
            async for raw_message in websocket:
                parsed = json_loads(raw_message)
                if isinstance(parsed, dict):
                    await self._handle_message(cast(JsonObject, parsed))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if not self._closing:
                disconnect_error = BrowserConnectionError("CDP connection lost")
                disconnect_error.__cause__ = exc
        finally:
            self._connected = False
            if not self._closing:
                error = disconnect_error or BrowserConnectionError("CDP connection closed")
                self._fail_pending(error)
                self._schedule_event("disconnected", error)

    async def _handle_message(self, message: JsonObject) -> None:
        command_id = message.get("id")
        if isinstance(command_id, int):
            pending = self._pending.pop(command_id, None)
            if pending is None or pending.future.done():
                return

            error = message.get("error")
            if isinstance(error, dict):
                code = error.get("code", -32000)
                text = error.get("message", "CDP command failed")
                pending.future.set_exception(
                    CdpError(
                        pending.method,
                        int(code) if isinstance(code, int) else -32000,
                        str(text),
                        error.get("data"),
                    )
                )
                return

            result = message.get("result")
            pending.future.set_result(cast(JsonObject, result if isinstance(result, dict) else {}))
            return

        method = message.get("method")
        if isinstance(method, str):
            params = message.get("params")
            session_id = message.get("sessionId")
            event_params = cast(JsonObject, params if isinstance(params, dict) else {})
            if method == "Target.detachedFromTarget":
                detached_session_id = event_params.get("sessionId")
                if isinstance(detached_session_id, str):
                    self._fail_pending_for_session(
                        detached_session_id,
                        TargetClosedError(f"CDP session {detached_session_id!r} closed"),
                    )
            event = CdpEvent(
                method=method,
                params=event_params,
                session_id=session_id if isinstance(session_id, str) else None,
            )
            self._schedule_event(method, event)
            self._schedule_event("event", event)

    def _schedule_event(self, event: str, payload: object) -> None:
        task = asyncio.create_task(self._emitter.emit(event, payload))
        self._event_tasks.add(task)
        task.add_done_callback(lambda done: self._event_tasks.discard(done))

    def _fail_pending(self, error: Exception) -> None:
        for pending in self._pending.values():
            if not pending.future.done():
                pending.future.set_exception(error)
        self._pending.clear()

    def _fail_pending_for_session(self, session_id: str, error: Exception) -> None:
        for command_id, pending in list(self._pending.items()):
            if pending.session_id != session_id:
                continue
            if not pending.future.done():
                pending.future.set_exception(error)
            self._pending.pop(command_id, None)
