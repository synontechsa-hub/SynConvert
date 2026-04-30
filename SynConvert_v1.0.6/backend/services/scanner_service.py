import os
from pathlib import Path
from typing import List, Optional
from backend.models.scan import ScanResult
from backend.core.exceptions import ScannerError

SUPPORTED_EXTENSIONS = frozenset({".mkv", ".mp4", ".webm"})

class ScannerService:
    """Service for discovering video files in the filesystem."""

    def scan(self, root: str | Path, output_dir: Optional[str | Path] = None) -> List[ScanResult]:
        """Recursively scan root for supported video files."""
        root_path = Path(root).resolve()
        
        self._validate(root_path, output_dir)

        results: List[ScanResult] = []
        try:
            for dirpath, _dirnames, filenames in os.walk(root_path):
                for filename in filenames:
                    ext = Path(filename).suffix.lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        abs_path = Path(dirpath) / filename
                        rel_path = abs_path.relative_to(root_path)
                        results.append(ScanResult(source_path=abs_path, relative_path=rel_path))
        except Exception as exc:
            raise ScannerError(f"Directory scan failed: {exc}")

        results.sort(key=lambda r: str(r.relative_path))
        return results

    def _validate(self, root: Path, output_dir: Optional[str | Path]) -> None:
        """Validate input/output directory constraints."""
        if not root.exists():
            raise FileNotFoundError(f"Input directory does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Input path is not a directory: {root}")
            
        if output_dir is not None:
            output_resolved = Path(output_dir).resolve()
            if root == output_resolved:
                raise ValueError("Input and output directories must not be the same path.")
            
            try:
                output_resolved.relative_to(root)
                raise ValueError("Output directory must not be inside the input directory.")
            except ValueError as exc:
                if "must not be inside" in str(exc):
                    raise
                # Related to paths being unrelated — this is good.
                pass
