from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from noctra_browser.utils.errors import TargetClosedError, TimeoutError

T = TypeVar("T")
Condition = Callable[[], T | None | Awaitable[T | None]]
ClosedCheck = Callable[[], bool | Awaitable[bool]]


async def maybe_await(value: T | Awaitable[T]) -> T:
    if inspect.isawaitable(value):
        return await value
    return value


async def wait_for_condition(
    condition: Condition[T],
    *,
    timeout: float,
    interval: float = 0.05,
    timeout_message: str,
    closed_check: ClosedCheck | None = None,
) -> T:
    deadline = time.monotonic() + timeout
    while True:
        if closed_check is not None and await maybe_await(closed_check()):
            raise TargetClosedError("Target closed while waiting")

        result = await maybe_await(condition())
        if result is not None and result is not False:
            return result

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(timeout_message)
        await asyncio.sleep(min(interval, remaining))
