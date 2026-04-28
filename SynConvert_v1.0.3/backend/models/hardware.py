from dataclasses import dataclass
from enum import Enum, auto

class EncoderBackend(Enum):
    NVENC = auto()
    QSV = auto()
    CPU = auto()

@dataclass(frozen=True)
class EncoderInfo:
    """Result of hardware detection."""
    backend: EncoderBackend
    video_encoder: str   # e.g. "h264_nvenc", "h264_qsv", "libx264"
    label: str           # Human-readable label for logging
    is_hardware: bool    # True if GPU-accelerated
