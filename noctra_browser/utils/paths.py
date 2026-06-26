from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path


def find_chrome_executable() -> str | None:
    env_path = os.environ.get("CHROME_PATH") or os.environ.get("CHROME_EXECUTABLE")
    if env_path and _is_executable(Path(env_path)):
        return env_path

    for name in _binary_names():
        resolved = shutil.which(name)
        if resolved:
            return resolved

    for candidate in _platform_candidates():
        path = Path(candidate)
        if _is_executable(path):
            return str(path)
    return None


def resolve_executable_path(executable_path: str | None) -> str | None:
    if executable_path is None:
        return find_chrome_executable()
    path = Path(executable_path).expanduser()
    if _is_executable(path):
        return str(path)
    return None


def _is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def _binary_names() -> tuple[str, ...]:
    return (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "chrome",
        "msedge",
        "brave-browser",
    )


def _platform_candidates() -> tuple[str, ...]:
    system = platform.system()
    if system == "Darwin":
        return (
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        )
    if system == "Windows":
        roots = [
            os.environ.get("PROGRAMFILES"),
            os.environ.get("PROGRAMFILES(X86)"),
            os.environ.get("LOCALAPPDATA"),
        ]
        suffixes = (
            r"Google\Chrome\Application\chrome.exe",
            r"Chromium\Application\chrome.exe",
            r"Microsoft\Edge\Application\msedge.exe",
            r"BraveSoftware\Brave-Browser\Application\brave.exe",
        )
        return tuple(str(Path(root) / suffix) for root in roots if root for suffix in suffixes)
    return (
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    )
