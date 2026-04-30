import json
from pathlib import Path
from dataclasses import asdict
from backend.models.config import SynConvertConfig
from backend.utils.paths import _default_config_file
from backend.core.exceptions import ConfigError

class ConfigService:
    """Service for managing application configuration."""

    def __init__(self, config_path: Path | None = None):
        self._path = config_path or _default_config_file()

    def load(self) -> SynConvertConfig:
        """Load config from JSON file, or return defaults if file doesn't exist."""
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    data = json.load(f)
                
                # Filter unknown fields to avoid errors on schema changes
                known = {k for k in SynConvertConfig.__dataclass_fields__}
                filtered = {k: v for k, v in data.items() if k in known}
                return SynConvertConfig(**filtered)
            except (json.JSONDecodeError, TypeError) as exc:
                # In a real service, we might log this. 
                # For now, we fall back to defaults but keep the file.
                return SynConvertConfig()
        return SynConvertConfig()

    def save(self, cfg: SynConvertConfig) -> None:
        """Persist config to JSON file."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(asdict(cfg), f, indent=2)
        except Exception as exc:
            raise ConfigError(f"Failed to save configuration to {self._path}: {exc}")

    def update_from_json(self, json_str: str) -> SynConvertConfig:
        """Update current config with values from a JSON string."""
        try:
            updates = json.loads(json_str)
            cfg = self.load()
            for k, v in updates.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
            self.save(cfg)
            return cfg
        except json.JSONDecodeError:
            raise ConfigError("Invalid JSON provided for configuration update.")
        except Exception as exc:
            raise ConfigError(f"Configuration update failed: {exc}")
