from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class StealthConfig:
    enabled: bool = True
    webdriver: bool = True
    navigator_plugins: bool = True
    navigator_languages: bool = True
    navigator_vendor: bool = True
    navigator_hardware: bool = True
    window_chrome: bool = True
    permissions: bool = True
    webgl_vendor: bool = True
    canvas_noise: bool = True
    audio_noise: bool = True
    spoof_workers: bool = True
    user_agent_override: bool = True
    media_codecs: bool = True
    languages: tuple[str, ...] = ("en-US", "en")
    vendor: str = "Google Inc."
    platform: str = "Win32"
    hardware_concurrency: int = 8
    device_memory: int = 8
    webgl_vendor_string: str = "Intel Inc."
    webgl_renderer_string: str = "Intel Iris OpenGL Engine"
    extra_evasions: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def disabled(cls) -> StealthConfig:
        return cls(
            enabled=False,
            webdriver=False,
            navigator_plugins=False,
            navigator_languages=False,
            navigator_vendor=False,
            navigator_hardware=False,
            window_chrome=False,
            permissions=False,
            webgl_vendor=False,
            canvas_noise=False,
            audio_noise=False,
            spoof_workers=False,
            user_agent_override=False,
            media_codecs=False,
        )
