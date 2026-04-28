# SynConvert — Design Bible

## Overview

SynConvert is a lightweight, offline-first PC-based media transcoding tool designed to batch convert video files (primarily anime) into optimized formats for mobile playback.

It is not a streaming tool, not a media player, and not a cloud service. It is a **local video conversion pipeline** focused on speed, simplicity, and storage efficiency.

Codename: **SynConvert**

---

## Core Philosophy

* **Offline First**: No internet dependency. Ever.
* **Batch Over Manual**: Process folders, not single files.
* **Simplicity Over Features**: Fewer options, better defaults.
* **Performance Matters**: FFmpeg is the engine; Python is the conductor.
* **Deterministic Output**: Same input + preset = same output every time.

---

## Scope (What SynConvert IS)

SynConvert is:

* A PC-only batch video transcoder
* A folder-based processing system
* A preset-driven conversion tool
* A local file optimization pipeline for mobile playback

---

## Non-Goals (What SynConvert is NOT)

SynConvert is NOT:

* ❌ A video player
* ❌ A streaming platform
* ❌ A cloud sync tool
* ❌ A mobile application
* ❌ A real-time editing suite
* ❌ A media library manager like Plex

---

## Platform Constraint

* Runs exclusively on **PC (Windows/Linux/macOS optional)**
* Uses local filesystem access only
* No required mobile installation
* Output files are manually transferred to phone via USB or storage media

---

## System Architecture

### 1. Python Backend (Core Engine)

Responsible for:

* File scanning (directories, recursive folder support)
* Job queue management
* FFmpeg command execution
* Conversion presets
* Output file naming and organization
* Logging and progress tracking

### 2. FFmpeg (Execution Layer)

Responsible for:

* Video decoding
* Codec conversion (HEVC → H.264)
* Resolution scaling (1080p → 720p / 480p)
* Audio re-encoding (AAC)

### 3. UI Layer (Optional)

Initially CLI-first. UI may be added later:

* Flutter desktop UI OR simple Python GUI
* Displays queue, progress, and folder selection

UI is strictly a control layer and must not contain conversion logic.

---

## Core Features (MVP)

### Media Stream Preservation Requirements

* SynConvert must preserve existing media streams unless explicitly overridden by presets
* Default behavior is **stream passthrough where possible**

#### Audio Preservation

* If source contains multiple audio tracks (e.g., Japanese + English)

  * ALL audio tracks must be retained in output file
  * No automatic removal or reordering of audio streams
* Audio codecs may be re-encoded to AAC if required for compatibility, but stream count must remain intact

#### Subtitle Preservation

* If source contains embedded subtitles (soft subtitles):

  * All subtitle tracks must be preserved
  * Multi-language subtitle tracks must remain available
* Supported subtitle types:

  * ASS / SSA
  * SRT
  * Embedded MKV subtitle streams

#### Subtitle Handling Rules

* Subtitles must be **copied (stream copy)** where possible
* No burning-in subtitles by default
* No modification of subtitle timing or structure

---

### 1. Folder Input System

* User selects one or more folders
* System recursively detects video files
* Supported formats: .mkv, .mp4, .webm

### Output Safety & Destination Control

* SynConvert must NEVER overwrite source files under any condition
* Source files are treated as immutable inputs
* All outputs must be written to a user-defined destination directory (global default or per job override)
* Source and output directories must always remain strictly separated
* No in-place conversion is permitted

### Directory Mirroring System

* SynConvert must preserve the **directory structure of the input library**
* If a user selects a root folder (e.g. "Failure Frame"), the output must create a matching root folder with the same name in the destination directory
* All subdirectories (e.g. Season 1, Season 2, OVA, Extras) must be preserved exactly as-is in the output structure
* Folder hierarchy must be mirrored 1:1 from input to output

Example:

Input:

* Failure Frame/Season 1/episode files

Output:

* Failure Frame/Season 1/converted files

---

### File Naming Rules

* SynConvert must NOT preserve original source file names
* Original filenames are considered untrusted and often overly verbose or inconsistent

#### Output naming format

Each file must be renamed using a normalized structure:

* **Primary format:** `S{Season}E{Episode} - {Episode Title}.mkv`
* **Full example:** `S03E12 - The Way Things Were.mkv`

#### Naming constraints

* Season and episode numbers must always be zero-padded to two digits (e.g. S01, E03, S04, E24)
* DO NOT include anime/show name in file names (it is already represented by folder structure)
* DO NOT include codec, resolution, or encoding metadata in filename
* DO NOT retain original long filenames

#### Extraction rules

* Season number must be inferred from folder structure (e.g. "Season 1" → S01)
* Episode number must be extracted from filename or metadata where available
* Episode title must be extracted if present; otherwise fallback to `Episode {number}`

