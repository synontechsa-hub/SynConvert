import subprocess
import sys
import os
from pathlib import Path

def main():
    root = Path(__file__).parent.resolve()
    frontend_dir = root / "frontend"
    venv_python = root / ".venv" / "Scripts" / "python.exe"

    print("🚀 SynConvert v1.0.1 Launcher")
    print("━" * 30)

    # 1. Check Environment
    if not venv_python.exists():
        print("❌ Error: Virtual environment (.venv) not found.")
        print("   Please run 'python -m venv .venv' and install dependencies.")
        sys.exit(1)

    # 2. Check Flutter
    flutter_cmd = "flutter.bat" if os.name == "nt" else "flutter"
    try:
        # Use shell=True for Windows to resolve the .bat file correctly
        subprocess.run([flutter_cmd, "--version"], capture_output=True, check=True, shell=(os.name == "nt"))
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: Flutter SDK not found in PATH.")
        print("   If you have Flutter installed, make sure it's added to your System Environment Variables.")
        sys.exit(1)

    print("✅ Environment: OK")
    print("✅ Backend: Ready")
    print("📡 Launching UI...")
    print("━" * 30)

    # 3. Launch Flutter (Windows Desktop)
    try:
        # We run 'flutter run' from the frontend directory
        subprocess.run(
            ["flutter", "run", "-d", "windows"],
            cwd=frontend_dir,
            shell=True
        )
    except KeyboardInterrupt:
        print("\n👋 Launcher closed.")

if __name__ == "__main__":
    main()
