from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SelectorKind = Literal["css"]


@dataclass(slots=True, frozen=True)
class ParsedSelector:
    kind: SelectorKind
    value: str
