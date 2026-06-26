from __future__ import annotations

from noctra_browser.selectors.models import ParsedSelector
from noctra_browser.utils.errors import SelectorError


class SelectorEngine:
    SUPPORTED_PREFIX = "css="

    def parse(self, selector: str) -> ParsedSelector:
        value = selector.strip()
        if not value:
            raise SelectorError("Selector must not be empty")
        if value.startswith(("text=", "xpath=", "role=")):
            prefix = value.split("=", 1)[0]
            raise SelectorError(f"Unsupported selector engine {prefix!r}")
        if value.startswith(self.SUPPORTED_PREFIX):
            value = value[len(self.SUPPORTED_PREFIX) :].strip()
        if not value:
            raise SelectorError("CSS selector must not be empty")
        if not self._looks_like_css(value):
            raise SelectorError(f"Invalid CSS selector {selector!r}")
        return ParsedSelector(kind="css", value=value)

    def _looks_like_css(self, selector: str) -> bool:
        if "\x00" in selector or selector[-1] in {">", "+", "~", ","}:
            return False

        stack: list[str] = []
        quote: str | None = None
        escaped = False
        pairs = {"(": ")", "[": "]"}

        for char in selector:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if quote is not None:
                if char == quote:
                    quote = None
                continue
            if char in {"'", '"'}:
                quote = char
                continue
            if char in pairs:
                stack.append(pairs[char])
                continue
            if char in {")", "]"}:
                if not stack or stack.pop() != char:
                    return False

        return quote is None and not stack
