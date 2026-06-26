from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict


class JsonDict(TypedDict, total=False):
    id: int
    method: str
    params: dict[str, Any]
    result: dict[str, Any]
    error: dict[str, Any]
    sessionId: str


@dataclass(slots=True, frozen=True)
class TargetInfo:
    target_id: str
    type: str
    title: str
    url: str
    attached: bool
