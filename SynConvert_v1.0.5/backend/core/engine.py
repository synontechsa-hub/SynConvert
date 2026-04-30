import subprocess
import re
import os
import signal
from typing import Callable, Optional
from backend.core.exceptions import FFmpegError, DiskFullError

class FFmpegEngine:
    """Low-level wrapper for FFmpeg process management."""

    def __init__(self, ffmpeg_path: str):
        self.ffmpeg_path = ffmpeg_path
        self._process: Optional[subprocess.Popen] = None

    def run(
        self, 
        args: list[str], 
        on_progress: Optional[Callable[[float], None]] = None
    ) -> bool:
        """Run FFmpeg with provided arguments and parse progress."""
        cmd = [self.ffmpeg_path] + args
        
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            duration = 1.0
            for line in self._process.stdout:
                # Parse duration
                if "Duration:" in line:
                    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", line)
                    if m:
                        h, m_val, s = m.groups()
                        duration = int(h) * 3600 + int(m_val) * 60 + float(s)

                # Parse time
                if "time=" in line:
                    m = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                    if m and on_progress:
                        h, m_val, s = m.groups()
                        current_time = int(h) * 3600 + int(m_val) * 60 + float(s)
                        progress = min(100.0, (current_time / duration) * 100)
                        on_progress(progress)

                # Check for specific errors
                if "No space left on device" in line:
                    self.stop()
                    raise DiskFullError("Target disk is full.")

            self._process.wait()
            return self._process.returncode == 0

        except Exception as exc:
            self.stop()
            if isinstance(exc, DiskFullError): raise
            raise FFmpegError(f"FFmpeg execution failed: {exc}")
        finally:
            self._process = None

    def stop(self):
        """Forcefully terminate the running FFmpeg process."""
        if self._process:
            try:
                if os.name == "nt":
                    # Windows: kill process tree to ensure ffmpeg.exe dies
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self._process.pid)], 
                                 capture_output=True)
                else:
                    os.kill(self._process.pid, signal.SIGKILL)
            except Exception:
                pass
            self._process = None
