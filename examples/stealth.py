from __future__ import annotations

import asyncio

from noctra_browser import StealthConfig, launch


async def main() -> None:
    config = StealthConfig(
        languages=("en-US", "en"),
        platform="Win32",
        vendor="Google Inc.",
        hardware_concurrency=8,
        device_memory=8,
        webgl_vendor_string="Intel Inc.",
        webgl_renderer_string="Intel Iris OpenGL Engine",
    )

    async with await launch(headless=True, stealth=config) as browser:
        page = await browser.new_page()
        await page.goto("https://example.com", wait_until="domcontentloaded")

        report = await page.evaluate(
            """
            () => ({
                webdriver: navigator.webdriver,
                plugins: navigator.plugins.length,
                vendor: navigator.vendor,
                platform: navigator.platform,
                hasChrome: typeof window.chrome,
                headlessInUserAgent: navigator.userAgent.includes('Headless'),
            })
            """
        )
        for key, value in report.items():
            print(f"{key:24} = {value}")


if __name__ == "__main__":
    asyncio.run(main())
