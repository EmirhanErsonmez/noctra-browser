from __future__ import annotations

import asyncio
import os
import tempfile
from dataclasses import dataclass

import httpx

from noctra_browser.types.public import Viewport
from noctra_browser.utils.errors import BrowserLaunchError
from noctra_browser.utils.paths import find_chrome_executable, resolve_executable_path
from noctra_browser.utils.ports import find_free_port
from noctra_browser.utils.process import remove_directory, terminate_process


@dataclass(slots=True)
class LaunchOptions:
    headless: bool = True
    executable_path: str | None = None
    user_data_dir: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    timeout: float = 30.0
    viewport: Viewport | None = None
    stealth: bool = True


_STEALTH_ARGS = (
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process,Translate",
    "--disable-infobars",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
)


@dataclass(slots=True)
class BrowserProcess:
    process: asyncio.subprocess.Process
    user_data_dir: str
    owns_user_data_dir: bool

    async def close(self) -> None:
        await terminate_process(self.process)
        if self.owns_user_data_dir:
            remove_directory(self.user_data_dir)


@dataclass(slots=True)
class LaunchResult:
    websocket_url: str
    debugging_port: int
    process: BrowserProcess


class BrowserLauncher:
    def find_executable(self, executable_path: str | None = None) -> str | None:
        return resolve_executable_path(executable_path)

    async def launch(self, options: LaunchOptions) -> LaunchResult:
        executable = self.find_executable(options.executable_path)
        if executable is None:
            raise BrowserLaunchError(
                "Could not find Chrome or Chromium executable. Pass executable_path explicitly."
            )

        port = find_free_port()
        user_data_dir = options.user_data_dir or tempfile.mkdtemp(prefix="noctra-browser-")
        owns_user_data_dir = options.user_data_dir is None

        command = self._build_command(executable, port, user_data_dir, options)
        environment = os.environ.copy()
        if options.env:
            environment.update(options.env)

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                env=environment,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except Exception as exc:
            if owns_user_data_dir:
                remove_directory(user_data_dir)
            raise BrowserLaunchError(f"Failed to launch browser executable {executable!r}") from exc

        process_handle = BrowserProcess(
            process=process,
            user_data_dir=user_data_dir,
            owns_user_data_dir=owns_user_data_dir,
        )

        try:
            websocket_url = await self._wait_for_websocket_url(
                port,
                process,
                timeout=options.timeout,
            )
        except Exception:
            await process_handle.close()
            raise

        return LaunchResult(
            websocket_url=websocket_url,
            debugging_port=port,
            process=process_handle,
        )

    def _build_command(
        self,
        executable: str,
        port: int,
        user_data_dir: str,
        options: LaunchOptions,
    ) -> list[str]:
        command = [
            executable,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        if options.stealth:
            command.append("--exclude-switches=enable-automation")
            command.extend(_STEALTH_ARGS)
        if options.headless:
            command.append("--headless=new")
        if options.viewport is not None:
            command.append(f"--window-size={options.viewport.width},{options.viewport.height}")
        if options.args:
            command.extend(options.args)
        command.append("about:blank")
        return command

    async def _wait_for_websocket_url(
        self,
        port: int,
        process: asyncio.subprocess.Process,
        *,
        timeout: float,
    ) -> str:
        endpoint = f"http://127.0.0.1:{port}/json/version"
        deadline = asyncio.get_running_loop().time() + timeout
        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=1.0) as client:
            while True:
                if process.returncode is not None:
                    raise BrowserLaunchError(
                        "Browser process exited before CDP was ready "
                        f"with code {process.returncode}"
                    )
                try:
                    response = await client.get(endpoint)
                    response.raise_for_status()
                    payload = response.json()
                    websocket_url = payload.get("webSocketDebuggerUrl")
                    if isinstance(websocket_url, str) and websocket_url:
                        return websocket_url
                except Exception as exc:
                    last_error = exc

                if asyncio.get_running_loop().time() >= deadline:
                    raise BrowserLaunchError(
                        f"Timed out after {timeout:.1f}s while waiting for CDP endpoint"
                    ) from last_error
                await asyncio.sleep(0.1)


__all__ = [
    "BrowserLauncher",
    "BrowserProcess",
    "LaunchOptions",
    "LaunchResult",
    "find_chrome_executable",
]
