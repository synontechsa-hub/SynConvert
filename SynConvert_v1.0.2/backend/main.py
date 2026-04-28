"""CLI entry point for SynConvert.

Commands:
    synconvert scan     --input <dir> [--output <dir>] [--json]
    synconvert convert  --input <dir> --output <dir> [--preset <name>] [--encoder <enc>]
                        [--no-review] [--template <fmt>]
    synconvert status   [--queue <file>] [--json]
    synconvert presets

Usage examples:
    python -m backend.main scan --input "D:/Anime/Failure Frame"
    python -m backend.main convert --input "D:/Anime/Failure Frame" --output "D:/Mobile/Failure Frame"
    python -m backend.main convert --input "D:/Anime" --output "D:/Mobile" --preset 480p_saver --no-review
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Force UTF-8 output so Flutter's utf8.decoder never sees unexpected bytes,
# regardless of the Windows system locale (which defaults to cp1252/cp850).
# reconfigure() is available on Python 3.7+ and is the recommended approach.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from backend.config import load_config, save_config, DEFAULT_CONFIG_FILE
from backend.converter import DiskFullError, convert_file
from backend.hardware import detect_encoder
from backend.logger import SynLogger
from backend.naming import build_proposals, review_proposals, DEFAULT_TEMPLATE
from backend.presets import get_preset, list_presets
from backend.queue import JobQueue
from backend.scanner import scan_directory


# ---------------------------------------------------------------------------
# Sub-command: scan
# ---------------------------------------------------------------------------

def cmd_scan(args: argparse.Namespace) -> int:
    """Scan an input directory and list discovered files."""
    cfg = load_config()
    output_dir = Path(args.output) if args.output else Path(cfg.output_dir)
    preset_name = cfg.default_preset
    template = cfg.naming_template

    try:
        preset = get_preset(preset_name)
        results = scan_directory(args.input, output_dir=output_dir)
        proposals = build_proposals(
            results,
            output_root=output_dir,
            template=template,
            container=preset.container,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        import json as _json
        output = [
            {
                "source": str(p.scan_result.source_path),
                "relative": str(p.scan_result.relative_path),
                "output_filename": p.output_filename,
                "season": p.season,
                "episode": p.episode,
                "title": p.title,
            }
            for p in proposals
        ]
        print(_json.dumps(output, indent=2))
        return 0

    if not results:
        print("No supported video files found.")
        return 0

    print(f"\nFound {len(results)} file(s) in: {args.input}\n")
    for r in results:
        print(f"  {r.relative_path}")

    return 0


# ---------------------------------------------------------------------------
# Sub-command: convert
# ---------------------------------------------------------------------------

def cmd_convert(args: argparse.Namespace) -> int:
    """Full scan → name → (review) → convert pipeline."""
    cfg = load_config()

    output_dir = Path(args.output) if args.output else Path(cfg.output_dir)
    preset_name = args.preset or cfg.default_preset
    template = args.template or cfg.naming_template
    review = not args.no_review and cfg.review_before_convert

    # --- Load preset ---
    try:
        preset = get_preset(preset_name)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # --- Detect encoder ---
    print("Detecting hardware encoder…")
    encoder = detect_encoder(force=args.encoder or cfg.force_encoder)
    print(f"  Selected: {encoder.label}")

    # --- Scan ---
    print(f"\nScanning: {args.input}")
    try:
        results = scan_directory(args.input, output_dir=output_dir)
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not results:
        print("No supported video files found.")
        return 0

    print(f"  Found {len(results)} file(s).")

    # --- Build naming proposals ---
    proposals = build_proposals(
        results,
        output_root=output_dir,
        template=template,
        container=preset.container,
    )

    # --- Review mode ---
    if review:
        proposals = review_proposals(proposals)

    active = [p for p in proposals if not p.skipped]
    if not active:
        print("Nothing to convert.")
        return 0

    # --- Build persistent queue ---
    queue = JobQueue(cfg.queue_file)
    for p in active:
        queue.add(
            source=str(p.scan_result.source_path),
            output=str(p.output_path),
            preset=preset.name,
        )

    # --- Setup logger ---
    logger = SynLogger(cfg.log_dir)
    logger.session_start(total_files=len(active), encoder_label=encoder.label)

    # --- Convert ---
    pending = queue.pending()
    total = len(pending)
    failed_count = 0

    for i, job in enumerate(pending, start=1):
        proposal = next(
            (p for p in active if str(p.scan_result.source_path) == job.source),
            None,
        )
        if proposal is None:
            continue

        logger.file_start(i, total, job.source)
        job.mark_in_progress()
        queue.update(job)

        try:
            ok = convert_file(
                proposal=proposal,
                preset=preset,
                encoder=encoder,
                logger=logger,
                max_retries=cfg.max_retries,
                skip_existing=cfg.skip_existing,
            )
        except DiskFullError as exc:
            logger.error(str(exc))
            job.mark_failed(str(exc))
            queue.update(job)
            logger.session_end()
            return 1

        if ok:
            job.mark_done()
        else:
            job.mark_failed("FFmpeg conversion failed")
            failed_count += 1
        queue.update(job)

    logger.session_end()
    return 1 if failed_count else 0


# ---------------------------------------------------------------------------
# Sub-command: status
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> int:
    """Show current queue status."""
    cfg = load_config()
    queue_file = Path(args.queue) if args.queue else Path(cfg.queue_file)

    if not queue_file.exists():
        print("No queue file found. Run 'convert' first.")
        return 0

    queue = JobQueue(queue_file)
    jobs = queue.all_jobs()

    if args.json:
        import json
        output = [
            {
                "id": j.id,
                "source": j.source,
                "output": j.output,
                "preset": j.preset,
                "status": j.status.value,
                "error": j.error,
                "attempts": j.attempts
            }
            for j in jobs
        ]
        print(json.dumps(output, indent=2))
        return 0

    summary = queue.summary()
    total = sum(summary.values())

    print(f"\nQueue: {queue_file}")
    print(f"  Total     : {total}")
    for status, count in summary.items():
        if count:
            print(f"  {status:<12}: {count}")

    failed_jobs = [j for j in jobs if j.status.value == "failed"]
    if failed_jobs:
        print("\nFailed jobs:")
        for j in failed_jobs:
            print(f"  [{j.id[:8]}] {Path(j.source).name}")
            if j.error:
                print(f"             {j.error[:80]}")

    return 0


# ---------------------------------------------------------------------------
# Sub-command: presets
# ---------------------------------------------------------------------------

def cmd_presets(_args: argparse.Namespace) -> int:
    """List all available presets."""
    print("\nAvailable presets:\n")
    for p in list_presets():
        print(f"  {p.name:<16}  {p.label}")
        print(f"  {'':16}  {p.description}")
        print(f"  {'':16}  Resolution: {p.width}×{p.height}")
        print(f"  {'':16}  CPU CRF: {p.cpu_crf}  |  GPU bitrate: {p.gpu_bitrate}")
        print()
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="synconvert",
        description="SynConvert — Offline batch video transcoder",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- scan --
    p_scan = sub.add_parser("scan", help="Scan a directory and list video files")
    p_scan.add_argument("--input", "-i", required=True, help="Input directory to scan")
    p_scan.add_argument("--output", "-o", help="Output directory (for safety check only)")
    p_scan.add_argument("--json", action="store_true", help="Output results as JSON")

    # -- convert --
    p_conv = sub.add_parser("convert", help="Convert video files")
    p_conv.add_argument("--input",    "-i", required=True, help="Input directory")
    p_conv.add_argument("--output",   "-o", help="Output root directory")
    p_conv.add_argument("--preset",   "-p", help="Preset name (720p_mobile / 480p_saver)")
    p_conv.add_argument("--encoder",  "-e", help="Force a specific FFmpeg encoder (e.g. libx264)")
    p_conv.add_argument("--template", "-t", help="Custom naming template, e.g. 'S{S:02d}E{E:02d}'")
    p_conv.add_argument("--no-review", action="store_true", help="Skip review mode and convert immediately")

    # -- status --
    p_stat = sub.add_parser("status", help="Show queue status")
    p_stat.add_argument("--queue", "-q", help="Path to queue file (default: from config)")
    p_stat.add_argument("--json", action="store_true", help="Output status as JSON")

    # -- presets --
    sub.add_parser("presets", help="List available presets")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "scan":    cmd_scan,
        "convert": cmd_convert,
        "status":  cmd_status,
        "presets": cmd_presets,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    sys.exit(handler(args))


if __name__ == "__main__":
    main()
