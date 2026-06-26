from __future__ import annotations

import asyncio

from noctra_browser import ConsoleMessage, launch


async def main() -> None:
    async with await launch(headless=True) as browser:
        page = await browser.new_page()

        def on_console(message: object) -> None:
            if isinstance(message, ConsoleMessage):
                print(message.type, message.text)

        page.on("console", on_console)
        await page.goto("https://example.com")
        await page.evaluate("console.log('hello from page')")


if __name__ == "__main__":
    asyncio.run(main())
