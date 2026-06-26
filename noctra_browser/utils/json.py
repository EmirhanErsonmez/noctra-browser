from __future__ import annotations

import json
from typing import Any


def json_dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def json_loads(value: str | bytes) -> Any:
    return json.loads(value)
