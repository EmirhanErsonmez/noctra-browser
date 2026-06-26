from __future__ import annotations

import math
from typing import Any


def remote_object_to_python(remote_object: dict[str, Any]) -> Any:
    if "value" in remote_object:
        return remote_object["value"]
    unserializable = remote_object.get("unserializableValue")
    if unserializable == "NaN":
        return math.nan
    if unserializable == "Infinity":
        return math.inf
    if unserializable == "-Infinity":
        return -math.inf
    if unserializable == "-0":
        return -0.0
    if remote_object.get("subtype") == "null":
        return None
    return remote_object.get("description")


def json_argument(value: Any) -> dict[str, Any]:
    return {"value": value}
