from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class TargetInfo:
    target_id: str
    type: str
    title: str
    url: str
    attached: bool

    @classmethod
    def from_cdp(cls, payload: dict[str, Any]) -> TargetInfo:
        return cls(
            target_id=str(payload.get("targetId", "")),
            type=str(payload.get("type", "")),
            title=str(payload.get("title", "")),
            url=str(payload.get("url", "")),
            attached=bool(payload.get("attached", False)),
        )
