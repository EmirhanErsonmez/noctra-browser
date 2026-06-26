from __future__ import annotations

from noctra_browser.cdp.domains import EmulationDomain, PageDomain
from noctra_browser.cdp.session import CdpSession
from noctra_browser.page.page import Page
from noctra_browser.types.public import Viewport
from noctra_browser.utils.errors import CdpError


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object] | None]] = []

    def on(self, event: str, handler: object) -> None:
        return None

    def off(self, event: str, handler: object) -> None:
        return None

    async def send(
        self,
        method: str,
        params: dict[str, object] | None = None,
        *,
        session_id: str | None = None,
        timeout: float = 30.0,
    ) -> dict[str, object]:
        self.calls.append((method, params))
        return {}


class ClosingClient(FakeClient):
    async def send(
        self,
        method: str,
        params: dict[str, object] | None = None,
        *,
        session_id: str | None = None,
        timeout: float = 30.0,
    ) -> dict[str, object]:
        self.calls.append((method, params))
        raise CdpError(method, -32000, "No target with given id found")


class FakeBrowser:
    def __init__(self, client: FakeClient) -> None:
        self.client = client
        self.forgotten: list[str] = []

    def _forget_page(self, target_id: str) -> None:
        self.forgotten.append(target_id)


class RecordingSession(CdpSession):
    def __init__(self) -> None:
        self.session_id = "session-1"
        self.calls: list[tuple[str, dict[str, object] | None]] = []
        self.closed = False

    async def send(
        self,
        method: str,
        params: dict[str, object] | None = None,
        *,
        timeout: float = 30.0,
    ) -> dict[str, object]:
        self.calls.append((method, params))
        return {}

    def mark_closed(self) -> None:
        self.closed = True


async def test_page_initialize_applies_viewport_with_emulation() -> None:
    session = RecordingSession()
    page = Page(
        FakeBrowser(FakeClient()),
        target_id="target-1",
        session=session,
        viewport=Viewport(width=390, height=844, device_scale_factor=2.0, is_mobile=True),
    )

    await page.initialize()

    assert (
        EmulationDomain.SET_DEVICE_METRICS_OVERRIDE,
        {
            "width": 390,
            "height": 844,
            "deviceScaleFactor": 2.0,
            "mobile": True,
        },
    ) in session.calls
    assert session.calls[0][0] == PageDomain.ENABLE


async def test_page_close_is_idempotent_when_target_is_already_gone() -> None:
    client = ClosingClient()
    browser = FakeBrowser(client)
    session = RecordingSession()
    page = Page(browser, target_id="target-1", session=session)

    await page.close()

    assert page.is_closed()
    assert session.closed
    assert browser.forgotten == ["target-1"]
    assert client.calls[0][0] == "Target.closeTarget"
