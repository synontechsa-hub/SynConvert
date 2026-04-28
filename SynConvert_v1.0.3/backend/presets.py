"""Preset definitions for SynConvert.

Each preset fully specifies the FFmpeg encoding parameters for a conversion job.
The actual encoder (GPU vs CPU) is injected at runtime by the hardware module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PresetName = Literal["720p_mobile", "480p_saver"]


@dataclass(frozen=True)
class Preset:
    """Immutable encoding preset."""

    name: PresetName
    label: str
    description: str

    # Video
    width: int
    height: int
    """Target resolution. Aspect ratio is always preserved (scale filter)."""

    # CPU encoder settings (libx264)
    cpu_crf: int
    cpu_preset: str  # FFmpeg preset speed/quality trade-off

    # GPU encoder settings (NVENC / QSV)
    gpu_bitrate: str   # e.g. "2500k"
    gpu_maxrate: str   # e.g. "3000k"
    gpu_bufsize: str   # e.g. "5000k"

    # Audio
    audio_codec: str   # e.g. "aac"
    audio_bitrate: str  # per-track bitrate, e.g. "128k"

    # Container
    container: str     # output file extension without dot, e.g. "mkv"


# ---------------------------------------------------------------------------
# Preset registry
# ---------------------------------------------------------------------------

_PRESETS: dict[PresetName, Preset] = {
    "720p_mobile": Preset(
        name="720p_mobile",
        label="720p Mobile",
        description="1280×720 H.264 — recommended for most devices",
        width=1280,
        height=720,
        cpu_crf=23,
        cpu_preset="fast",
        gpu_bitrate="2500k",
        gpu_maxrate="3000k",
        gpu_bufsize="5000k",
        audio_codec="aac",
        audio_bitrate="128k",
        container="mkv",
    ),
    "480p_saver": Preset(
        name="480p_saver",
        label="480p Storage Saver",
        description="854×480 H.264 — maximum storage savings, lower quality",
        width=854,
        height=480,
        cpu_crf=26,
        cpu_preset="fast",
        gpu_bitrate="1200k",
        gpu_maxrate="1500k",
        gpu_bufsize="2500k",
        audio_codec="aac",
        audio_bitrate="96k",
        container="mkv",
    ),
}


def get_preset(name: PresetName) -> Preset:
    """Return a preset by name. Raises ValueError if not found."""
    if name not in _PRESETS:
        available = ", ".join(_PRESETS.keys())
        raise ValueError(f"Unknown preset '{name}'. Available: {available}")
    return _PRESETS[name]


def list_presets() -> list[Preset]:
    """Return all available presets."""
    return list(_PRESETS.values())
