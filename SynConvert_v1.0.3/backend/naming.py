"""Output filename generation for SynConvert.

Handles:
  - Season number extraction from folder names
  - Episode number extraction from filenames (multiple regex strategies)
  - Episode title extraction from filenames
  - Custom naming templates
  - Review mode: show source → output mapping and prompt for confirmation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from backend.scanner import ScanResult

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class NameProposal:
    """A proposed output name for a single file."""

    scan_result: ScanResult
    season: int
    episode: int
    title: str
    output_filename: str  # Fully rendered filename (e.g. "S01E03 - The Dark.mkv")
    output_path: Path     # Absolute output path
    skipped: bool = False  # Set to True in review mode if user skips


# ---------------------------------------------------------------------------
# Season extraction
# ---------------------------------------------------------------------------

# Ordered from most specific to least specific
_SEASON_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"season\s*(\d+)", re.IGNORECASE),
    re.compile(r"\bS(\d+)\b", re.IGNORECASE),
    re.compile(r"\bser(?:ies)?\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"(\d+)(?:st|nd|rd|th)\s*season", re.IGNORECASE),
]


def extract_season(folder_name: str) -> int:
    """Infer season number from a folder name. Returns 1 if undetectable."""
    for pattern in _SEASON_PATTERNS:
        m = pattern.search(folder_name)
        if m:
            return int(m.group(1))
    return 1


# ---------------------------------------------------------------------------
# Episode extraction
# ---------------------------------------------------------------------------

# Strategies tried in order; first match wins.
_EPISODE_PATTERNS: list[re.Pattern[str]] = [
    # Standard SxxExx notation: S01E05, s1e5
    re.compile(r"[Ss]\d+[Ee](\d+)"),
    # Episode word: "Episode 12", "Ep.3", "EP 04"
    re.compile(r"\bEp(?:isode)?\.?\s*(\d+)\b", re.IGNORECASE),
    # Hyphen-separated episode (common in fansubs): "Show Name - 12 [tag]"
    re.compile(r"(?:^|[\s\-_])(\d{2,3})(?:\s*[\[\(v\.]|$)"),
    # Simple trailing number before extension: "ShowName_05.mkv"
    re.compile(r"[_\s\-\.](\d{1,3})(?:\.\w+)?$"),
]


def extract_episode(filename_stem: str) -> int:
    """Extract episode number from a filename stem. Returns 0 if undetectable."""
    for pattern in _EPISODE_PATTERNS:
        m = pattern.search(filename_stem)
        if m:
            try:
                return int(m.group(1))
            except (IndexError, ValueError):
                continue
    return 0


# ---------------------------------------------------------------------------
# Title extraction
# ---------------------------------------------------------------------------

# Remove common noise tokens from fansub filenames
_NOISE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\[.*?\]"),          # [SubGroup], [1080p], [HEVC], etc.
    re.compile(r"\(.*?\)"),          # (BD), (2024), etc.
    re.compile(r"\b(?:BDRip|BluRay|WEBRip|WEB-DL|HDTV|DVDRip)\b", re.IGNORECASE),
    re.compile(r"\b(?:\d{3,4}p)\b", re.IGNORECASE),          # 1080p, 720p
    re.compile(r"\b(?:HEVC|H\.265|H265|x264|x265|AVC)\b", re.IGNORECASE),
    re.compile(r"\b(?:AAC|AC3|DTS|FLAC|MP3)\b", re.IGNORECASE),
    re.compile(r"\bS\d+E\d+\b", re.IGNORECASE),              # S01E05
    re.compile(r"\bEp(?:isode)?\.?\s*\d+\b", re.IGNORECASE), # Episode 12
    re.compile(r"(?:^|[\s_\-])\d{1,3}(?=[\s_\-\.]|$)"),     # bare episode numbers
]


def extract_title(filename_stem: str) -> str | None:
    """Try to extract a human-readable episode title from a filename stem.

    Returns None if no meaningful title can be found (caller uses fallback).
    """
    text = filename_stem

    # Remove noise
    for pat in _NOISE_PATTERNS:
        text = pat.sub(" ", text)

    # Normalise separators to spaces
    text = re.sub(r"[_\-\.]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # If what's left looks like a show name (which we don't want in the title),
    # we can't reliably isolate an episode title — return None.
    if not text or len(text) < 3:
        return None

    return text.title()  # Title-case the result


# ---------------------------------------------------------------------------
# Naming template rendering
# ---------------------------------------------------------------------------

DEFAULT_TEMPLATE = "S{S:02d}E{E:02d} - {title}"


def render_filename(
    season: int,
    episode: int,
    title: str,
    template: str,
    container: str = "mkv",
) -> str:
    """Render a filename using a format_map-compatible template.

    Template variables:
        S     — season number (int)
        E     — episode number (int)
        title — episode title (str)

    The container extension is appended automatically.
    """
    try:
        name = template.format(S=season, E=episode, title=title)
    except (KeyError, ValueError):
        # Malformed template — use safe default
        name = DEFAULT_TEMPLATE.format(S=season, E=episode, title=title)

    # Sanitise illegal filename characters (Windows + Unix)
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return f"{name}.{container}"


# ---------------------------------------------------------------------------
# Season inference from scan results
# ---------------------------------------------------------------------------

def _season_from_result(result: ScanResult) -> int:
    """Walk the parent folders of a file looking for a season indicator."""
    # Check immediate parent first, then grandparent (common: Show/Season 1/ep.mkv)
    for parent in result.source_path.parents:
        season = extract_season(parent.name)
        if season != 1 or re.search(r"season\s*1|S0*1\b", parent.name, re.IGNORECASE):
            return season
    return 1


# ---------------------------------------------------------------------------
# Core proposal builder
# ---------------------------------------------------------------------------


def build_proposals(
    results: list[ScanResult],
    output_root: Path,
    template: str = DEFAULT_TEMPLATE,
    container: str = "mkv",
) -> list[NameProposal]:
    """Build NameProposal list from scan results.

    Args:
        results:     Files discovered by the scanner.
        output_root: Root directory where output files will be written.
        template:    Filename template string.
        container:   Output file extension (without dot).

    Returns:
        List of NameProposal, one per input file.
    """
    proposals: list[NameProposal] = []

    for result in results:
        stem = result.source_path.stem
        season = _season_from_result(result)
        episode = extract_episode(stem)
        raw_title = extract_title(stem)

        if raw_title:
            title = raw_title
        elif episode:
            title = f"Episode {episode:02d}"
        else:
            title = result.source_path.stem  # Last resort: use raw stem

        # Episode fallback counter (per season)
        if not episode:
            season_eps = [p for p in proposals if p.season == season]
            ep_num = len(season_eps) + 1
        else:
            ep_num = episode

        filename = render_filename(season, ep_num, title, template, container)

        # Mirror relative directory structure
        output_dir = output_root / result.relative_path.parent
        output_path = output_dir / filename

        proposals.append(
            NameProposal(
                scan_result=result,
                season=season,
                episode=ep_num,
                title=title,
                output_filename=filename,
                output_path=output_path,
            )
        )

    return proposals


# ---------------------------------------------------------------------------
# Review mode (interactive CLI)
# ---------------------------------------------------------------------------

_COL_W = 55  # column width for table display


def _truncate(s: str, width: int) -> str:
    return s if len(s) <= width else s[: width - 1] + "…"


def review_proposals(proposals: list[NameProposal]) -> list[NameProposal]:
    """Print a source → output mapping table and prompt the user for confirmation.

    The user can:
        - Press Enter / type 'y' / 'all' to accept everything
        - Type 'n' to reject a specific file (mark as skipped)
        - Type a custom name to override the proposed filename

    Returns:
        The same list, with .skipped set and .output_filename / .output_path
        potentially modified by user input.
    """
    print()
    print("━" * 120)
    print(f"  {'SOURCE FILE':<{_COL_W}}  {'→':<3}  {'PROPOSED OUTPUT':<{_COL_W}}")
    print("━" * 120)

    for i, p in enumerate(proposals):
        src = _truncate(str(p.scan_result.relative_path), _COL_W)
        out = _truncate(p.output_filename, _COL_W)
        print(f"  {src:<{_COL_W}}       {out:<{_COL_W}}")

    print("━" * 120)
    print(f"  Total: {len(proposals)} file(s)")
    print()

    # Bulk confirm
    bulk = input("Accept all proposed names? [Y/n/edit]: ").strip().lower()
    if bulk in ("", "y", "yes", "all"):
        return proposals

    if bulk in ("n", "no"):
        print("Conversion cancelled by user.")
        for p in proposals:
            p.skipped = True
        return proposals

    # Per-file review
    print("\nReviewing each file. Press Enter to accept, 'n' to skip, or type a custom name.\n")
    for p in proposals:
        src = str(p.scan_result.relative_path)
        print(f"  Source : {src}")
        print(f"  Output : {p.output_filename}")
        answer = input("  [Enter=accept | n=skip | custom name]: ").strip()
        if answer.lower() == "n":
            p.skipped = True
            print("  ↳ Skipped.\n")
        elif answer:
            # Custom name provided — sanitise and apply
            custom = re.sub(r'[<>:"/\\|?*]', "_", answer)
            if not custom.lower().endswith(f".{p.output_path.suffix.lstrip('.')}"):
                custom += p.output_path.suffix
            p.output_filename = custom
            p.output_path = p.output_path.parent / custom
            print(f"  ↳ Renamed to: {custom}\n")
        else:
            print("  ↳ Accepted.\n")

    return proposals
