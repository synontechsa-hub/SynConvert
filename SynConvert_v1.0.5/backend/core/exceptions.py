"""Custom exceptions for SynConvert."""

class SynConvertError(Exception):
    """Base class for all SynConvert exceptions."""
    pass

class ConfigError(SynConvertError):
    """Raised when configuration is missing or malformed."""
    pass

class HardwareError(SynConvertError):
    """Raised when hardware detection or initialization fails."""
    pass

class GPUInitError(HardwareError):
    """Specific error when a GPU backend exists but fails to start."""
    pass

class ScannerError(SynConvertError):
    """Raised during directory scanning or file identification."""
    pass

class NamingError(SynConvertError):
    """Raised during template parsing or filename generation."""
    pass

class ConversionError(SynConvertError):
    """Base class for conversion failures."""
    pass

class FFmpegError(ConversionError):
    """Raised when FFmpeg returns a non-zero exit code or crashes."""
    pass

class DiskFullError(ConversionError):
    """Raised when the output drive has insufficient space."""
    pass

class PresetError(SynConvertError):
    """Raised when a requested preset is missing or invalid."""
    pass
