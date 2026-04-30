from pathlib import Path

def _default_output_dir() -> Path:
    return Path.cwd() / "SynConvert_Output"

def _default_log_dir() -> Path:
    return Path.cwd() / "logs"

def _default_queue_file() -> Path:
    return Path.cwd() / "synconvert_queue.json"

def _default_config_file() -> Path:
    return Path.cwd() / "synconvert_config.json"
