from __future__ import annotations

import inspect
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

EventHandler = Callable[[Any], Awaitable[None] | None]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _Listener:
    handler: EventHandler
    once: bool


class EventEmitter:
    def __init__(self) -> None:
        self._listeners: dict[str, list[_Listener]] = defaultdict(list)

    def on(self, event: str, handler: EventHandler) -> None:
        self._listeners[event].append(_Listener(handler=handler, once=False))

    def off(self, event: str, handler: EventHandler) -> None:
        listeners = self._listeners.get(event)
        if not listeners:
            return
        self._listeners[event] = [
            listener for listener in listeners if listener.handler is not handler
        ]
        if not self._listeners[event]:
            del self._listeners[event]

    def once(self, event: str, handler: EventHandler) -> None:
        self._listeners[event].append(_Listener(handler=handler, once=True))

    async def emit(self, event: str, payload: Any = None) -> None:
        listeners = list(self._listeners.get(event, ()))
        if not listeners:
            return
        for listener in listeners:
            if listener.once:
                self.off(event, listener.handler)
            try:
                result = listener.handler(payload)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Unhandled exception in %r event handler", event)
