import json
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

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
    if not _COLOR: return text
    return "".join(codes) + text + _RESET

@dataclass
class ConversionRecord:
    source: str
    output: str
    preset: str
    encoder: str
    status: str
    duration_seconds: float = 0.0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class SynLogger:
    """Centralized logger for console and file output."""

    def __init__(self, log_dir: str | Path):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._session_start = datetime.now()
        self._log_file = self._log_dir / f"session_{self._session_start.strftime('%Y%m%d_%H%M%S')}.json"
        self._records: List[ConversionRecord] = []

    def session_start(self, total_files: int, encoder_label: str):
        print()
        print(_fmt("━" * 60, _BOLD))
        print(_fmt("  SynConvert v1.0.4", _BOLD, _CYAN))
        print(f"  Encoder  : {_fmt(encoder_label, _BOLD)}")
        print(f"  Files    : {_fmt(str(total_files), _BOLD)}")
        print(_fmt("━" * 60, _BOLD))
        print()

    def session_end(self, show_notification: bool = False):
        success = sum(1 for r in self._records if r.status == "success")
        failed  = sum(1 for r in self._records if r.status == "failed")
        total_time = sum(r.duration_seconds for r in self._records)

        print()
        print(_fmt("━" * 60, _BOLD))
        print(_fmt("  Session Complete", _BOLD))
        print(f"  {_fmt(str(success), _GREEN, _BOLD)} succeeded  "
              f"{_fmt(str(failed), _RED, _BOLD)} failed")
        print(f"  Total time : {_fmt(self._format_duration(total_time), _BOLD)}")
        print(_fmt("━" * 60, _BOLD))
        print()
        self._flush()

        if show_notification:
            self.notify(
                "Batch Complete", 
                f"Successfully converted {success} files ({failed} failed)."
            )

    def notify(self, title: str, message: str):
        """Send a system notification using plyer."""
        try:
            from plyer import notification
            notification.notify(
                title=f"SynConvert: {title}",
                message=message,
                app_name="SynConvert",
                timeout=10
            )
        except Exception:
            pass # Notifications shouldn't crash the app

    def file_start(self, index: int, total: int, source: str, job_id: str = "") -> float:
        prefix = f"[{job_id}] " if job_id else ""
        label = _fmt(f"{prefix}[{index}/{total}]", _DIM)
        print(f"{label} {_fmt('Converting', _CYAN)} {self._truncate(source, 55)}")
        return time.monotonic()

    def file_success(self, source: str, output: str, preset: str, encoder: str, start_time: float, job_id: str = ""):
        elapsed = time.monotonic() - start_time
        prefix = f"[{job_id}] " if job_id else ""
        print(f"        {prefix}{_fmt('✓', _GREEN)} Done in {self._format_duration(elapsed)}")
        self._records.append(ConversionRecord(
            source=source, output=output, preset=preset,
            encoder=encoder, status="success", duration_seconds=elapsed
        ))
        self._flush()

    def file_failed(self, source: str, output: str, preset: str, encoder: str, start_time: float, error: str, job_id: str = ""):
        elapsed = time.monotonic() - start_time
        prefix = f"[{job_id}] " if job_id else ""
        print(f"        {prefix}{_fmt('✗', _RED)} FAILED: {error}")
        self._records.append(ConversionRecord(
            source=source, output=output, preset=preset,
            encoder=encoder, status="failed", duration_seconds=elapsed, error=error
        ))
        self._flush()

    def info(self, msg: str, job_id: str = ""): 
        prefix = f"[{job_id}] " if job_id else ""
        print(f"  {prefix}{_fmt('ℹ', _CYAN)} {msg}")
        
    def warning(self, msg: str, job_id: str = ""): 
        prefix = f"[{job_id}] " if job_id else ""
        print(f"  {prefix}{_fmt('⚠', _YELLOW)} {msg}")
        
    def error(self, msg: str, job_id: str = ""): 
        prefix = f"[{job_id}] " if job_id else ""
        print(f"  {prefix}{_fmt('✗', _RED)} {msg}")

    def _flush(self):
        data = {
            "session_start": self._session_start.isoformat(),
            "records": [asdict(r) for r in self._records],
        }
        with open(self._log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _truncate(self, s: str, width: int) -> str:
        return s if len(s) <= width else "…" + s[-(width - 1):]

    def _format_duration(self, seconds: float) -> str:
        if seconds < 60: return f"{seconds:.1f}s"
        m, s = divmod(int(seconds), 60)
        if m < 60: return f"{m}m{s:02d}s"
        h, m = divmod(m, 60)
        return f"{h}h{m:02d}m{s:02d}s"
