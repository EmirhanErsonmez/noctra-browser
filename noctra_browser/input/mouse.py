from __future__ import annotations

import asyncio
import random

from noctra_browser.cdp.domains import InputDomain
from noctra_browser.cdp.session import CdpSession

_BUTTONS = {"left", "right", "middle", "none"}


class Mouse:
    def __init__(self, session: CdpSession) -> None:
        self._session = session
        self._x = 0.0
        self._y = 0.0

    @property
    def position(self) -> tuple[float, float]:
        return self._x, self._y

    async def move(self, x: float, y: float, *, steps: int = 1) -> None:
        steps = max(1, steps)
        start_x, start_y = self._x, self._y
        for step in range(1, steps + 1):
            ratio = step / steps
            await self._session.send(
                InputDomain.DISPATCH_MOUSE_EVENT,
                {
                    "type": "mouseMoved",
                    "x": start_x + (x - start_x) * ratio,
                    "y": start_y + (y - start_y) * ratio,
                    "button": "none",
                },
            )
        self._x, self._y = x, y

    async def click(
        self,
        x: float,
        y: float,
        *,
        button: str = "left",
        click_count: int = 1,
        delay: float = 0,
        human: bool = True,
    ) -> None:
        if button not in _BUTTONS:
            raise ValueError(f"Unknown mouse button {button!r}")
        steps = random.randint(8, 18) if human else 1
        await self.move(x, y, steps=steps)
        if human:
            await asyncio.sleep(random.uniform(0.01, 0.06))
        await self._dispatch("mousePressed", x, y, button, click_count)
        if delay > 0:
            await asyncio.sleep(delay)
        elif human:
            await asyncio.sleep(random.uniform(0.02, 0.09))
        await self._dispatch("mouseReleased", x, y, button, click_count)

    async def down(self, *, button: str = "left", click_count: int = 1) -> None:
        if button not in _BUTTONS:
            raise ValueError(f"Unknown mouse button {button!r}")
        await self._dispatch("mousePressed", self._x, self._y, button, click_count)

    async def up(self, *, button: str = "left", click_count: int = 1) -> None:
        if button not in _BUTTONS:
            raise ValueError(f"Unknown mouse button {button!r}")
        await self._dispatch("mouseReleased", self._x, self._y, button, click_count)

    async def _dispatch(
        self, event_type: str, x: float, y: float, button: str, click_count: int
    ) -> None:
        await self._session.send(
            InputDomain.DISPATCH_MOUSE_EVENT,
            {
                "type": event_type,
                "x": x,
                "y": y,
                "button": button,
                "clickCount": click_count,
            },
        )
