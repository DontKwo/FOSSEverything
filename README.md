# fosseverything: local desktop power tool # noqa: 19

[![Privacy: 100% Offline](https://img.shields.io/badge/Privacy-100%25%20Offline-success)](https://github.com)
[![Platform: Windows | macOS | Linux](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)](https://github.com)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-informational)](https://github.com)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)

FOSSEverything is the all-in-one local desktop power tool. Edit PDFs, images, videos, audio, extract text with offline OCR, scan & decode QR/barcodes, tailor master resumes per job, compute recursive folder checksum manifests, query structured data, and convert files. All processing is 100% offline on your own machine with zero cloud tracking, zero accounts, and zero telemetry.

---

## quick start

Two paths, for two audiences. Both are a single step; neither requires anything
pre-installed.

### Just want to use the app? One download, nothing else to install.
The installer/binary is a self-contained build with its own bundled Python
runtime and all dependencies baked in. You never touch Python, uv, or a terminal.
- **Windows:** download `FOSSEverything-Setup.exe` from [Releases](https://github.com)
  and run it. Installs the app with Start Menu/Desktop shortcuts and an uninstaller.
- **macOS / Linux:** download the portable `FOSSEverything` binary from
  [Releases](https://github.com) and run it (`./FOSSEverything`).

### Want to run from source / contribute code? One script.
```bash
git clone https://github.com/your-username/fosseverything.git
cd fosseverything

./setup.sh        # macOS / Linux
.\setup.ps1        # Windows (PowerShell)
```
This one script installs [uv](https://astral.sh/uv) if it's missing, uses it to fetch
a matching Python and all dependencies (`uv sync`), and launches the app
(`uv run python main.py`). Nothing needs to be pre-installed here either.

Already have uv on PATH? Skip the script and run the same two commands yourself:
```bash
uv sync
uv run python main.py
```

---

## file integration and smart file routing

FOSSEverything automatically detects and opens files in the right tool when launched with a filename (via double-click, CLI, or "Open with"):

- `.pdf` -> PDF Editor
- `.png`, `.jpg`, `.webp`, `.bmp` -> Image Editor
- `.mp4`, `.mov`, `.mkv`, `.mp3`, `.wav` -> Video & Audio
- `.json`, `.yaml`, `.csv`, `.xml` -> Data Tools

Register FOSSEverything with your OS file manager so "Open in FOSSEverything" appears in right-click menus:

```bash
# All platforms (Windows, macOS, Linux)
python main.py --register-shell

# To remove
python main.py --unregister-shell
```

Platform details:
- Windows: Writes `HKEY_CURRENT_USER` registry entries so "Open in FOSSEverything" appears for all file types and folders. Set as default app via right-click > Open with > Choose another app > check Always use this app.
- Linux: Installs a FreeDesktop `.desktop` file to `~/.local/share/applications/` with MIME-type associations for GNOME, KDE, and compatible file managers.
- macOS: Creates a CLI launcher at `~/.local/bin/fosseverything`. Set as default PDF/image viewer via Finder > Get Info > Open With > Change All.

---

## key features

| Workspace | Description |
|---|---|
| PDFs | View, annotate, reorder, merge, split, compress, protect/encrypt, stamp diagonal watermarks, insert page numbers, and extract text. |
| Images | Crop, resize, freehand markup, shapes, text, auto-enhance, blur/sharpen, redacting brush, and interactive screen capture / snipping. |
| Video & Audio | Frame-accurate and lossless fast stream-copy trim, 1-click audio extraction to MP3/WAV/AAC, transcode formats, compress (Discord 8MB preset), mute audio, and high-res frame capture. |
| OCR & Text | 100% offline Tesseract OCR (18+ languages). Extract text from scans or images and create searchable PDFs with invisible text layers. |
| Resume Builder | Master resume repository. Click to enable/disable individual bullet points per job application, reorder sections, analyze ATS keyword matches, and export clean PDFs. |
| Converter | Convert files single or in batch queues across images, PDFs, videos, audios, JSON, YAML, and CSV. |
| Metadata | Inspect EXIF, PDF document properties, and audio/video tags (ID3, QuickTime, Vorbis). Strip metadata with lossless stream copy. |
| QR Codes & Barcodes | Generate custom QR codes with logo embedding and vector SVG export. Scan and decode QR codes and barcodes from images/PDFs/clipboard with Wi-Fi password copy and URL opening. |
| Renamer | Batch rename files with Regex capture groups, find/replace, sequential zero-padded numbering, and live collision-safe previews. |
| Data Tools | Pretty-print, format, and minify JSON, YAML, and XML. Evaluate JSONPath queries and infer JSON Schema (Draft-07). |
| Color Palette | Extract dominant color palettes and sample exact pixel colors from images with the mouse eyedropper tool. |
| Photo Collage | Combine multiple photos into clean, customizable grid layouts with fit modes, border padding, and captions. |
| Hash & Verify | Calculate and verify SHA-256, SHA-512, MD5, and SHA-1 checksums offline. Directory Manifest Generator and Verifier for recursive folder integrity checks. |
| Text Tools | Case conversion, text/line reversal, whitespace and line cleanup, sort/dedupe/number lines, regex find & replace, and a diff checker. |
| Encoding / Decoding | Encode and decode text and files between Base64, URL/percent-encoding, HTML entities, hex, and binary. |

---

## privacy and architecture pledge

- 100% Local Processing: Every operation (OCR, PDF rendering, media transcoding, metadata inspection, data formatting, QR decoding) executes locally on your CPU/GPU.
- Zero Telemetry: No analytics, tracking pixels, cookies, network pings, or background cloud calls.
- Safe Outputs: Operations never overwrite original input files without explicit user confirmation.
- Global Command Palette: Press `Ctrl+K` (or `Cmd+K`) anywhere to search and launch any tool instantly.

See [PRIVACY.md](PRIVACY.md) for the full privacy statement.

---

## building standalone executables

Compile FOSSEverything into a portable standalone binary for any platform:

```bash
# Windows
build.bat

# macOS / Linux
bash build.sh

# All platforms (directly with Python or uv)
python scripts/build_executable.py
# Or for a single-file bundle:
python scripts/build_executable.py --onefile
```

Output: `dist/FOSSEverything.exe` (Windows), `dist/FOSSEverything.app` (macOS), `dist/FOSSEverything` (Linux).
PyMuPDF's fallback compression is used automatically if Ghostscript is not installed -- PDF compression works everywhere with no extra setup.

**Reproducible builds**: `uv.lock` pins the exact resolved version of every dependency, so `uv sync` (or `python scripts/build_executable.py`, which uses the same environment) reproduces the same dependency set on any machine. Only the Python interpreter version (`>=3.11,<4.0`, per `pyproject.toml`) and platform-specific system tools (Ghostscript, Calibre, a local Java runtime for LanguageTool) are outside the lockfile's control, since those are optional external programs invoked via subprocess, not bundled dependencies.

To also build the Windows GUI installer (wraps the executable above with Inno Setup):
```bash
python scripts/build_installer.py
```
This requires the free [Inno Setup](https://jrsoftware.org/isinfo.php) compiler and is
Windows-only; it prints a clear message and exits on other platforms.

---

## contributing and license

Contributions are welcome! Please feel free to submit a pull request or open an issue -- see [CONTRIBUTING.md](CONTRIBUTING.md) for how to set up a dev environment and the required pre-commit checks.

Distributed under the GNU Affero General Public License v3.0 (or later). See [LICENSE](LICENSE) for the full text and [NOTICES.md](NOTICES.md) for why AGPL-3.0 was chosen and for third-party dependency/model license notices.
