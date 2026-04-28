import time
from pathlib import Path
from typing import Optional, List

from backend.core.engine import FFmpegEngine
from backend.core.exceptions import ConversionError, DiskFullError
from backend.models.job import Job, JobStatus
from backend.models.hardware import EncoderInfo
from backend.presets import Preset
from backend.utils.logger import SynLogger

class ConverterService:
    """High-level service for orchestrating video conversions."""

    def __init__(self, engine: FFmpegEngine, logger: SynLogger):
        self.engine = engine
        self.logger = logger

    def process_job(
        self, 
        job: Job, 
        preset: Preset, 
        encoder: EncoderInfo,
        skip_existing: bool = True
    ) -> bool:
        """Process a single conversion job."""
        start_time = time.monotonic()
        
        # 1. Skip if exists
        if skip_existing and Path(job.output).exists():
            self.logger.info(f"Skipping existing file: {Path(job.output).name}")
            return True

        # 2. Build arguments
        args = self._build_args(job, preset, encoder)
        
        # 3. Run Engine
        try:
            self.logger.info(f"Using encoder: {encoder.video_encoder}")
            success = self.engine.run(args)
            
            if success:
                self.logger.file_success(
                    job.source, job.output, preset.name, 
                    encoder.video_encoder, start_time
                )
                return True
            else:
                self.logger.file_failed(
                    job.source, job.output, preset.name,
                    encoder.video_encoder, start_time, "FFmpeg returned non-zero"
                )
                return False
                
        except DiskFullError as exc:
            self.logger.error(str(exc))
            raise
        except Exception as exc:
            self.logger.file_failed(
                job.source, job.output, preset.name,
                encoder.video_encoder, start_time, str(exc)
            )
            return False

    def _build_args(self, job: Job, preset: Preset, encoder: EncoderInfo) -> List[str]:
        """Build FFmpeg command line arguments based on preset and encoder."""
        args = ["-hide_banner", "-y", "-i", job.source]
        
        # Video settings
        args += ["-c:v", encoder.video_encoder]
        args += ["-vf", f"scale={preset.width}:{preset.height}"]
        
        if encoder.is_hardware:
            args += ["-b:v", preset.gpu_bitrate]
        else:
            args += ["-crf", str(preset.cpu_crf), "-preset", "veryfast"]
            
        # Audio settings (passthrough for speed)
        args += ["-c:a", "copy"]
        
        args.append(job.output)
        return args