If parsing fails:

* Fallback naming: `S01E01.mkv`, `S01E02.mkv`, etc.

---

### Output Container Format

* SynConvert must use **.mkv (Matroska) as the default output container format**
* Reason: MKV provides better flexibility for multi-audio tracks, multiple subtitle streams, and complex media structures commonly found in anime releases
* MKV supports:

  * Multiple audio tracks (e.g. Japanese + English)
  * Multiple subtitle tracks (soft subs preserved)
  * Chapter data (if present)

⚠️ Important clarification:

* MKV does NOT inherently improve video compression quality compared to MP4
* Compression efficiency is determined by the codec (e.g. H.264 / H.265), not the container
* MKV is chosen for **compatibility with multi-stream media preservation**, not bitrate savings

* Default output rule:
  * Video codec: H.264 (libx264 / h264_nvenc depending on hardware)
  * Container: MKV

---

### 2. Preset Conversion System

#### Preset: 720p Mobile (Default)

* Resolution: 1280x720
* Codec: H.264 (GPU-accelerated if available, CPU fallback)
* Audio: AAC
* CRF: ~23 (CPU) / VBR equivalent (GPU)

#### Preset: 480p Saver

* Resolution: 854x480
* Codec: H.264 (GPU-accelerated if available, CPU fallback)
* Audio: AAC
* CRF: ~26 (CPU) / VBR equivalent (GPU)

### 3. Batch Queue System

* Sequential processing (default)
* Optional future parallel processing
* Persistent job list (survives restart)

### 4. Output Management

* Preserved folder structure
* Normalized naming convention: `S{Season}E{Episode} - {Episode Title}.mkv`
* Separate output directory from source

---

## Hardware Acceleration Layer

SynConvert includes an automatic hardware detection and encoding selection system to ensure optimal performance across different machines.

### Auto-Detection Rules

At startup or first job run, SynConvert detects available hardware using FFmpeg and system tools:

* Detect NVIDIA GPU availability (NVENC support)
  * via FFmpeg encoder list (`h264_nvenc`, `hevc_nvenc`)
  * or system detection (`nvidia-smi`)

* Detect Intel QuickSync availability (optional enhancement)
  * via FFmpeg (`h264_qsv`, `hevc_qsv`)

* Default fallback: CPU encoding (`libx264`)

### Encoder Selection Decision Tree

1. If NVIDIA NVENC is available → use `h264_nvenc` (**default**)
2. Else if Intel QuickSync is available → use `h264_qsv` (**default**)
3. Else → fallback to CPU encoder `libx264`

> GPU acceleration is the **preferred and default encoder** when hardware is available. CPU encoding is strictly a fallback.

### Mode Overrides

* Fast Mode → prefer GPU encoder (NVENC/QSV)
* Balanced Mode → CPU encoder (libx264 CRF-based)
* Archive Mode → CPU high-quality encoding (future expansion)

### Design Constraint

* Hardware acceleration must be optional and fail-safe
* System must NEVER crash if GPU acceleration is unavailable
* Encoding must always fall back to CPU automatically

---

## Performance Strategy

* Default FFmpeg preset: fast (or equivalent GPU preset where applicable)
* CRF-based quality control (no bitrate locking in CPU mode)
* VBR-based control in GPU mode (NVENC/QSV)
* Avoid unnecessary upscaling
* Prioritize processing stability and batch throughput over absolute compression efficiency

---

## Offline Guarantee

* No network calls
* No API dependencies
* No cloud services
* Fully functional in airplane mode

---

## Error Handling

* Corrupt file detection → skip + log
* FFmpeg failure → retry once then mark failed
* Disk full → stop queue safely

---

## Logging System

* Track:
  * input file
  * output file
  * duration
  * success/failure
* Stored locally in JSON or simple log file

---

## Future Expansion (Optional)

* Auto-detection of codec quality (HEVC vs H.264)
* Smart preset selection (AI rules, not ML initially)
* Folder watcher (auto-convert on drop)
* Resume interrupted jobs
* Parallel batch processing

---

## Design Constraints

* Keep dependencies minimal (FFmpeg + Python only)
* Avoid over-engineering UI early
* No cloud integration allowed at any stage
* Maintain deterministic, repeatable outputs

---

## Success Criteria

SynConvert is successful when:

* A full anime season can be converted in batch without user supervision
* Output plays smoothly on low-end Android devices
* Storage usage is reduced significantly (30–70%)
* User interaction required only: select folder → press convert

---

## Closing Statement

SynConvert is not meant to be a complex media ecosystem.

It is a **quiet, offline machine** that takes heavy video files and reshapes them into something portable, efficient, and reliable for everyday mobile viewing.
