from __future__ import annotations

import asyncio
import contextlib
import shutil
from pathlib import Path


async def terminate_process(process: asyncio.subprocess.Process, *, timeout: float = 5.0) -> None:
    if process.returncode is not None:
        return
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=timeout)
    except TimeoutError:
        process.kill()
        await process.wait()


def remove_directory(path: str) -> None:
    with contextlib.suppress(FileNotFoundError):
        shutil.rmtree(Path(path), ignore_errors=True)
