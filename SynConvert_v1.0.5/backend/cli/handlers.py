import sys
import json
import argparse
from pathlib import Path
from dataclasses import asdict

from backend.services.config_service import ConfigService
from backend.services.hardware_service import HardwareService
from backend.services.scanner_service import ScannerService
from backend.services.naming_service import NamingService
from backend.services.queue_service import QueueService
from backend.services.converter_service import ConverterService
from backend.core.engine import FFmpegEngine
from backend.core.exceptions import SynConvertError
from backend.utils.logger import SynLogger
from backend.presets import get_preset, list_presets

from backend.models.job import Job, JobStatus

def handle_presets(_args: argparse.Namespace) -> int:
    print("\nAvailable presets:\n")
    for p in list_presets():
        print(f"  {p.name:<16}  {p.label}")
    return 0

def handle_config(args: argparse.Namespace) -> int:
    svc = ConfigService()
    if args.get:
        print(json.dumps(asdict(svc.load()), indent=2))
    elif args.set:
        svc.update_from_json(args.set)
        print("Configuration updated.")
    return 0

def handle_encoders(_args: argparse.Namespace) -> int:
    svc = HardwareService()
    backends = svc.get_available_backends()
    output = []
    for b in backends:
        d = asdict(b)
        d["backend"] = b.backend.name
        output.append(d)
    print(json.dumps(output, indent=2))
    return 0

def handle_scan(args: argparse.Namespace) -> int:
    cfg = ConfigService().load()
    output_dir = args.output or cfg.output_dir
    
    scanner = ScannerService()
    naming = NamingService(template=cfg.naming_template)
    
    results = scanner.scan(args.input, output_dir=output_dir)
    proposals = naming.build_proposals(results, Path(output_dir))
    
    if args.json:
        out = [{
            "source": str(p.scan_result.source_path),
            "relative": str(p.scan_result.relative_path),
            "output_filename": p.output_filename,
            "season": p.season,
            "episode": p.episode,
            "title": p.title
        } for p in proposals]
        print(json.dumps(out, indent=2))
    else:
        print(f"Found {len(results)} files.")
    return 0

def handle_status(args: argparse.Namespace) -> int:
    cfg = ConfigService().load()
    q_file = args.queue or cfg.queue_file
    svc = QueueService(q_file)
    
    if args.json:
        jobs = [asdict(j) for j in svc.get_all()]
        # Convert Enum to string
        for j in jobs: j["status"] = j["status"].value
        print(json.dumps(jobs, indent=2))
    else:
        summary = svc.get_summary()
        print(f"Queue Status ({q_file}):")
        for k, v in summary.items():
            print(f"  {k:12}: {v}")
    return 0

def handle_queue(args: argparse.Namespace) -> int:
    cfg = ConfigService().load()
    svc = QueueService(cfg.queue_file)
    
    if args.clear_done:
        n = svc.clear_completed()
        print(f"Cleared {n} jobs.")
    elif args.clear_all:
        n = svc.clear_all_history()
        print(f"Cleared {n} jobs from history.")
    elif args.reset_failed:
        n = svc.reset_failed()
        print(f"Reset {n} jobs.")
    elif args.remove:
        ids = [i.strip() for i in args.remove.split(",") if i.strip()]
        n = svc.remove_by_ids(ids)
        print(f"Removed {n} job(s).")
    elif args.add:
        out_dir = Path(args.to or cfg.output_dir)
        preset_name = cfg.default_preset
        count = 0
        for f in args.add:
            src = Path(f)
            if src.exists() and src.is_file():
                # Ensure output directory exists
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{src.stem}_converted.mp4"
                svc.add(source=str(src.absolute()), output=str(out_path.absolute()), preset=preset_name)
                count += 1
        print(f"Added {count} file(s) to queue.")
    elif args.resume:
        return _process_queue(svc, cfg)
    return 0


def handle_convert(args: argparse.Namespace) -> int:
    cfg = ConfigService().load()
    output_dir = Path(args.output or cfg.output_dir)
    preset_name = args.preset or cfg.default_preset
    template = args.template or cfg.naming_template
    
    # 1. Hardware
    hw_svc = HardwareService()
    encoder = hw_svc.detect_best_encoder(force=args.encoder or cfg.force_encoder)
    
    # 2. Scan & Name
    scanner = ScannerService()
    naming = NamingService(template=template)
    
    results = scanner.scan(args.input, output_dir=output_dir)
    proposals = naming.build_proposals(results, output_dir)
    
    # 3. Filter active
    active = [p for p in proposals if not p.skipped]
    if not active:
        print("Nothing to convert.")
        return 0
        
    # 4. Queue
    q_svc = QueueService(cfg.queue_file)
    for p in active:
        q_svc.add(
            source=str(p.scan_result.source_path),
            output=str(p.output_path),
            preset=preset_name
        )
        
    # 5. Process
    return _process_queue(q_svc, cfg)

def _process_queue(q_svc: QueueService, cfg) -> int:
    import sys
    import threading
    import os
    
    hw_svc = HardwareService()
    encoder = hw_svc.detect_best_encoder(force=cfg.force_encoder)
    
    logger = SynLogger(cfg.log_dir)
    engine = FFmpegEngine(hw_svc._ffmpeg)
    
    # Watchdog to kill FFmpeg if parent (Flutter) dies and closes stdin
    def _watchdog():
        try:
            sys.stdin.read()
        except Exception:
            pass
        logger.error("Parent process died! Terminating FFmpeg...")
        engine.stop()
        os._exit(1)
        
    if not sys.stdin.isatty():
        threading.Thread(target=_watchdog, daemon=True).start()

    converter = ConverterService(engine, logger)
    
    from concurrent.futures import ThreadPoolExecutor
    
    pending = q_svc.get_pending()
    if not pending:
        print("No pending jobs.")
        return 0
        
    logger.session_start(len(pending), encoder.label)
    
    # We use a ThreadPoolExecutor to run multiple FFmpeg processes in parallel.
    # FFmpeg is a subprocess, so threads are perfect for waiting on I/O without blocking.
    max_workers = max(1, min(cfg.parallel_jobs, 4)) # Limit to 4 to avoid system choke
    
    def worker(job_tuple):
        index, job = job_tuple
        job_id = job.id
        logger.file_start(index, len(pending), job.source, job_id=job_id)
        q_svc.update_status(job_id, JobStatus.IN_PROGRESS)
        
        try:
            preset = get_preset(job.preset)
            # Create a dedicated engine per thread to avoid state conflicts
            thread_engine = FFmpegEngine(hw_svc._ffmpeg)
            thread_converter = ConverterService(thread_engine, logger)
            
            success = thread_converter.process_job(
                job, preset, encoder, 
                skip_existing=cfg.skip_existing,
                max_retries=cfg.max_retries
            )
            
            if success:
                q_svc.update_status(job_id, JobStatus.DONE)
            else:
                last_err = "FFmpeg failed (check logs for details)"
                q_svc.update_status(job_id, JobStatus.FAILED, error=last_err)
        except Exception as exc:
            q_svc.update_status(job_id, JobStatus.FAILED, error=str(exc))
            logger.error(f"Worker failed: {exc}", job_id=job_id)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(worker, enumerate(pending, start=1))
            
    logger.session_end(show_notification=cfg.show_notifications)
    return 0
