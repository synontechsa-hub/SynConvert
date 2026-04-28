"""Hardware detection for SynConvert.

Determines the best available FFmpeg encoder at startup:
  1. NVIDIA NVENC  (h264_nvenc)
  2. Intel QuickSync (h264_qsv)
  3. CPU fallback  (libx264)

The detection probes FFmpeg directly to avoid false positives from
`nvidia-smi` existing without NVENC support in the FFmpeg build.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import Enum, auto
from functools import lru_cache

import static_ffmpeg


class EncoderBackend(Enum):
    NVENC = auto()
    QSV = auto()
    CPU = auto()


@dataclass(frozen=True)
class EncoderInfo:
    """Result of hardware detection."""

    backend: EncoderBackend
    video_encoder: str   # e.g. "h264_nvenc", "h264_qsv", "libx264"
    label: str           # Human-readable label for logging
    is_hardware: bool    # True if GPU-accelerated


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ffmpeg_bin() -> str:
    """Return the path to the static FFmpeg binary."""
    ffmpeg, _ = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
    return str(ffmpeg)


def _encoder_available(ffmpeg: str, encoder: str) -> bool:
    """Return True if FFmpeg reports the given encoder as available."""
    try:
        result = subprocess.run(
            [ffmpeg, "-encoders", "-v", "quiet"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return encoder in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _test_nvenc(ffmpeg: str) -> bool:
    """Do a real probe: try to encode 1 frame with NVENC to confirm it works."""
    try:
        result = subprocess.run(
            [
                ffmpeg,
                "-f", "lavfi",
                "-i", "color=black:s=128x128:r=1",
                "-vframes", "1",
                "-c:v", "h264_nvenc",
                "-pix_fmt", "yuv420p",
                "-f", "null",
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _test_qsv(ffmpeg: str) -> bool:
    """Do a real probe: try to encode 1 frame with QSV to confirm it works."""
    try:
        result = subprocess.run(
            [
                ffmpeg,
                "-f", "lavfi",
                "-i", "color=black:s=128x128:r=1",
                "-vframes", "1",
                "-c:v", "h264_qsv",
                "-pix_fmt", "nv12",
                "-f", "null",
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def detect_encoder(force: str | None = None) -> EncoderInfo:
    """Detect and return the best available encoder.

    Args:
        force: If provided, skip detection and use this encoder name.
               E.g. "libx264" to force CPU mode.

    Returns:
        EncoderInfo with the selected encoder details.
    """
    ffmpeg = _ffmpeg_bin()

    if force:
        # Determine backend from encoder name
        if "nvenc" in force:
            return EncoderInfo(EncoderBackend.NVENC, force, f"Forced ({force})", True)
        if "qsv" in force:
            return EncoderInfo(EncoderBackend.QSV, force, f"Forced ({force})", True)
        return EncoderInfo(EncoderBackend.CPU, force, f"Forced ({force})", False)

    # 1. Try NVIDIA NVENC
    if _encoder_available(ffmpeg, "h264_nvenc") and _test_nvenc(ffmpeg):
        return EncoderInfo(
            backend=EncoderBackend.NVENC,
            video_encoder="h264_nvenc",
            label="NVIDIA NVENC (GPU)",
            is_hardware=True,
        )

    # 2. Try Intel QuickSync
    if _encoder_available(ffmpeg, "h264_qsv") and _test_qsv(ffmpeg):
        return EncoderInfo(
            backend=EncoderBackend.QSV,
            video_encoder="h264_qsv",
            label="Intel QuickSync (GPU)",
            is_hardware=True,
        )

    # 3. CPU fallback
    return EncoderInfo(
        backend=EncoderBackend.CPU,
        video_encoder="libx264",
        label="CPU (libx264)",
        is_hardware=False,
    )


def get_available_backends() -> list[EncoderInfo]:
    """Return a list of all encoders that successfully passed detection."""
    ffmpeg = _ffmpeg_bin()
    backends = []

    # Check NVENC
    if _encoder_available(ffmpeg, "h264_nvenc") and _test_nvenc(ffmpeg):
        backends.append(EncoderInfo(
            backend=EncoderBackend.NVENC,
            video_encoder="h264_nvenc",
            label="NVIDIA NVENC (GPU)",
            is_hardware=True,
        ))

    # Check QSV
    if _encoder_available(ffmpeg, "h264_qsv") and _test_qsv(ffmpeg):
        backends.append(EncoderInfo(
            backend=EncoderBackend.QSV,
            video_encoder="h264_qsv",
            label="Intel QuickSync (GPU)",
            is_hardware=True,
        ))

    # CPU is always available
    backends.append(EncoderInfo(
        backend=EncoderBackend.CPU,
        video_encoder="libx264",
        label="CPU (libx264)",
        is_hardware=False,
    ))

    return backends
