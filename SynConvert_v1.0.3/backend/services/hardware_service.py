import subprocess
from pathlib import Path
from typing import List
import static_ffmpeg.run

from backend.models.hardware import EncoderInfo, EncoderBackend
from backend.core.exceptions import HardwareError, GPUInitError

def _ffmpeg_bin() -> str:
    """Resolve the static_ffmpeg binary path."""
    try:
        ffmpeg, _ = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
        return str(ffmpeg)
    except Exception as exc:
        raise HardwareError(f"FFmpeg binary not found: {exc}")

class HardwareService:
    """Service for hardware encoder discovery and selection."""

    def __init__(self):
        self._ffmpeg = _ffmpeg_bin()

    def get_available_backends(self) -> List[EncoderInfo]:
        """Detect all available hardware backends on this system."""
        backends = []
        
        # 1. Check NVIDIA NVENC
        if self._test_encoder("h264_nvenc", "yuv420p"):
            backends.append(EncoderInfo(
                backend=EncoderBackend.NVENC,
                video_encoder="h264_nvenc",
                label="NVIDIA NVENC (GPU)",
                is_hardware=True
            ))
            
        # 2. Check Intel QSV
        if self._test_encoder("h264_qsv", "nv12"):
            backends.append(EncoderInfo(
                backend=EncoderBackend.QSV,
                video_encoder="h264_qsv",
                label="Intel QuickSync (GPU)",
                is_hardware=True
            ))
            
        # 3. Always include CPU
        backends.append(EncoderInfo(
            backend=EncoderBackend.CPU,
            video_encoder="libx264",
            label="Standard H.264 (CPU)",
            is_hardware=False
        ))
        
        return backends

    def detect_best_encoder(self, force: str | None = None) -> EncoderInfo:
        """Pick the best available encoder, or force a specific one."""
        available = self.get_available_backends()
        
        if force:
            # Check if force string matches an encoder name
            for info in available:
                if info.video_encoder == force:
                    return info
            # If not found among validated backends, try raw check
            if self._test_encoder(force):
                return EncoderInfo(
                    backend=EncoderBackend.CPU, # Fallback category
                    video_encoder=force,
                    label=f"Forced: {force}",
                    is_hardware="nvenc" in force or "qsv" in force or "amf" in force
                )
            raise GPUInitError(f"Forced encoder '{force}' is not available or failed initialization.")

        # Default priority: NVENC > QSV > CPU
        for b in [EncoderBackend.NVENC, EncoderBackend.QSV]:
            for info in available:
                if info.backend == b:
                    return info
        
        return [i for i in available if i.backend == EncoderBackend.CPU][0]

    def _test_encoder(self, codec: str, pix_fmt: str = "yuv420p") -> bool:
        """Run a minimal FFmpeg job to verify the encoder actually works.
        Uses 256x256 resolution for compatibility with modern GPUs.
        """
        cmd = [
            self._ffmpeg,
            "-hide_banner", "-loglevel", "error",
            "-f", "lavfi",
            "-i", "color=black:s=256x256:r=1",
            "-vframes", "1",
            "-c:v", codec,
            "-pix_fmt", pix_fmt,
            "-f", "null",
            "-",
        ]
        try:
            return subprocess.run(cmd, capture_output=True).returncode == 0
        except Exception:
            return False
