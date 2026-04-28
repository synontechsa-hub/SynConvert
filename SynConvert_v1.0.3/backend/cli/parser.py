import argparse

def build_parser() -> argparse.ArgumentParser:
    """Define the CLI structure for SynConvert."""
    parser = argparse.ArgumentParser(
        prog="synconvert",
        description="SynConvert — Offline batch video transcoder",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- config --
    p_config = sub.add_parser("config", help="Read or update global configuration")
    p_config.add_argument("--get", action="store_true", help="Get current config as JSON")
    p_config.add_argument("--set", help="Update config with a JSON string")

    # -- queue --
    p_queue = sub.add_parser("queue", help="Manage the job queue")
    p_queue.add_argument("--resume", action="store_true", help="Process pending jobs in the queue")
    p_queue.add_argument("--clear-done", action="store_true", help="Remove completed/skipped jobs")
    p_queue.add_argument("--reset-failed", action="store_true", help="Reset failed jobs to pending")

    # -- scan --
    p_scan = sub.add_parser("scan", help="Scan a directory and list video files")
    p_scan.add_argument("--input", "-i", required=True, help="Input directory to scan")
    p_scan.add_argument("--output", "-o", help="Output directory (for safety check only)")
    p_scan.add_argument("--json", action="store_true", help="Output results as JSON")

    # -- convert --
    p_conv = sub.add_parser("convert", help="Convert video files")
    p_conv.add_argument("--input",    "-i", required=True, help="Input directory")
    p_conv.add_argument("--output",   "-o", help="Output root directory")
    p_conv.add_argument("--preset",   "-p", help="Preset name")
    p_conv.add_argument("--encoder",  "-e", help="Force a specific FFmpeg encoder")
    p_conv.add_argument("--template", "-t", help="Custom naming template")
    p_conv.add_argument("--no-review", action="store_true", help="Skip review mode")

    # -- status --
    p_stat = sub.add_parser("status", help="Show queue status")
    p_stat.add_argument("--queue", "-q", help="Path to queue file")
    p_stat.add_argument("--json", action="store_true", help="Output status as JSON")

    # -- presets --
    sub.add_parser("presets", help="List available presets")

    # -- encoders --
    sub.add_parser("encoders", help="List available hardware backends")

    return parser
