from __future__ import annotations

import asyncio
import base64
from pathlib import Path

from noctra_browser.cdp.domains import PageDomain
from noctra_browser.cdp.session import CdpSession
from noctra_browser.types.public import ScreenshotType


class ScreenshotService:
    def __init__(self, session: CdpSession) -> None:
        self._session = session

    async def capture(
        self,
        *,
        path: str | None = None,
        full_page: bool = False,
        type: ScreenshotType = "png",
    ) -> bytes:
        params: dict[str, object] = {"format": type}
        if full_page:
            metrics = await self._session.send(PageDomain.GET_LAYOUT_METRICS)
            content_size = metrics.get("contentSize", {})
            if isinstance(content_size, dict):
                width = float(content_size.get("width", 0))
                height = float(content_size.get("height", 0))
                if width > 0 and height > 0:
                    params["captureBeyondViewport"] = True
                    params["clip"] = {
                        "x": 0,
                        "y": 0,
                        "width": width,
                        "height": height,
                        "scale": 1,
                    }
        result = await self._session.send(PageDomain.CAPTURE_SCREENSHOT, params)
        data = result.get("data", "")
        image = base64.b64decode(str(data))
        if path is not None:
            await asyncio.to_thread(Path(path).write_bytes, image)
        return image
