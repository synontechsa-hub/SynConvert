"""File scanner for SynConvert.

Recursively walks input directories and discovers supported video files.
Produces ScanResult objects that carry both the absolute source path and
the relative path (used later to mirror the directory structure in output).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Supported input extensions (lowercase)
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".mkv", ".mp4", ".webm"})


@dataclass
class ScanResult:
    """A single discovered video file."""

    source_path: Path
    """Absolute path to the source file."""

    relative_path: Path
    """Path relative to the scan root (used for directory mirroring)."""

    @property
    def filename(self) -> str:
        return self.source_path.name

    @property
    def parent_name(self) -> str:
        """Immediate parent folder name (e.g. 'Season 1')."""
        return self.source_path.parent.name


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scan_directory(
    root: str | Path,
    output_dir: str | Path | None = None,
) -> list[ScanResult]:
    """Recursively scan *root* for supported video files.

    Args:
        root:       Directory to scan.
        output_dir: If provided, raise ValueError if root resolves to the
                    same path as output_dir (safety guard against in-place
                    conversion).

    Returns:
        List of ScanResult, sorted by relative path for deterministic ordering.

    Raises:
        FileNotFoundError: If root doesn't exist.
        NotADirectoryError: If root is a file, not a folder.
        ValueError: If root == output_dir or output_dir is inside root.
    """
    root = Path(root).resolve()
    _validate_root(root, output_dir)

    results: list[ScanResult] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            ext = Path(filename).suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                abs_path = Path(dirpath) / filename
                rel_path = abs_path.relative_to(root)
                results.append(ScanResult(source_path=abs_path, relative_path=rel_path))

    results.sort(key=lambda r: str(r.relative_path))
    return results


def _validate_root(root: Path, output_dir: str | Path | None) -> None:
    """Internal validation helper."""
    if not root.exists():
        raise FileNotFoundError(f"Input directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {root}")
    if output_dir is not None:
        output_resolved = Path(output_dir).resolve()

        # Guard: input and output must not be the same path
        if root == output_resolved:
            raise ValueError(
                f"Input and output directories must not be the same path.\n"
                f"  Input:  {root}\n"
                f"  Output: {output_resolved}"
            )

        # FIX #2: original code raised ValueError inside a try/except ValueError
        # which silently caught its own error, making this guard do nothing.
        # Now we check explicitly without relying on exception control flow.
        try:
            output_resolved.relative_to(root)
            # If relative_to() succeeds, output IS inside root — that's bad.
            raise ValueError(
                f"Output directory must not be inside the input directory.\n"
                f"  Input:  {root}\n"
                f"  Output: {output_resolved}"
            )
        except ValueError as exc:
            # Re-raise only our own intentional error.
            # relative_to() raises ValueError when paths are unrelated (good).
            if "must not be inside" in str(exc):
                raise
            # Otherwise: output is NOT inside root — this is correct, continue.
