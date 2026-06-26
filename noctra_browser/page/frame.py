from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from noctra_browser.page.page import Page


@dataclass(slots=True)
class Frame:
    page: Page
    frame_id: str

    async def evaluate(self, expression_or_function: str, *args: Any) -> Any:
        return await self.page.evaluate(expression_or_function, *args)
