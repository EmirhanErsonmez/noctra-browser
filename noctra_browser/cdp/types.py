from __future__ import annotations

from dataclasses import dataclass
from typing import Any

JsonObject = dict[str, Any]


@dataclass(slots=True, frozen=True)
class CdpEvent:
    method: str
    params: JsonObject
    session_id: str | None = None
