from __future__ import annotations

from typing import Any


class NoctraError(Exception):
    """Base class for all Noctra Browser errors."""


class TimeoutError(NoctraError):
    """Raised when an operation exceeds its timeout."""


class BrowserLaunchError(NoctraError):
    """Raised when a browser process cannot be launched."""


class BrowserConnectionError(NoctraError):
    """Raised when the CDP connection cannot be established or is lost."""


class CdpError(NoctraError):
    """Raised when Chrome DevTools Protocol returns an error response."""

    def __init__(
        self,
        method: str,
        code: int,
        message: str,
        data: Any | None = None,
    ) -> None:
        self.method = method
        self.code = code
        self.message = message
        self.data = data
        detail = f"CDP command {method!r} failed with code {code}: {message}"
        if data is not None:
            detail = f"{detail} ({data!r})"
        super().__init__(detail)


class TargetClosedError(NoctraError):
    """Raised when an operation targets a closed page, browser, or CDP session."""


class SelectorError(NoctraError):
    """Raised when a selector is invalid or unsupported."""
