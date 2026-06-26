# Noctra Browser

Async Python browser automation framework powered by Chrome DevTools Protocol.

## Project Status

Noctra Browser is an async-first framework for launching Chrome or Chromium, connecting over CDP, controlling pages, evaluating JavaScript, using CSS selectors, handling events, taking screenshots, managing cookies, and driving human-like input.

It ships with a built-in stealth layer engineered to defeat detection that also catches the evasions themselves:

- **No `Runtime.enable`.** JavaScript is evaluated inside an isolated world, so the single most reliable CDP automation signal never fires.
- **No `Proxy`-based hooks.** Property spoofs are installed with native-looking getters, defeating the prototype-chain `ownKeys` inspector leak and the `Error.stack` getter trap that expose naive stealth tooling.
- **`toString` and descriptor integrity.** Every patched function reports `[native code]`, and `Object.getOwnPropertyDescriptor` stays faithful (e.g. `navigator.webdriver` remains a native getter on `Navigator.prototype`).
- **Worker consistency.** Evasions are re-applied inside web/shared/service workers via `Target.setAutoAttach`, so `navigator.platform`/`hardwareConcurrency`/user-agent match the main thread — a gap nodriver leaves open.
- **Fingerprint surface.** Spoofs `navigator.webdriver/plugins/mimeTypes/languages/vendor/platform/hardwareConcurrency/deviceMemory`, builds a realistic `window.chrome`, fixes the permissions API, spoofs the WebGL vendor/renderer, adds deterministic (stable) canvas/audio noise, and strips the `HeadlessChrome` user-agent marker.

## Installation

```bash
pip install -e ".[dev]"
```

Noctra Browser requires Python 3.11+ and a local Chrome or Chromium-compatible browser.

## Basic Usage

```python
import asyncio
from noctra_browser import launch


async def main() -> None:
    async with await launch(headless=False) as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")
        await page.wait_for_load_state("domcontentloaded")

        title = await page.title()
        heading = await page.locator("h1").text()

        await page.screenshot(path="example.png")

        print(title, heading)


asyncio.run(main())
```

## Launch Options

```python
from noctra_browser import Viewport, launch

browser = await launch(
    headless=True,
    executable_path=None,
    user_data_dir=None,
    args=["--lang=en-US"],
    env=None,
    timeout=30.0,
    viewport=Viewport(width=1280, height=720),
)
```

If `executable_path` is not supplied, Noctra Browser searches common Chrome and Chromium locations on macOS, Windows, and Linux. If `user_data_dir` is omitted, a temporary profile directory is created and cleaned up when the browser closes.

## Stealth

Stealth is enabled by default. To configure or disable it, pass the `stealth` argument:

```python
from noctra_browser import StealthConfig, launch

# Disable entirely (uses Runtime.enable, faster, detectable)
browser = await launch(stealth=False)

# Fine-tune the spoofed fingerprint
browser = await launch(
    stealth=StealthConfig(
        languages=("en-US", "en"),
        platform="Win32",
        vendor="Google Inc.",
        hardware_concurrency=8,
        device_memory=8,
        webgl_vendor_string="Intel Inc.",
        webgl_renderer_string="Intel Iris OpenGL Engine",
        canvas_noise=True,
        audio_noise=True,
        spoof_workers=True,
    ),
)
```

When stealth is active, `page.evaluate()` runs in an isolated world, so page scripts cannot observe the evaluation context. Custom evasions can be injected via `StealthConfig(extra_evasions=(...,))`; they run in both the main world and workers.

## Human-like Input

```python
element = await page.query("#search")
await element.type("query", human=True)   # variable per-key delay
await element.fill("fast value")          # Input.insertText, no per-key events

await page.locator("#submit").click()     # stepped mouse movement + press/release
```

## Async Context Manager

```python
async with await launch(headless=True) as browser:
    page = await browser.new_page()
    await page.goto("https://example.com")
```

You can also manage cleanup manually:

```python
browser = await launch(headless=True)
page = await browser.new_page()
await page.goto("https://example.com")
await browser.close()
```

## Page Navigation

```python
page = await browser.new_page()
await page.goto("https://example.com", wait_until="load")
await page.reload(wait_until="domcontentloaded")
print(await page.url())
print(await page.title())
```

## Locators

```python
heading = page.locator("h1")
print(await heading.text())

button = page.locator("button[type='submit']")
await button.click()
```

Locators are lazy. The selector is resolved when an action or read method runs.

## Screenshots

```python
await page.goto("https://example.com")
await page.screenshot(path="example.png", full_page=True)

image_bytes = await page.screenshot()
```

## Cookies

```python
from noctra_browser import Cookie

await page.set_cookies([
    Cookie(name="theme", value="dark", domain="example.com"),
])

cookies = await page.cookies()
```

## Network Events

```python
from noctra_browser import Request, Response


def on_request(payload: object) -> None:
    if isinstance(payload, Request):
        print(payload.method, payload.url)


def on_response(payload: object) -> None:
    if isinstance(payload, Response):
        print(payload.status, payload.url)


page.on("request", on_request)
page.on("response", on_response)
await page.goto("https://example.com")
```

## Console Events

```python
from noctra_browser import ConsoleMessage


def on_console(payload: object) -> None:
    if isinstance(payload, ConsoleMessage):
        print(payload.type, payload.text)


page.on("console", on_console)
await page.evaluate("console.log('hello')")
```

## JavaScript Evaluation

```python
title = await page.evaluate("document.title")
answer = await page.evaluate("(a, b) => a + b", 20, 22)
```

## Error Handling

```python
from noctra_browser import NoctraError, TimeoutError

try:
    await page.wait_for_selector("main h1", timeout=2.0)
except TimeoutError as exc:
    print(exc)
except NoctraError as exc:
    print(f"Browser automation failed: {exc}")
```

All framework-specific exceptions inherit from `NoctraError`.

## Development Setup

```bash
pip install -e ".[dev]"
python -m pytest
python -m mypy noctra_browser
python -m ruff check noctra_browser tests examples
python -m ruff format noctra_browser tests examples
```

## Testing

The unit tests cover CDP command id generation, response matching, CDP error conversion, async-aware events, selector validation, timeout behavior, public imports, and a Chrome launch smoke test. The smoke test skips automatically when the environment does not have a usable Chrome or Chromium executable.

## Ethical Usage

Noctra Browser is designed for authorized automation, QA, testing, research, and internal tooling. Do not use it for abuse, spam, credential attacks, unauthorized scraping, or bypassing platform protections.
