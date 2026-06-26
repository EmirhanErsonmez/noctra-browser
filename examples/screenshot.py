from __future__ import annotations

import asyncio

from noctra_browser import launch


async def main() -> None:
    async with await launch(headless=True) as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")
        await page.screenshot(path="example.png", full_page=True)


if __name__ == "__main__":
    asyncio.run(main())
