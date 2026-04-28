import subprocess
import static_ffmpeg.run

def _ffmpeg_bin() -> str:
    ffmpeg, _ = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
    return str(ffmpeg)

def probe_nvenc():
    ffmpeg = _ffmpeg_bin()
    cmd = [
        ffmpeg,
        "-f", "lavfi",
        "-i", "color=black:s=256x256:r=1",
        "-vframes", "1",
        "-c:v", "h264_nvenc",
        "-pix_fmt", "yuv420p",
        "-f", "null",
        "-",
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    print(f"STDOUT: {result.stdout}")
    print(f"STDERR: {result.stderr}")

if __name__ == "__main__":
    probe_nvenc()
