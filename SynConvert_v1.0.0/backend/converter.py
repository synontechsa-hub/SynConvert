"""FFmpeg command builder and executor for SynConvert.

Responsibilities:
  - Build FFmpeg command from preset + encoder info
  - Preserve ALL audio and subtitle streams (stream copy where possible)
  - Execute FFmpeg with stdout/stderr capture and real-time progress parsing
  - Retry once on failure
  - Detect disk-full condition
  - Mirror output directory structure
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import static_ffmpeg

from backend.hardware import EncoderInfo, EncoderBackend
from backend.logger import SynLogger
from backend.naming import NameProposal
from backend.presets import Preset


# ---------------------------------------------------------------------------
# FFmpeg binary resolution
# ---------------------------------------------------------------------------

def _get_ffmpeg() -> str:
    ffmpeg, _ = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
    return str(ffmpeg)


# ---------------------------------------------------------------------------
# Command builder
# ---------------------------------------------------------------------------

def build_ffmpeg_command(
    source: Path,
    output: Path,
    preset: Preset,
    encoder: EncoderInfo,
) -> list[str]:
    """Build the FFmpeg argument list for a single conversion job.

    Stream preservation rules:
      - Video: re-encoded to target codec / resolution
      - Audio: ALL tracks preserved; re-encoded to AAC if needed
      - Subtitles: ALL tracks stream-copied (no burn-in)
      - Chapters: passed through if present

    Args:
        source:  Absolute path to the source file.
        output:  Absolute path to the output file.
        preset:  Encoding preset (resolution, quality settings).
        encoder: Detected encoder (GPU or CPU).

    Returns:
        List of strings suitable for subprocess.run / Popen.
    """
    ffmpeg = _get_ffmpeg()

    # Scale filter: fit within target dimensions while preserving aspect ratio.
    # The 'min(1,...)' guards prevent upscaling.
    scale_filter = (
        f"scale=w='min({preset.width},iw)':h='min({preset.height},ih)':"
        f"force_original_aspect_ratio=decrease,"
        f"pad={preset.width}:{preset.height}:(ow-iw)/2:(oh-ih)/2:black"
    )

    cmd = [ffmpeg, "-y",  # -y = overwrite output without prompting
           "-i", str(source)]

    # --- Video stream ---
    cmd += ["-map", "0:v:0?"]  # Map first video stream (if present)

    if encoder.backend == EncoderBackend.NVENC:
        cmd += [
            "-c:v", encoder.video_encoder,
            "-vf", scale_filter,
            "-b:v", preset.gpu_bitrate,
            "-maxrate", preset.gpu_maxrate,
            "-bufsize", preset.gpu_bufsize,
            "-preset", "p4",  # NVENC balanced preset
            "-rc", "vbr",
            "-cq", "23",
        ]
    elif encoder.backend == EncoderBackend.QSV:
        cmd += [
            "-c:v", encoder.video_encoder,
            "-vf", scale_filter,
            "-b:v", preset.gpu_bitrate,
            "-maxrate", preset.gpu_maxrate,
            "-bufsize", preset.gpu_bufsize,
            "-preset", "fast",
        ]
    else:  # CPU (libx264)
        cmd += [
            "-c:v", encoder.video_encoder,
            "-vf", scale_filter,
            "-crf", str(preset.cpu_crf),
            "-preset", preset.cpu_preset,
        ]

    # --- Audio streams: map ALL, re-encode to AAC ---
    cmd += ["-map", "0:a"]          # Map every audio track
    cmd += ["-c:a", preset.audio_codec]
    cmd += ["-b:a", preset.audio_bitrate]

    # --- Subtitle streams: map ALL, stream copy ---
    cmd += ["-map", "0:s?"]         # '?' = don't fail if no subtitle streams
    cmd += ["-c:s", "copy"]

    # --- Chapters: pass through ---
    cmd += ["-map_chapters", "0"]

    # --- Output format ---
    cmd += ["-f", "matroska"]
    cmd += [str(output)]

    return cmd


# ---------------------------------------------------------------------------
# FFmpeg executor
# ---------------------------------------------------------------------------

_DISK_FULL_PATTERNS = [
    re.compile(r"no space left", re.IGNORECASE),
    re.compile(r"disk full", re.IGNORECASE),
    re.compile(r"errno=28", re.IGNORECASE),
]

_PROGRESS_RE = re.compile(r"time=\s*(\d{2}):(\d{2}):(\d{2})\.\d+")


def _parse_time_seconds(m: re.Match[str]) -> float:
    h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return h * 3600 + mi * 60 + s


def _is_disk_full(stderr: str) -> bool:
    return any(p.search(stderr) for p in _DISK_FULL_PATTERNS)


def run_ffmpeg(
    cmd: list[str],
    log_prefix: str = "",
) -> tuple[bool, str]:
    """Execute an FFmpeg command and return (success, stderr_output).

    Streams stderr in real-time so progress can be captured.
    """
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stderr_lines: list[str] = []
        assert proc.stderr is not None

        for line in proc.stderr:
            stderr_lines.append(line)
            # Optional: surface progress to console (time= parsing)
            m = _PROGRESS_RE.search(line)
            if m:
                t = _parse_time_seconds(m)
                print(f"\r        ⏱  {_format_time(t)}", end="", flush=True)

        proc.wait()
        print()  # newline after progress

        stderr_output = "".join(stderr_lines)
        return proc.returncode == 0, stderr_output

    except FileNotFoundError:
        return False, "FFmpeg binary not found."
    except OSError as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# High-level conversion runner
# ---------------------------------------------------------------------------

class DiskFullError(RuntimeError):
    """Raised when FFmpeg reports no disk space remaining."""


def convert_file(
    proposal: NameProposal,
    preset: Preset,
    encoder: EncoderInfo,
    logger: SynLogger,
    max_retries: int = 1,
    skip_existing: bool = True,
) -> bool:
    """Convert a single file according to a NameProposal.

    Args:
        proposal:     Source + output path information.
        preset:       Encoding preset.
        encoder:      Selected FFmpeg encoder.
        logger:       Logger instance for progress/error output.
        max_retries:  Number of retry attempts on failure.
        skip_existing: Skip if output file already exists.

    Returns:
        True if conversion succeeded or was skipped, False if it failed.

    Raises:
        DiskFullError: If FFmpeg reports no space left on device.
    """
    source = proposal.scan_result.source_path
    output = proposal.output_path

    # Skip check
    if skip_existing and output.exists():
        logger.file_skipped(str(source), reason="output exists")
        return True

    # Ensure output directory exists
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = build_ffmpeg_command(source, output, preset, encoder)

    attempts = 0
    start = _time.monotonic()  # Initialized outside to avoid undefined-risk

    while attempts <= max_retries:
        if attempts > 0:
            logger.retry(str(source), attempts)

        success, stderr = run_ffmpeg(cmd)

        if _is_disk_full(stderr):
            # Clean up partial output
            if output.exists():
                output.unlink()
            raise DiskFullError(
                "Disk full — conversion queue halted. Free up space and re-run."
            )

        if success:
            logger.file_success(
                source=str(source),
                output=str(output),
                preset=preset.name,
                encoder=encoder.label,
                start_time=start,
            )
            return True

        attempts += 1

    # All attempts exhausted
    logger.file_failed(
        source=str(source),
        output=str(output),
        preset=preset.name,
        encoder=encoder.label,
        start_time=start,  # type: ignore[possibly-undefined]
        error=stderr[-300:].strip() if stderr else "Unknown FFmpeg error",
    )
    # Remove partial output on failure
    if output.exists():
        output.unlink()
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
