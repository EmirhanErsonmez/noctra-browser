from __future__ import annotations

import asyncio
import random

from noctra_browser.cdp.domains import InputDomain
from noctra_browser.cdp.session import CdpSession

KEY_CODES: dict[str, tuple[str, int]] = {
    # Navigation
    "Enter": ("Enter", 13),
    "Escape": ("Escape", 27),
    "Tab": ("Tab", 9),
    "Backspace": ("Backspace", 8),
    "Delete": ("Delete", 46),
    "Insert": ("Insert", 45),
    "Home": ("Home", 36),
    "End": ("End", 35),
    "PageUp": ("PageUp", 33),
    "PageDown": ("PageDown", 34),
    # Arrow keys
    "ArrowLeft": ("ArrowLeft", 37),
    "ArrowUp": ("ArrowUp", 38),
    "ArrowRight": ("ArrowRight", 39),
    "ArrowDown": ("ArrowDown", 40),
    # Modifier keys
    "Shift": ("ShiftLeft", 16),
    "Control": ("ControlLeft", 17),
    "Alt": ("AltLeft", 18),
    "Meta": ("MetaLeft", 91),
    "ShiftLeft": ("ShiftLeft", 16),
    "ShiftRight": ("ShiftRight", 16),
    "ControlLeft": ("ControlLeft", 17),
    "ControlRight": ("ControlRight", 17),
    "AltLeft": ("AltLeft", 18),
    "AltRight": ("AltRight", 18),
    # Function keys
    "F1": ("F1", 112),
    "F2": ("F2", 113),
    "F3": ("F3", 114),
    "F4": ("F4", 115),
    "F5": ("F5", 116),
    "F6": ("F6", 117),
    "F7": ("F7", 118),
    "F8": ("F8", 119),
    "F9": ("F9", 120),
    "F10": ("F10", 121),
    "F11": ("F11", 122),
    "F12": ("F12", 123),
    # Misc
    "Space": ("Space", 32),
    "CapsLock": ("CapsLock", 20),
    "PrintScreen": ("PrintScreen", 44),
    "ScrollLock": ("ScrollLock", 145),
    "Pause": ("Pause", 19),
}


class Keyboard:
    def __init__(self, session: CdpSession) -> None:
        self._session = session

    async def type_text(self, text: str, *, delay: float = 0, human: bool = False) -> None:
        for character in text:
            await self._session.send(
                InputDomain.DISPATCH_KEY_EVENT,
                {
                    "type": "char",
                    "text": character,
                    "unmodifiedText": character,
                },
            )
            if human:
                await asyncio.sleep(random.uniform(0.04, 0.18))
            elif delay > 0:
                await asyncio.sleep(delay)

    async def insert_text(self, text: str) -> None:
        await self._session.send(InputDomain.INSERT_TEXT, {"text": text})

    async def press(self, key: str) -> None:
        if key in KEY_CODES:
            code, windows_code = KEY_CODES[key]
        elif len(key) == 1:
            code = key
            windows_code = ord(key.upper()) if key.isalpha() else ord(key)
        else:
            raise ValueError(f"Unknown key {key!r}. Use a single character or a named key.")
        params: dict[str, object] = {
            "key": key,
            "code": code,
            "windowsVirtualKeyCode": windows_code,
            "nativeVirtualKeyCode": windows_code,
        }
        if len(key) == 1:
            params["text"] = key
            params["unmodifiedText"] = key
        await self._session.send(InputDomain.DISPATCH_KEY_EVENT, {"type": "keyDown", **params})
        await self._session.send(InputDomain.DISPATCH_KEY_EVENT, {"type": "keyUp", **params})
