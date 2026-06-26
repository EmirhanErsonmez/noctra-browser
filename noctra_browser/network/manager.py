from __future__ import annotations

from typing import Any

from noctra_browser.cdp.domains import NetworkDomain
from noctra_browser.cdp.session import CdpSession
from noctra_browser.types.public import Request, Response


class NetworkManager:
    def __init__(self, session: CdpSession) -> None:
        self._session = session

    async def enable(self) -> None:
        await self._session.send(NetworkDomain.ENABLE)

    def request_from_event(self, params: dict[str, Any]) -> Request:
        request = params.get("request", {})
        request_data = request if isinstance(request, dict) else {}
        return Request(
            url=str(request_data.get("url", "")),
            method=str(request_data.get("method", "GET")),
            headers=self._headers(request_data.get("headers")),
            resource_type=str(params.get("type")) if params.get("type") is not None else None,
        )

    def response_from_event(self, params: dict[str, Any]) -> Response:
        response = params.get("response", {})
        response_data = response if isinstance(response, dict) else {}
        status = response_data.get("status", 0)
        return Response(
            url=str(response_data.get("url", "")),
            status=int(status) if isinstance(status, int | float) else 0,
            status_text=str(response_data.get("statusText", "")),
            headers=self._headers(response_data.get("headers")),
            mime_type=str(response_data.get("mimeType"))
            if response_data.get("mimeType") is not None
            else None,
        )

    def _headers(self, raw_headers: object) -> dict[str, str]:
        if not isinstance(raw_headers, dict):
            return {}
        headers: dict[str, str] = {}
        for key, value in raw_headers.items():
            if isinstance(value, list):
                headers[str(key)] = ", ".join(str(item) for item in value)
            else:
                headers[str(key)] = str(value)
        return headers
