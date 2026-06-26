from __future__ import annotations

import pytest

from noctra_browser.utils.async_utils import wait_for_condition
from noctra_browser.utils.errors import TimeoutError


async def test_timeout_helper_raises_clear_timeout_error() -> None:
    with pytest.raises(TimeoutError, match="selector 'h1'"):
        await wait_for_condition(
            lambda: None,
            timeout=0.01,
            interval=0.001,
            timeout_message="Timed out after 0.0s while waiting for selector 'h1'",
        )
