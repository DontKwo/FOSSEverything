# FOSSEverything User Guide

Welcome to FOSSEverything, the offline desktop suite for documents, media, data, 3D models, and system utilities.

## Installing

Download the single package for your computer from [Latest Releases](https://github.com/DontKwo/FOSSEverything/releases/latest) and follow the [Desktop Installation Guide](INSTALLATION.md) for Windows, macOS, or Linux:

- **Windows**: `FOSSEverything-Windows.exe` runs the setup wizard (per-user install needs no admin rights, optional Explorer right-click menu, Open With entries, desktop shortcut, initial theme, and UI scale).
- **macOS**: `FOSSEverything-macOS.dmg` packages `FOSSEverything.app` (drag to Applications and approve under Privacy & Security if prompted).
- **Linux**: `FOSSEverything-Linux.tar.gz` includes `FOSSEverything` and `./install.sh` (interactive or `--theme`, `--ui-scale`, `--prefix` flags).

### Silent Windows Installer Options

```text
FOSSEverything-Windows.exe /VERYSILENT /CURRENTUSER /DIR="<install folder>" /TYPE=compact /COMPONENTS="ctx,assoc\pdf" /TASKS=desktopicon /Theme=dark /Scale=1.25
```

Themes: `ut_austin_dark`, `dark`, `light`, `solarized`, `monokai`, `cyberpunk`, `ut_austin`. Scales: `0.9`, `1.0`, `1.1`, `1.25`, `1.5`, `2.0`.

### Silent Linux Installer Options

```bash
./install.sh --prefix ~/apps/FOSSEverything --theme dark --ui-scale 1.25 --no-cli-link --yes
./install.sh --uninstall --prefix ~/apps/FOSSEverything --yes
```

---

## Using the Application

- **Command Palette (`Ctrl+K` / `Cmd+K`)**: Type plain words such as `shrink`, `pdf`, `strip`, or `convert image` to jump to matching tools.
- **Drag and Drop**: Drag any document, image, media file, archive, or 3D model onto the window to open its matching workspace.
- **Offline Privacy**: Every conversion runs locally on your CPU and disk unless you explicitly trigger an optional neural model download in the Background Remover.

---

## Tool Suites

- **Documents**: PDF Studio (merge, split, reorder, compress, encrypt, redact), Offline OCR, Markdown Studio, Resume Studio.
- **Visuals & 3D**: Image Studio, Photo Collage, Color Palette Extractor, 3D Mesh & STEP Viewer.
- **Media**: Audio/Video Studio, Trim/Stream Copy, Playlist Manager, Batch Compressor.
- **Data & Security**: Data Studio (JSON/YAML/TOML/CSV/XML), Text Tools, Encoding/Hashing, Unit Converter, Local Network Monitor, Metadata Stripper, QR & Barcode Tools.

---

## Related Documentation

- [Project Overview](../README.md)
- [Desktop Installation Guide](INSTALLATION.md)
- [Frequently Asked Questions](FAQ.md)
- [Privacy Statement](../PRIVACY.md)
- [Developer Guide](DEVELOPMENT.md)
- [Security Policy](../SECURITY.md)
