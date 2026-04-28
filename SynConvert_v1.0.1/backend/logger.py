"""Logging system for SynConvert.

Provides:
  - Console progress output (with colour when supported)
  - Per-session JSON log file with structured conversion records
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# ANSI colour helpers (degrade gracefully on Windows without ANSI)
# ---------------------------------------------------------------------------

def _supports_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


_COLOR = _supports_color()

_RESET  = "\033[0m"   if _COLOR else ""
_BOLD   = "\033[1m"   if _COLOR else ""
_GREEN  = "\033[92m"  if _COLOR else ""
_YELLOW = "\033[93m"  if _COLOR else ""
_RED    = "\033[91m"  if _COLOR else ""
_CYAN   = "\033[96m"  if _COLOR else ""
_DIM    = "\033[2m"   if _COLOR else ""


def _fmt(text: str, *codes: str) -> str:
    if not _COLOR:
        return text
    return "".join(codes) + text + _RESET


# ---------------------------------------------------------------------------
# Log record
# ---------------------------------------------------------------------------

@dataclass
class ConversionRecord:
    """Structured record for a single file conversion."""

    source: str
    output: str
    preset: str
    encoder: str
    status: str           # "success" | "failed" | "skipped"
    duration_seconds: float = 0.0
    error: str | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

class SynLogger:
    """Combined console + JSON file logger."""

    def __init__(self, log_dir: str | Path) -> None:
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._session_start = datetime.now()
        self._log_file = self._log_dir / f"session_{self._session_start.strftime('%Y%m%d_%H%M%S')}.json"
        self._records: list[ConversionRecord] = []
        self._total = 0
        self._done = 0

    # ------------------------------------------------------------------
    # Session events
    # ------------------------------------------------------------------

    def session_start(self, total_files: int, encoder_label: str) -> None:
        self._total = total_files
        print()
        print(_fmt("━" * 60, _BOLD))
        print(_fmt("  SynConvert v1.0.1", _BOLD, _CYAN))
        print(f"  Encoder  : {_fmt(encoder_label, _BOLD)}")
        print(f"  Files    : {_fmt(str(total_files), _BOLD)}")
        print(f"  Log      : {self._log_file}")
        print(_fmt("━" * 60, _BOLD))
        print()

    def session_end(self) -> None:
        success = sum(1 for r in self._records if r.status == "success")
        failed  = sum(1 for r in self._records if r.status == "failed")
        skipped = sum(1 for r in self._records if r.status == "skipped")
        total_time = sum(r.duration_seconds for r in self._records)

        print()
        print(_fmt("━" * 60, _BOLD))
        print(_fmt("  Session Complete", _BOLD))
        print(f"  {_fmt(str(success), _GREEN, _BOLD)} succeeded  "
              f"{_fmt(str(failed), _RED, _BOLD)} failed  "
              f"{_fmt(str(skipped), _YELLOW, _BOLD)} skipped")
        print(f"  Total time : {_fmt(_format_duration(total_time), _BOLD)}")
        print(_fmt("━" * 60, _BOLD))
        print()

        self._flush()

    # ------------------------------------------------------------------
    # Per-file events
    # ------------------------------------------------------------------

    def file_start(self, index: int, total: int, source: str) -> float:
        """Call when starting a file. Returns start timestamp."""
        self._done = index
        label = _fmt(f"[{index}/{total}]", _DIM)
        print(f"{label} {_fmt('Converting', _CYAN)} {_truncate(source, 55)}")
        return time.monotonic()

    def file_success(
        self,
        source: str,
        output: str,
        preset: str,
        encoder: str,
        start_time: float,
    ) -> None:
        elapsed = time.monotonic() - start_time
        print(f"        {_fmt('✓', _GREEN)} Done in {_format_duration(elapsed)}"
              f"  →  {_truncate(output, 50)}")
        self._records.append(ConversionRecord(
            source=source, output=output, preset=preset,
            encoder=encoder, status="success", duration_seconds=elapsed,
        ))
        self._flush()

    def file_failed(
        self,
        source: str,
        output: str,
        preset: str,
        encoder: str,
        start_time: float,
        error: str,
    ) -> None:
        elapsed = time.monotonic() - start_time
        print(f"        {_fmt('✗', _RED)} FAILED in {_format_duration(elapsed)}: {error}")
        self._records.append(ConversionRecord(
            source=source, output=output, preset=preset,
            encoder=encoder, status="failed", duration_seconds=elapsed, error=error,
        ))
        self._flush()

    def file_skipped(self, source: str, reason: str = "") -> None:
        tag = f" ({reason})" if reason else ""
        print(f"        {_fmt('–', _YELLOW)} Skipped{tag}  {_truncate(source, 50)}")
        self._records.append(ConversionRecord(
            source=source, output="", preset="", encoder="", status="skipped",
        ))

    def retry(self, source: str, attempt: int) -> None:
        print(f"        {_fmt('⟳', _YELLOW)} Retrying ({attempt})…")

    def info(self, msg: str) -> None:
        print(f"  {_fmt('ℹ', _CYAN)} {msg}")

    def warning(self, msg: str) -> None:
        print(f"  {_fmt('⚠', _YELLOW)} {msg}")

    def error(self, msg: str) -> None:
        print(f"  {_fmt('✗', _RED)} {msg}")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _flush(self) -> None:
        """Write current records to JSON log file."""
        data = {
            "session_start": self._session_start.isoformat(),
            "records": [asdict(r) for r in self._records],
        }
        with open(self._log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(s: str, width: int) -> str:
    return s if len(s) <= width else "…" + s[-(width - 1):]


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m{s:02d}s"
