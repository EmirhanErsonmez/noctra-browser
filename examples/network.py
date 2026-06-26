from __future__ import annotations

import asyncio

from noctra_browser import Request, Response, launch


async def main() -> None:
    async with await launch(headless=True) as browser:
        page = await browser.new_page()

        def on_request(request: object) -> None:
            if isinstance(request, Request):
                print("request", request.method, request.url)

        def on_response(response: object) -> None:
            if isinstance(response, Response):
                print("response", response.status, response.url)

        page.on("request", on_request)
        page.on("response", on_response)
        await page.goto("https://example.com")


if __name__ == "__main__":
    asyncio.run(main())
