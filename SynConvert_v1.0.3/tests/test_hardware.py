"""Tests for backend.hardware

Since real GPU hardware is not available in CI, all encoder detection tests
mock the subprocess calls rather than executing real FFmpeg probes.
"""

from __future__ import annotations

import sys
from unittest.mock import patch, MagicMock


def _reset_cache() -> None:
    """Clear the lru_cache on detect_encoder between tests."""
    from backend import hardware
    hardware.detect_encoder.cache_clear()


def test_detect_encoder_cpu_fallback() -> None:
    """When no GPU encoders are available, should fall back to libx264."""
    _reset_cache()

    with (
        patch("backend.hardware._ffmpeg_bin", return_value="/fake/ffmpeg"),
        patch("backend.hardware._encoder_available", return_value=False),
    ):
        from backend.hardware import detect_encoder, EncoderBackend
        result = detect_encoder()
        assert result.backend == EncoderBackend.CPU
        assert result.video_encoder == "libx264"
        assert not result.is_hardware

    _reset_cache()


def test_detect_encoder_nvenc_when_available() -> None:
    """When NVENC is available and probe succeeds, should select NVENC."""
    _reset_cache()

    def encoder_available(_ffmpeg: str, encoder: str) -> bool:
        return encoder == "h264_nvenc"

    with (
        patch("backend.hardware._ffmpeg_bin", return_value="/fake/ffmpeg"),
        patch("backend.hardware._encoder_available", side_effect=encoder_available),
        patch("backend.hardware._test_nvenc", return_value=True),
    ):
        from backend.hardware import detect_encoder, EncoderBackend
        result = detect_encoder()
        assert result.backend == EncoderBackend.NVENC
        assert result.video_encoder == "h264_nvenc"
        assert result.is_hardware

    _reset_cache()


def test_detect_encoder_nvenc_probe_fails_falls_back_to_qsv() -> None:
    """NVENC reported available but probe fails → try QSV."""
    _reset_cache()

    def encoder_available(_ffmpeg: str, encoder: str) -> bool:
        return encoder in ("h264_nvenc", "h264_qsv")

    with (
        patch("backend.hardware._ffmpeg_bin", return_value="/fake/ffmpeg"),
        patch("backend.hardware._encoder_available", side_effect=encoder_available),
        patch("backend.hardware._test_nvenc", return_value=False),
        patch("backend.hardware._test_qsv", return_value=True),
    ):
        from backend.hardware import detect_encoder, EncoderBackend
        result = detect_encoder()
        assert result.backend == EncoderBackend.QSV

    _reset_cache()


def test_detect_encoder_force_override() -> None:
    """force= parameter should bypass all detection."""
    _reset_cache()

    with patch("backend.hardware._ffmpeg_bin", return_value="/fake/ffmpeg"):
        from backend.hardware import detect_encoder, EncoderBackend
        result = detect_encoder(force="libx264")
        assert result.video_encoder == "libx264"
        assert result.backend == EncoderBackend.CPU

    _reset_cache()


def test_detect_encoder_force_nvenc() -> None:
    _reset_cache()

    with patch("backend.hardware._ffmpeg_bin", return_value="/fake/ffmpeg"):
        from backend.hardware import detect_encoder, EncoderBackend
        result = detect_encoder(force="h264_nvenc")
        assert result.backend == EncoderBackend.NVENC
        assert result.is_hardware

    _reset_cache()
