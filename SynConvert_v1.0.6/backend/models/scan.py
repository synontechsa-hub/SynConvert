from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ScanResult:
    """A single discovered video file."""
    source_path: Path
    relative_path: Path

    @property
    def filename(self) -> str:
        return self.source_path.name

    @property
    def parent_name(self) -> str:
        return self.source_path.parent.name

@dataclass
class NameProposal:
    """A proposed output name for a single file."""
    scan_result: ScanResult
    season: int
    episode: int
    title: str
    output_filename: str
    output_path: Path
    skipped: bool = False
