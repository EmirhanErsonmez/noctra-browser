from __future__ import annotations

import asyncio

from noctra_browser import launch


async def main() -> None:
    async with await launch(headless=False) as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")
        await page.wait_for_load_state("domcontentloaded")

        title = await page.title()
        heading = await page.locator("h1").text()

        print(title, heading)


if __name__ == "__main__":
    asyncio.run(main())
