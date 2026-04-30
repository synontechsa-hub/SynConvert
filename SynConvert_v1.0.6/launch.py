import subprocess
import sys
import os
from pathlib import Path


def main():
    root = Path(__file__).parent.resolve()
    frontend_dir = root / "frontend"
    venv_python = root / ".venv" / "Scripts" / "python.exe"

    print("🚀 SynConvert v1.0.6 Launcher")
    print("━" * 30)

    # 1. Check Environment
    if not venv_python.exists():
        print("❌ Error: Virtual environment (.venv) not found.")
        print("   Please run 'python -m venv .venv' and install dependencies.")
        sys.exit(1)

    # 2. Check Flutter
    flutter_cmd = "flutter.bat" if os.name == "nt" else "flutter"
    try:
        subprocess.run(
            [flutter_cmd, "--version"],
            capture_output=True,
            check=True,
            shell=(os.name == "nt"),
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: Flutter SDK not found in PATH.")
        print("   If you have Flutter installed, make sure it's added to your System Environment Variables.")
        sys.exit(1)

    # 3. Verify backend is reachable before launching UI
    print("🔍 Checking backend...")
    try:
        result = subprocess.run(
            [str(venv_python), "-m", "backend.main", "--help"],
            cwd=str(root),
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            print("✅ Environment: OK")
            print("✅ Backend: Ready")
        else:
            print("⚠️  Backend check failed — module may be missing.")
            print("   Try: pip install -e .")
    except Exception as e:
        print(f"⚠️  Backend check error: {e}")

    print("📡 Launching UI...")
    print("━" * 30)

    # 4. Launch Flutter (Windows Desktop)
    # FIX: Pass SYNCONVERT_ROOT as an environment variable so backend_bridge.dart
    # can resolve the correct Python path without guessing from the executable location.
    env = os.environ.copy()
    env["SYNCONVERT_ROOT"] = str(root)

    try:
        subprocess.run(
            ["flutter", "run", "-d", "windows"],
            cwd=str(frontend_dir),
            shell=True,
            env=env,
        )
    except KeyboardInterrupt:
        print("\n👋 Launcher closed.")


if __name__ == "__main__":
    main()
