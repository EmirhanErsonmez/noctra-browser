from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from noctra_browser.cdp.client import CdpClient
from noctra_browser.utils.errors import BrowserConnectionError, CdpError, TargetClosedError


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.closed = False

    async def send(self, message: str) -> None:
        self.sent.append(json.loads(message))

    async def close(self) -> None:
        self.closed = True


class ClosingWebSocket(FakeWebSocket):
    def __init__(self) -> None:
        super().__init__()
        self.message_sent = asyncio.Event()

    async def send(self, message: str) -> None:
        await super().send(message)
        self.message_sent.set()

    def __aiter__(self) -> ClosingWebSocket:
        return self

    async def __anext__(self) -> str:
        await self.message_sent.wait()
        raise StopAsyncIteration


def connected_client() -> tuple[CdpClient, FakeWebSocket]:
    websocket = FakeWebSocket()
    client = CdpClient("ws://example.test/devtools/browser")
    client._websocket = websocket
    client._connected = True
    return client, websocket


async def test_cdp_command_id_increments() -> None:
    client, websocket = connected_client()

    first = asyncio.create_task(client.send("Runtime.evaluate", timeout=1))
    await asyncio.sleep(0)
    second = asyncio.create_task(client.send("Browser.getVersion", timeout=1))
    await asyncio.sleep(0)

    assert websocket.sent[0]["id"] == 1
    assert websocket.sent[1]["id"] == 2

    await client._handle_message({"id": 1, "result": {"value": "ok"}})
    await client._handle_message({"id": 2, "result": {"product": "Chrome"}})

    assert await first == {"value": "ok"}
    assert await second == {"product": "Chrome"}


async def test_cdp_response_matches_correct_pending_future() -> None:
    client, _websocket = connected_client()

    first = asyncio.create_task(client.send("First.command", timeout=1))
    second = asyncio.create_task(client.send("Second.command", timeout=1))
    await asyncio.sleep(0)

    await client._handle_message({"id": 2, "result": {"name": "second"}})
    await client._handle_message({"id": 1, "result": {"name": "first"}})

    assert await first == {"name": "first"}
    assert await second == {"name": "second"}


async def test_cdp_error_response_raises_cdp_error() -> None:
    client, _websocket = connected_client()

    command = asyncio.create_task(client.send("Runtime.evaluate", timeout=1))
    await asyncio.sleep(0)
    await client._handle_message(
        {
            "id": 1,
            "error": {
                "code": -32000,
                "message": "Evaluation failed",
                "data": {"line": 1},
            },
        }
    )

    with pytest.raises(CdpError) as exc_info:
        await command

    assert exc_info.value.method == "Runtime.evaluate"
    assert exc_info.value.code == -32000
    assert exc_info.value.data == {"line": 1}


async def test_clean_websocket_close_rejects_pending_commands_immediately() -> None:
    websocket = ClosingWebSocket()
    client = CdpClient("ws://example.test/devtools/browser")
    client._websocket = websocket
    client._connected = True
    client._reader_task = asyncio.create_task(client._reader_loop())

    command = asyncio.create_task(client.send("Runtime.evaluate", timeout=5))
    await websocket.message_sent.wait()

    with pytest.raises(BrowserConnectionError, match="CDP connection closed"):
        await asyncio.wait_for(command, timeout=0.5)


async def test_session_detach_rejects_matching_pending_commands() -> None:
    client, _websocket = connected_client()

    command = asyncio.create_task(
        client.send("Runtime.evaluate", session_id="session-1", timeout=5)
    )
    await asyncio.sleep(0)

    await client._handle_message(
        {
            "method": "Target.detachedFromTarget",
            "params": {"sessionId": "session-1", "targetId": "target-1"},
        }
    )

    with pytest.raises(TargetClosedError, match="CDP session 'session-1' closed"):
        await asyncio.wait_for(command, timeout=0.5)
