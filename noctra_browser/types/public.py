from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ScreenshotType = Literal["png", "jpeg"]
LoadState = Literal["load", "domcontentloaded", "networkidle"]
SelectorState = Literal["attached", "detached", "visible", "hidden"]
SameSite = Literal["Strict", "Lax", "None"]


@dataclass(slots=True, frozen=True)
class Viewport:
    width: int
    height: int
    device_scale_factor: float = 1.0
    is_mobile: bool = False

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError(
                f"Viewport dimensions must be positive, got {self.width}x{self.height}"
            )
        if self.device_scale_factor <= 0:
            raise ValueError(
                f"device_scale_factor must be positive, got {self.device_scale_factor}"
            )


@dataclass(slots=True, frozen=True)
class Cookie:
    name: str
    value: str
    domain: str | None = None
    path: str = "/"
    expires: float | None = None
    http_only: bool = False
    secure: bool = False
    same_site: SameSite | None = None


@dataclass(slots=True, frozen=True)
class Request:
    url: str
    method: str
    headers: dict[str, str] = field(default_factory=dict)
    resource_type: str | None = None


@dataclass(slots=True, frozen=True)
class Response:
    url: str
    status: int
    status_text: str
    headers: dict[str, str] = field(default_factory=dict)
    mime_type: str | None = None


@dataclass(slots=True, frozen=True)
class ConsoleMessage:
    type: str
    text: str
    location: dict[str, object] | None = None
