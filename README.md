# SynConvert

![SynConvert Logo](https://github.com/synontechsa-hub/SynConvert/blob/main/assets/synconvert-logo.png)

**Offline batch video transcoder** — Fast. Compatible. Reliable.

Built for anime and TV show collectors who want clean, mobile-optimized MP4/MKV files with smart naming, hardware acceleration, and a smooth desktop experience.

---

## ✨ Features

- **Hardware Acceleration** — Automatic detection of NVIDIA NVENC and Intel Quick Sync, with CPU fallback
- **Smart Naming** — Automatically detects season/episode and generates clean filenames (`S01E03 - Title.mkv`)
- **Review Mode** — Preview and edit proposed filenames before conversion
- **Persistent Queue** — Save your queue and resume later
- **Parallel Processing** — Convert multiple files simultaneously (configurable)
- **Full Stream Preservation** — Audio tracks, subtitles, and chapters are kept
- **Beautiful Flutter Desktop UI** — Modern, responsive interface (Windows focus)
- **Themes** — New in v1.0.6
- **Configurable Presets** — Optimized for mobile/tablet storage vs quality

---

## 📊 Available Presets

| Preset | Resolution | Target Use Case | Quality / Size |
|---|---|---|---|
| `720p_mobile` | 1280×720 | Phones & Tablets (Recommended) | Balanced |
| `480p_saver` | 854×480 | Maximum storage saving | Smallest |
| `1080p_high` | 1920×1080 | Best quality | Largest |

*(More presets available via CLI)*

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repo
git clone https://github.com/synontechsa-hub/SynConvert.git
cd SynConvert

# Install Python backend
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -e .

# Launch the app
python launch.py
```

### 2. Basic Usage (CLI)

```bash
# Scan a folder
synconvert scan --input "F:\Anime\Show Name"

# Convert with default settings
synconvert convert --input "F:\Anime\Show Name" --output "F:\Converted"

# Check queue status
synconvert status
```

---

## 🖥️ Screenshots

*(Add your screenshots here — especially the Wizard / New Job page and Queue page)*

| New Job Wizard | Queue Management | Settings Panel |
|---|---|---|
| *(screenshot)* | *(screenshot)* | *(screenshot)* |

---

## 📋 What's New in v1.0.6

- Themes support added to the Flutter UI
- Fixed hardcoded numbers on the Dashboard
- Various small bug fixes and stability improvements

---

## 🗂️ Project Structure

```
SynConvert/
├── backend/     # Python core (FFmpeg engine, queue, naming, hardware detection)
├── frontend/    # Flutter desktop application
└── launch.py    # Convenient launcher for the full app
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + FFmpeg (with static-ffmpeg) |
| Frontend | Flutter (Desktop) |
| UI State | Provider |
| Hardware | NVENC, Quick Sync, libx264 fallback |

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

*Made with ❤️ for offline media enthusiasts*
