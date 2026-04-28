import sys
from backend.cli.parser import build_parser
from backend.cli import handlers

# Force UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def main():
    parser = build_parser()
    args = parser.parse_args()

    command_map = {
        "config":   handlers.handle_config,
        "encoders": handlers.handle_encoders,
        "scan":     handlers.handle_scan,
        "status":   handlers.handle_status,
        "queue":    handlers.handle_queue,
        "presets":  handlers.handle_presets,
    }

    handler = command_map.get(args.command)
    if not handler:
        parser.print_help()
        sys.exit(1)

    try:
        sys.exit(handler(args))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
