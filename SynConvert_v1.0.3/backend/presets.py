"""Preset definitions for SynConvert.

Each preset fully specifies the FFmpeg encoding parameters for a conversion job.
The actual encoder (GPU vs CPU) is injected at runtime by the hardware module.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Preset:
    """Immutable encoding preset."""

    name: str
    label: str
    description: str

    # Video
    width: int
    height: int

    # CPU encoder settings (libx264)
    cpu_crf: int
    cpu_preset: str

    # GPU encoder settings (NVENC / QSV)
    gpu_bitrate: str
    gpu_maxrate: str
    gpu_bufsize: str

    # Audio
    audio_codec: str
    audio_bitrate: str

    # Container
    container: str


# ---------------------------------------------------------------------------
# Preset registry
# ---------------------------------------------------------------------------

_PRESETS: dict[str, Preset] = {
    # === 1080p ===
    "1080p_high": Preset(
        name="1080p_high", label="1080p High",
        description="1920×1080 — best quality, larger files",
        width=1920, height=1080,
        cpu_crf=20, cpu_preset="fast",
        gpu_bitrate="5000k", gpu_maxrate="6000k", gpu_bufsize="10000k",
        audio_codec="aac", audio_bitrate="192k", container="mkv",
    ),
    "1080p_medium": Preset(
        name="1080p_medium", label="1080p Medium",
        description="1920×1080 — balanced quality and size",
        width=1920, height=1080,
        cpu_crf=23, cpu_preset="fast",
        gpu_bitrate="3500k", gpu_maxrate="4200k", gpu_bufsize="7000k",
        audio_codec="aac", audio_bitrate="128k", container="mkv",
    ),
    "1080p_low": Preset(
        name="1080p_low", label="1080p Low",
        description="1920×1080 — smaller files, reduced quality",
        width=1920, height=1080,
        cpu_crf=28, cpu_preset="fast",
        gpu_bitrate="2000k", gpu_maxrate="2500k", gpu_bufsize="4000k",
        audio_codec="aac", audio_bitrate="96k", container="mkv",
    ),

    # === 720p ===
    "720p_high": Preset(
        name="720p_high", label="720p High",
        description="1280×720 — sharp on tablets and phones",
        width=1280, height=720,
        cpu_crf=20, cpu_preset="fast",
        gpu_bitrate="3000k", gpu_maxrate="3600k", gpu_bufsize="6000k",
        audio_codec="aac", audio_bitrate="192k", container="mkv",
    ),
    "720p_medium": Preset(
        name="720p_medium", label="720p Medium",
        description="1280×720 — recommended for most devices",
        width=1280, height=720,
        cpu_crf=23, cpu_preset="fast",
        gpu_bitrate="2000k", gpu_maxrate="2500k", gpu_bufsize="4000k",
        audio_codec="aac", audio_bitrate="128k", container="mkv",
    ),
    "720p_low": Preset(
        name="720p_low", label="720p Low",
        description="1280×720 — maximum savings at 720p",
        width=1280, height=720,
        cpu_crf=28, cpu_preset="fast",
        gpu_bitrate="1200k", gpu_maxrate="1500k", gpu_bufsize="2500k",
        audio_codec="aac", audio_bitrate="96k", container="mkv",
    ),

    # === 480p ===
    "480p_high": Preset(
        name="480p_high", label="480p High",
        description="854×480 — best quality at low resolution",
        width=854, height=480,
        cpu_crf=20, cpu_preset="fast",
        gpu_bitrate="1500k", gpu_maxrate="1800k", gpu_bufsize="3000k",
        audio_codec="aac", audio_bitrate="128k", container="mkv",
    ),
    "480p_medium": Preset(
        name="480p_medium", label="480p Medium",
        description="854×480 — balanced for storage-limited devices",
        width=854, height=480,
        cpu_crf=23, cpu_preset="fast",
        gpu_bitrate="1000k", gpu_maxrate="1200k", gpu_bufsize="2000k",
        audio_codec="aac", audio_bitrate="96k", container="mkv",
    ),
    "480p_low": Preset(
        name="480p_low", label="480p Low",
        description="854×480 — absolute minimum size",
        width=854, height=480,
        cpu_crf=28, cpu_preset="fast",
        gpu_bitrate="600k", gpu_maxrate="750k", gpu_bufsize="1200k",
        audio_codec="aac", audio_bitrate="64k", container="mkv",
    ),
}

# Backwards-compatibility aliases for existing queue entries
_PRESETS["720p_mobile"] = _PRESETS["720p_medium"]
_PRESETS["480p_saver"] = _PRESETS["480p_low"]


def get_preset(name: str) -> Preset:
    """Return a preset by name. Raises ValueError if not found."""
    if name not in _PRESETS:
        available = ", ".join(k for k in _PRESETS if not k.endswith(("_mobile", "_saver")))
        raise ValueError(f"Unknown preset '{name}'. Available: {available}")
    return _PRESETS[name]


def list_presets() -> list[Preset]:
    """Return all available presets (excluding aliases)."""
    seen = set()
    result = []
    for p in _PRESETS.values():
        if p.name not in seen:
            seen.add(p.name)
            result.append(p)
    return result
