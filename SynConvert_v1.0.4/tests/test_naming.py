"""Tests for synconvert.naming"""

from __future__ import annotations

import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Season extraction
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("folder,expected", [
    ("Season 1",       1),
    ("Season 2",       2),
    ("Season 01",      1),
    ("S2",             2),
    ("S03",            3),
    ("series 4",       4),
    ("2nd Season",     2),
    ("3rd Season",     3),
    ("Extras",         1),    # No match → default 1
    ("OVA",            1),    # No match → default 1
    ("Season 12",     12),
])
def test_extract_season(folder: str, expected: int) -> None:
    from backend.naming import extract_season
    assert extract_season(folder) == expected


# ---------------------------------------------------------------------------
# Episode extraction
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stem,expected", [
    # SxxExx notation
    ("[SubGroup] Show Name - S01E05 [1080p]",                5),
    ("Show.S02E12.HDTV",                                    12),
    # Fansub hyphen style
    ("[SubGroup] Anime Show - 07 [720p][HEVC]",              7),
    ("[Erai-raws] Dandadan - 12 [1080p][AAC]",              12),
    # Episode word
    ("Anime Show Episode 03",                                3),
    ("Show Ep.11 BluRay",                                   11),
    # Trailing number
    ("ShowName_05",                                          5),
    ("ShowName-24",                                         24),
    # Three digit
    ("[Group] Long Show - 101 [720p]",                     101),
])
def test_extract_episode(stem: str, expected: int) -> None:
    from backend.naming import extract_episode
    assert extract_episode(stem) == expected


# ---------------------------------------------------------------------------
# Title extraction
# ---------------------------------------------------------------------------

def test_extract_title_strips_noise() -> None:
    from backend.naming import extract_title
    stem = "[Erai-raws] Dandadan - 12 [1080p][AAC][MultiSub]"
    title = extract_title(stem)
    # Should not contain noise tags
    assert title is not None
    assert "[" not in title
    assert "1080p" not in title
    assert "AAC" not in title


def test_extract_title_returns_none_for_unrecognisable() -> None:
    from backend.naming import extract_title
    # Very short remainder after cleaning → None
    title = extract_title("01")
    assert title is None


# ---------------------------------------------------------------------------
# Filename rendering
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("season,episode,title,template,expected", [
    (1,  3,  "The Dark",   "S{S:02d}E{E:02d} - {title}", "S01E03 - The Dark.mkv"),
    (2, 12,  "Last Stand", "S{S:02d}E{E:02d} - {title}", "S02E12 - Last Stand.mkv"),
    (1,  5,  "Ep 5",       "{S}x{E:02d}",                "1x05.mkv"),
    (3,  7,  "Title Here", "Episode {E}",                "Episode 7.mkv"),
])
def test_render_filename(
    season: int, episode: int, title: str, template: str, expected: str
) -> None:
    from backend.naming import render_filename
    result = render_filename(season, episode, title, template, "mkv")
    assert result == expected


def test_render_filename_sanitises_illegal_chars() -> None:
    from backend.naming import render_filename
    result = render_filename(1, 1, "A/B:C?D", "S{S:02d}E{E:02d} - {title}", "mkv")
    assert "/" not in result
    assert ":" not in result
    assert "?" not in result


def test_render_filename_fallback_on_bad_template() -> None:
    from backend.naming import render_filename
    # Bad template key — should fall back gracefully
    result = render_filename(1, 5, "Title", "{bad_key}", "mkv")
    # Should not raise and should produce a .mkv file
    assert result.endswith(".mkv")
