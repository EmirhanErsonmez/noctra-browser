from __future__ import annotations

from typing import cast

from noctra_browser.types.public import LoadState, SelectorState
from noctra_browser.utils.errors import NoctraError

LOAD_STATES: set[str] = {"load", "domcontentloaded", "networkidle"}
SELECTOR_STATES: set[str] = {"attached", "detached", "visible", "hidden"}


def normalize_load_state(state: str) -> LoadState:
    if state not in LOAD_STATES:
        raise NoctraError(f"Unsupported load state {state!r}")
    return cast(LoadState, state)


def normalize_selector_state(state: str) -> SelectorState:
    if state not in SELECTOR_STATES:
        raise NoctraError(f"Unsupported selector state {state!r}")
    return cast(SelectorState, state)
