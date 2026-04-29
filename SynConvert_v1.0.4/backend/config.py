"""Global configuration for SynConvert."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Root of the backend package
_PACKAGE_DIR = Path(__file__).parent.resolve()

# Default locations — resolved lazily at call time (NOT at import time).
# Using functions ensures the correct CWD is used even when the backend is
# spawned as a subprocess by the Flutter UI from a different working directory.
def _default_output_dir() -> Path:
    return Path.cwd() / "SynConvert_Output"

def _default_log_dir() -> Path:
    return Path.cwd() / "logs"

def _default_queue_file() -> Path:
    return Path.cwd() / "synconvert_queue.json"

def _default_config_file() -> Path:
    return Path.cwd() / "synconvert_config.json"

# Keep module-level constants for backwards-compat, but they now snapshot
# the CWD at the time of first import — prefer the functions above internally.
DEFAULT_OUTPUT_DIR: Path = _default_output_dir()
DEFAULT_LOG_DIR: Path = _default_log_dir()
DEFAULT_QUEUE_FILE: Path = _default_queue_file()
DEFAULT_CONFIG_FILE: Path = _default_config_file()

# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------

PresetName = Literal["720p_mobile", "480p_saver"]
NamingTemplate = str  # e.g. "S{S:02d}E{E:02d} - {title}" or custom


@dataclass
class SynConvertConfig:
    """User-editable global configuration.

    Persisted as JSON at DEFAULT_CONFIG_FILE between runs.
    """

    # --- Output ---
    output_dir: str = field(default_factory=lambda: str(_default_output_dir()))
    """Absolute path to the root output directory."""

    # --- Conversion ---
    default_preset: PresetName = "720p_mobile"
    """Default preset to use when none is specified."""

    # --- Naming ---
    naming_template: str = "S{S:02d}E{E:02d} - {title}"
    """Python str.format_map() template for output filenames.

    Available keys:
        S     — season number (int)
        E     — episode number (int)
        title — episode title (str, may be 'Episode N' fallback)
    """

    # --- Behaviour ---
    review_before_convert: bool = True
    """If True, show source→output name mapping and ask for confirmation."""

    skip_existing: bool = True
    """If True, skip files that already exist in the output directory."""

    max_retries: int = 1
    """Number of times to retry a failed FFmpeg job before marking it failed."""

    # --- Hardware ---
    force_encoder: str | None = None
    """Force a specific FFmpeg encoder (e.g. 'libx264'). None = auto-detect."""

    # --- Logging ---
    log_dir: str = field(default_factory=lambda: str(_default_log_dir()))
    queue_file: str = field(default_factory=lambda: str(_default_queue_file()))


# ---------------------------------------------------------------------------
# Load / save helpers
# ---------------------------------------------------------------------------


def load_config(path: Path | None = None) -> SynConvertConfig:
    """Load config from JSON file, or return defaults if file doesn't exist."""
    path = path or _default_config_file()
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            # Only keep known fields to avoid errors on schema changes
            known = {k for k in SynConvertConfig.__dataclass_fields__}
            filtered = {k: v for k, v in data.items() if k in known}
            return SynConvertConfig(**filtered)
        except (json.JSONDecodeError, TypeError):
            pass  # Corrupt config — fall back to defaults
    return SynConvertConfig()


def save_config(cfg: SynConvertConfig, path: Path | None = None) -> None:
    """Persist config to JSON file."""
    path = path or _default_config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, indent=2)
