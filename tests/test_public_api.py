from __future__ import annotations


def test_public_imports_work() -> None:
    from noctra_browser import (
        Browser,
        BrowserConnectionError,
        BrowserLaunchError,
        CdpError,
        ElementHandle,
        NoctraError,
        Page,
        SelectorError,
        TargetClosedError,
        TimeoutError,
        connect,
        launch,
    )

    assert Browser is not None
    assert BrowserConnectionError is not None
    assert BrowserLaunchError is not None
    assert CdpError is not None
    assert ElementHandle is not None
    assert NoctraError is not None
    assert Page is not None
    assert SelectorError is not None
    assert TargetClosedError is not None
    assert TimeoutError is not None
    assert connect is not None
    assert launch is not None
