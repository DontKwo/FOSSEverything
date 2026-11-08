# fosseverything: local desktop power tool # noqa: 19

[![Privacy: 100% Offline](https://img.shields.io/badge/Privacy-100%25%20Offline-success)](https://github.com/DontKwo/FOSSEverything)
[![Platform: Windows | macOS | Linux](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)](https://github.com/DontKwo/FOSSEverything)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-informational)](https://github.com/DontKwo/FOSSEverything)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)

FOSSEverything is an offline desktop utility suite for editing documents, media, and data locally. Edit PDFs, manipulate images, transcode audio and video, extract text with Tesseract OCR, inspect 3D models, monitor local network sockets, generate QR codes, tailor ATS-friendly resumes, compute folder hash manifests, and batch-convert files. All processing executes on your device with zero cloud tracking, zero accounts, and zero telemetry.

---

## quick start

### Portable Binaries & Distributables
Standalone packages bundle a dedicated runtime with all core dependencies and require zero setup.
- **Windows:** Download `FOSSEverything-Setup.exe` (or `FOSSEverything-Portable-win64.zip`) from [Releases](https://github.com/DontKwo/FOSSEverything/releases). The setup wizard installs Start Menu and Desktop shortcuts.
- **Linux:** Download `FOSSEverything-Portable-linux64.tar.gz` from [Releases](https://github.com/DontKwo/FOSSEverything/releases). Extract and run `./install.sh` (or `./FOSSEverything --install-desktop`) to register the application launcher shortcut with the high-resolution app icon.

### Run From Source
Prerequisites: [uv](https://astral.sh/uv) and Python 3.11+.

```bash
git clone https://github.com/DontKwo/FOSSEverything.git
cd FOSSEverything

# Bootstrap dependencies and launch
uv sync
uv run python main.py
```

Helper launch scripts are also provided:
```bash
./setup.sh        # macOS / Linux
.\setup.ps1       # Windows PowerShell
```

### Developer vs. Packaged Distributable Coexistence
Developers often run both the cloned Git repo via `uv run python main.py` and have the packaged standalone binary installed. Both workflows are designed to coexist cleanly:
- **Shared Offline Configuration:** User preferences (themes, UI scaling, tool settings) reside in `~/.fosseverything/settings.json`, remaining consistent whether launched from source or via the packaged executable.
- **Single-Instance Routing:** If an instance is already running (either development or packaged), subsequent launches automatically forward opened files to the active window via local socket IPC (`127.0.0.1:47891`).
- **Updates:**
  - *Source installs* update dynamically via `git pull && uv sync`.
  - *Packaged binaries* update via GitHub Releases. The automated CI/CD workflow builds fresh release assets for Windows and Linux on new merges and pull requests.
- **Desktop Launchers & Shortcuts:** On Windows, the installer creates system Start Menu and Desktop shortcuts. On Linux, running `FOSSEverything --install-desktop` installs `fosseverything.desktop` into `~/.local/share/applications` and registers high-resolution app icons into `~/.local/share/icons/hicolor/256x256/apps/`.

---

## file integration and shell routing

FOSSEverything automatically routes files opened via double-click, drag-and-drop, or CLI arguments to the matching tool:

- `.pdf` -> PDF Editor
- `.png`, `.jpg`, `.webp`, `.bmp`, `.tiff`, `.svg` -> Image Editor
- `.mp4`, `.mov`, `.mkv`, `.mp3`, `.wav`, `.aac` -> Video & Audio
- `.stl`, `.obj`, `.ply`, `.gltf`, `.step` -> 3D Model Viewer
- `.docx`, `.xlsx`, `.pptx` -> Office Tools
- `.json`, `.yaml`, `.csv`, `.xml`, `.toml` -> Data Tools
- `.zip`, `.tar`, `.gz`, `.7z` -> Archive Tools

Register shell associations in your operating system file manager:

```bash
# Register "Open in FOSSEverything" context menu items
python main.py --register-shell

# Remove shell integration
python main.py --unregister-shell
```

Platform behavior:
- **Windows**: Adds `HKEY_CURRENT_USER` registry keys for right-click file and directory actions.
- **Linux**: Creates a FreeDesktop `.desktop` file under `~/.local/share/applications/`.
- **macOS**: Configures a command-line launcher at `~/.local/bin/fosseverything`.

---

## core tools

| Tool | Capabilities |
|---|---|
| PDFs | View, annotate, reorder, merge, split, compress, password-protect, stamp watermarks, insert page numbers, and extract text. |
| Images | Crop, resize, freehand markup, shapes, text, auto-enhance, blur, pixelate redaction, and screen capture. |
| Video & Audio | Lossless stream-copy trimming, audio extraction (MP3, WAV, AAC), container transcoding, compression presets, and frame capture. |
| OCR & Text | Offline Tesseract OCR across 18+ languages. Generates searchable PDFs with invisible text layers and plain text exports. |
| 3D Model Viewer | Inspect STL, OBJ, PLY, GLTF, and STEP models with Three.js rendering, bounding box measurements, cross-section slicing, and export. |
| Network Monitor | View local socket connections, listening ports, process owners, and live network transfer rates via psutil. |
| Archive & Compression | Compress and extract ZIP, TAR, GZ, and 7Z archives with password protection and integrity checking. |
| File Compressor | Unified media compression tool optimizing PDFs, images, video, and audio to target file size budgets. |
| Resume Builder | Master resume repository with granular bullet-point toggles, section reordering, ATS keyword analysis, and PDF export. |
| File Converter | Batch and single-file format conversions across images, documents, audio, video, spreadsheets, and structured data. |
| Office Documents | Extract text and metadata from DOCX, XLSX, and PPTX documents, with format conversion to PDF, TXT, and Markdown. |
| Metadata Tools | Inspect and edit EXIF tags, PDF document properties, and audio/video ID3 tags. Strip metadata with stream-copy. |
| QR & Barcodes | Generate custom vector SVG QR codes with logo embedding. Scan and decode QR codes and 1D barcodes from files or webcam. |
| Batch Renamer | Batch rename files with regular expressions, sequential zero-padded numbering, case transforms, and disk collision previews. |
| Data Studio | Format, validate, and minify JSON, YAML, TOML, and XML. Evaluate JSONPath queries and infer Draft-07 JSON Schemas. |
| Markdown Editor | Side-by-side Markdown editing with live HTML rendering, table formatting, and document export. |
| Color Palette | Extract dominant palettes using median-cut and K-means clustering. Live eyedropper pixel sampler with WCAG contrast ratios. |
| Photo Collage | Arrange photos into custom grid templates with borders, cell padding, fit modes, and captions. |
| Hash & Verify | Checksum calculation (SHA-256, SHA-512, MD5, BLAKE2). Generate and verify directory tree manifest files. |
| Text Tools | Case transforms, text reversal, whitespace normalization, line deduplication, regex search, and side-by-side diffing. |
| Encoding / Decoding | Encode and decode Base64, URL percent-encoding, HTML entities, hex strings, and byte representations. |

---

## architecture and privacy

- **100% Local Processing**: All tasks execute directly on local CPU and GPU resources.
- **Zero Telemetry**: No tracking pixels, crash analytics, external pings, or background cloud sync.
- **Safe Outputs**: Modifying operations save to new file destinations by default.
- **Keyboard Navigation**: Press `Ctrl+K` (or `Cmd+K` on macOS) anywhere to invoke the global command palette.

Read [PRIVACY.md](PRIVACY.md) for full data processing details.

---

## building standalone executables

Build standalone distributable binaries with PyInstaller:

```bash
# Windows
build.bat

# macOS / Linux
bash build.sh

# Platform-agnostic direct invocation
python scripts/build_executable.py

# Single-file binary distribution
python scripts/build_executable.py --onefile
```

Build outputs are saved to `dist/FOSSEverything.exe` (Windows), `dist/FOSSEverything.app` (macOS), or `dist/FOSSEverything` (Linux).
PyMuPDF fallback compression operates automatically when Ghostscript is not present.

To build the Windows installer package (requires [Inno Setup](https://jrsoftware.org/isinfo.php)):
```bash
python scripts/build_installer.py
```

---

## contributing and license

Contributions are welcome. Please refer to [CONTRIBUTING.md](CONTRIBUTING.md) for development setup instructions and required verification checks.

FOSSEverything is distributed under the GNU Affero General Public License v3.0 or later. See [LICENSE](LICENSE) for terms and [NOTICES.md](NOTICES.md) for third-party dependency notices.
