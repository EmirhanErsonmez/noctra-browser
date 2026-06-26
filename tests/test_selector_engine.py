from __future__ import annotations

import pytest

from noctra_browser.selectors.engine import SelectorEngine
from noctra_browser.utils.errors import SelectorError


def test_selector_engine_accepts_valid_css_selector() -> None:
    parsed = SelectorEngine().parse("css=main article.card[data-kind='primary'] > h1")

    assert parsed.kind == "css"
    assert parsed.value == "main article.card[data-kind='primary'] > h1"


@pytest.mark.parametrize("selector", ["", "   ", "[broken", "text=Submit"])
def test_selector_engine_rejects_empty_or_invalid_selector(selector: str) -> None:
    with pytest.raises(SelectorError):
        SelectorEngine().parse(selector)
