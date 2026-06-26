from __future__ import annotations

import asyncio

from noctra_browser import Cookie, launch


async def main() -> None:
    async with await launch(headless=True) as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")
        await page.set_cookies([Cookie(name="theme", value="dark", domain="example.com")])
        cookies = await page.cookies()
        print(cookies)


if __name__ == "__main__":
    asyncio.run(main())
