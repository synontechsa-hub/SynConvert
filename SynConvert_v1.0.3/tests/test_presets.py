"""Tests for backend.presets"""

from __future__ import annotations

import pytest


def test_get_preset_720p() -> None:
    from backend.presets import get_preset

    p = get_preset("720p_mobile")
    assert p.name == "720p_mobile"
    assert p.width == 1280
    assert p.height == 720
    assert p.audio_codec == "aac"
    assert p.container == "mkv"


def test_get_preset_480p() -> None:
    from backend.presets import get_preset

    p = get_preset("480p_saver")
    assert p.name == "480p_saver"
    assert p.width == 854
    assert p.height == 480
    assert p.cpu_crf == 26


def test_get_preset_invalid_raises() -> None:
    from backend.presets import get_preset

    with pytest.raises(ValueError, match="Unknown preset"):
        get_preset("nonexistent_preset")  # type: ignore[arg-type]


def test_list_presets_returns_all() -> None:
    from backend.presets import list_presets

    presets = list_presets()
    names = {p.name for p in presets}
    assert "720p_mobile" in names
    assert "480p_saver" in names


def test_presets_are_immutable() -> None:
    from backend.presets import get_preset

    p = get_preset("720p_mobile")
    with pytest.raises((AttributeError, TypeError)):
        p.width = 999  # type: ignore[misc]


def test_preset_gpu_bitrate_format() -> None:
    """GPU bitrate strings should end in 'k' (e.g. '2500k')."""
    from backend.presets import list_presets

    for p in list_presets():
        assert p.gpu_bitrate.endswith("k"), f"{p.name}: gpu_bitrate must end in 'k'"
        assert p.gpu_maxrate.endswith("k"), f"{p.name}: gpu_maxrate must end in 'k'"
        assert p.gpu_bufsize.endswith("k"), f"{p.name}: gpu_bufsize must end in 'k'"
