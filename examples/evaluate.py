from __future__ import annotations

import asyncio

from noctra_browser import launch


async def main() -> None:
    async with await launch(headless=True) as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")
        value = await page.evaluate("(a, b) => a + b", 20, 22)
        print(value)


if __name__ == "__main__":
    asyncio.run(main())
