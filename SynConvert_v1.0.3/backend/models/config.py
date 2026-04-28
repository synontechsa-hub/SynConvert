from dataclasses import dataclass, field
from typing import Literal
from backend.utils.paths import _default_output_dir, _default_log_dir, _default_queue_file

PresetName = Literal["720p_mobile", "480p_saver"]

@dataclass
class SynConvertConfig:
    """User-editable global configuration."""

    # --- Output ---
    output_dir: str = field(default_factory=lambda: str(_default_output_dir()))

    # --- Conversion ---
    default_preset: PresetName = "720p_mobile"

    # --- Naming ---
    naming_template: str = "S{S:02d}E{E:02d} - {title}"

    # --- Behaviour ---
    review_before_convert: bool = True
    skip_existing: bool = True
    max_retries: int = 1

    # --- Hardware ---
    force_encoder: str | None = None

    # --- Logging & Queue ---
    log_dir: str = field(default_factory=lambda: str(_default_log_dir()))
    queue_file: str = field(default_factory=lambda: str(_default_queue_file()))
