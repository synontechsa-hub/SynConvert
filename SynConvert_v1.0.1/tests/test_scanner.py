"""Tests for synconvert.scanner"""

from __future__ import annotations

import pytest
from pathlib import Path


def test_scan_finds_supported_files(tmp_path: Path) -> None:
    """Scanner should find .mkv, .mp4, .webm files recursively."""
    from backend.scanner import scan_directory, SUPPORTED_EXTENSIONS

    # Create a nested structure
    season1 = tmp_path / "Season 1"
    season1.mkdir()
    (season1 / "ep01.mkv").touch()
    (season1 / "ep02.mp4").touch()
    (season1 / "ep03.webm").touch()
    (season1 / "poster.jpg").touch()       # should be ignored
    (season1 / "subtitle.srt").touch()     # should be ignored

    results = scan_directory(tmp_path)

    assert len(results) == 3
    exts = {r.source_path.suffix.lower() for r in results}
    assert exts == {".mkv", ".mp4", ".webm"}


def test_scan_returns_sorted_results(tmp_path: Path) -> None:
    """Results should be sorted by relative path for deterministic ordering."""
    from backend.scanner import scan_directory

    (tmp_path / "ep03.mkv").touch()
    (tmp_path / "ep01.mkv").touch()
    (tmp_path / "ep02.mkv").touch()

    results = scan_directory(tmp_path)
    names = [r.source_path.name for r in results]
    assert names == sorted(names)


def test_scan_relative_path(tmp_path: Path) -> None:
    """ScanResult.relative_path should be relative to the scan root."""
    from backend.scanner import scan_directory

    sub = tmp_path / "Season 1"
    sub.mkdir()
    (sub / "ep01.mkv").touch()

    results = scan_directory(tmp_path)
    assert len(results) == 1
    assert results[0].relative_path == Path("Season 1") / "ep01.mkv"


def test_scan_rejects_nonexistent_root() -> None:
    from backend.scanner import scan_directory

    with pytest.raises(FileNotFoundError):
        scan_directory("/nonexistent/path/that/does/not/exist")


def test_scan_rejects_file_as_root(tmp_path: Path) -> None:
    from backend.scanner import scan_directory

    f = tmp_path / "file.mkv"
    f.touch()
    with pytest.raises(NotADirectoryError):
        scan_directory(f)


def test_scan_rejects_same_input_output(tmp_path: Path) -> None:
    from backend.scanner import scan_directory

    with pytest.raises(ValueError, match="must not be the same"):
        scan_directory(tmp_path, output_dir=tmp_path)


def test_scan_rejects_output_inside_input(tmp_path: Path) -> None:
    from backend.scanner import scan_directory

    output_inside = tmp_path / "Output"
    output_inside.mkdir()
    with pytest.raises(ValueError, match="must not be inside"):
        scan_directory(tmp_path, output_dir=output_inside)
