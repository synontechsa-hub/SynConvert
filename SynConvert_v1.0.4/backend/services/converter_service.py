import time
from pathlib import Path
from typing import List

from backend.core.engine import FFmpegEngine
from backend.core.exceptions import ConversionError, DiskFullError
from backend.models.job import Job, JobStatus
from backend.models.hardware import EncoderInfo, EncoderBackend
from backend.presets import Preset
from backend.utils.logger import SynLogger


class ConverterService:
    """High-level service for orchestrating video conversions.
    
    Uses FFmpegEngine for subprocess management and builds full FFmpeg
    commands with proper stream mapping, subtitle/chapter passthrough,
    and no-upscale guards.
    """

    def __init__(self, engine: FFmpegEngine, logger: SynLogger):
        self.engine = engine
        self.logger = logger

    def process_job(
        self,
        job: Job,
        preset: Preset,
        encoder: EncoderInfo,
        skip_existing: bool = True,
        max_retries: int = 1,
    ) -> bool:
        """Process a single conversion job with retry support."""
        start_time = time.monotonic()
        job_id = job.id

        # 1. Skip if output exists
        output_path = Path(job.output)
        if skip_existing and output_path.exists():
            self.logger.info(f"Skipping (exists): {output_path.name}", job_id=job_id)
            return True

        # 2. Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 3. Build command
        args = self._build_ffmpeg_args(job, preset, encoder)

        # 4. Run with retries
        attempts = 0
        while attempts <= max_retries:
            if attempts > 0:
                self.logger.info(f"Retrying ({attempts}/{max_retries})...", job_id=job_id)

            try:
                def progress_cb(pct: float):
                    print(f"[{job_id}] ⏱ Progress: {pct:.1f}%")

                success = self.engine.run(args, on_progress=progress_cb)

                if success:
                    self.logger.file_success(
                        job.source, job.output, preset.name,
                        encoder.video_encoder, start_time, job_id=job_id
                    )
                    return True

            except DiskFullError:
                # Clean up partial output
                if output_path.exists():
                    output_path.unlink()
                raise

            except Exception as exc:
                self.logger.error(f"Engine error: {exc}", job_id=job_id)

            attempts += 1

        # All attempts exhausted
        self.logger.file_failed(
            job.source, job.output, preset.name,
            encoder.video_encoder, start_time,
            "FFmpeg conversion failed after all retries",
            job_id=job_id
        )
        # Remove partial output on failure
        if output_path.exists():
            output_path.unlink()
        return False

    def _build_ffmpeg_args(
        self, job: Job, preset: Preset, encoder: EncoderInfo
    ) -> List[str]:
        """Build full FFmpeg arguments with proper stream mapping.
        
        Rules:
          - Video: re-encoded, downscaled only (never upscaled)
          - Audio: ALL tracks preserved, re-encoded to AAC
          - Subtitles: ALL tracks stream-copied
          - Chapters: passed through
        """
        # Scale filter: fit within target while preserving aspect ratio.
        # force_divisible_by=2 is CRITICAL for NVENC/QSV hardware encoders.
        scale = (
            f"scale=w='min({preset.width},iw)':h='min({preset.height},ih)':"
            f"force_original_aspect_ratio=decrease,format=yuv420p"
        )

        # --- Input & Hardware Acceleration ---
        # Note: -hwaccel MUST come before -i
        hw_args = []
        if encoder.backend == EncoderBackend.NVENC:
            # We use hybrid mode (HW decode -> SW filters -> HW encode) 
            # to maintain compatibility with our complex scaling/padding filters.
            hw_args = ["-hwaccel", "cuda"]
        elif encoder.backend == EncoderBackend.QSV:
            hw_args = ["-hwaccel", "qsv"]

        args = ["-hide_banner", "-y"] + hw_args + ["-i", job.source]

        # --- Video stream ---
        args += ["-map", "0:v:0?"]  # First video stream (if present)

        if encoder.backend == EncoderBackend.NVENC:
            args += [
                "-c:v", encoder.video_encoder,
                "-vf", f"{scale},pad='ceil(iw/2)*2:ceil(ih/2)*2'",
                "-b:v", preset.gpu_bitrate,
                "-maxrate", preset.gpu_maxrate,
                "-bufsize", preset.gpu_bufsize,
                "-preset", "p4",
                "-rc", "vbr",
                "-cq", "23",
            ]
        elif encoder.backend == EncoderBackend.QSV:
            args += [
                "-c:v", encoder.video_encoder,
                "-vf", f"{scale},pad='ceil(iw/2)*2:ceil(ih/2)*2'",
                "-b:v", preset.gpu_bitrate,
                "-maxrate", preset.gpu_maxrate,
                "-bufsize", preset.gpu_bufsize,
                "-preset", "fast",
            ]
        else:  # CPU (libx264)
            args += [
                "-c:v", encoder.video_encoder,
                "-vf", scale,
                "-crf", str(preset.cpu_crf),
                "-preset", preset.cpu_preset,
            ]

        # --- Audio: map ALL tracks (if present), re-encode to AAC ---
        args += ["-map", "0:a?"]
        args += ["-c:a", preset.audio_codec]
        args += ["-b:a", preset.audio_bitrate]

        # --- Subtitles: map ALL tracks (if present), stream copy ---
        args += ["-map", "0:s?"]
        args += ["-c:s", "copy"]

        # --- Chapters: pass through ---
        args += ["-map_chapters", "0"]

        # --- Output format ---
        args += ["-f", "matroska"]
        args += [job.output]

        return args
