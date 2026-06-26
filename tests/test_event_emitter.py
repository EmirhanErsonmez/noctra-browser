from __future__ import annotations

from noctra_browser.utils.events import EventEmitter


async def test_event_emitter_runs_sync_handler() -> None:
    emitter = EventEmitter()
    received: list[str] = []

    def handler(payload: object) -> None:
        received.append(str(payload))

    emitter.on("ready", handler)
    await emitter.emit("ready", "ok")

    assert received == ["ok"]


async def test_event_emitter_runs_async_handler() -> None:
    emitter = EventEmitter()
    received: list[str] = []

    async def handler(payload: object) -> None:
        received.append(str(payload))

    emitter.on("ready", handler)
    await emitter.emit("ready", "ok")

    assert received == ["ok"]
