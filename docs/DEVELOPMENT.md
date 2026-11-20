# Developer Guide & Codebase Architecture

This guide covers setup, testing, build steps, and architectural invariants for developing on FOSSEverything.

---

## 1. Local Environment Setup

FOSSEverything uses [uv](https://astral.sh/uv) to manage Python dependencies.

### Prerequisites
- Python 3.11 or higher
- [uv](https://astral.sh/uv) package manager
- Git

### Initial Setup
```bash
git clone https://github.com/DontKwo/FOSSEverything.git
cd FOSSEverything

# Sync runtime and development dependencies
uv sync --dev

# Launch the application in development mode
uv run python main.py
```

Helper launch scripts:
- Windows PowerShell: `.\setup.ps1`
- macOS / Linux Bash: `./setup.sh`

---

## 2. Architecture Overview

FOSSEverything uses a decoupled, local-first architecture:

1. **Python Domain Layer (`app/features/`)**: Headless pure-Python business logic for document modification, audio/video transcoding, OCR, network auditing, 3D parsing, and file conversion.
2. **Frontend Container (`main.py` + `pywebview`)**: Native OS webview host (WebView2 on Windows, WebKit on macOS and Linux). Provides window lifecycle, drag-and-drop file routing, and single-instance IPC.
3. **Web Interface (`app/web/`)**: Vanilla HTML5, CSS3, and JavaScript without external runtime frameworks. Operates fully offline with zero remote assets.
4. **RPC Bridge (`app/web/api/`)**: Mixin-based `WebApi` class. Methods decorated with `@api_method` are exposed to JavaScript via `window.FOSS.api(method, params)` using `ok()` and `fail()` responses.

---

## 3. Developer & Packaged App Coexistence

Developers often run both source checkouts and installed binary packages on the same workstation:

- **Shared Configuration**: Application settings reside in `~/.fosseverything/settings.json`. Preferences (theme, scale, shortcuts) stay synchronized across both runtimes.
- **Single-Instance IPC**: The desktop app listens on TCP socket `127.0.0.1:47891`. Subsequent invocations forward paths directly to the active window.
- **Shell Integrations**: File associations and right-click context menu integrations use absolute executable paths to avoid collision between dev and installed builds.

---

## 4. Testing & Quality Verification

Run tests before committing code changes:

### Complete Non-UI Test Suite
```bash
uv run python -m pytest --ignore=tests/ui -q
```

### Static Contracts & Asset Checks
```bash
uv run python -m pytest tests/test_api_contract.py tests/test_web_static.py
```

### Headless Visual & DOM Audits
```bash
uv run python -m pytest tests/ui/test_ui_shell.py tests/ui/test_ui_tools.py
```

### Mandatory Linter
```bash
uv run --no-project python scripts/claudemd_linter.py . --level strict
```

---

## 5. Building Standalone Distributables

Executable builds are automated through PyInstaller and platform tooling.

### Windows Standalone & Installer
```bash
# Build onedir binary package
uv run python scripts/build_executable.py

# Build single-file executable
uv run python scripts/build_executable.py --onefile

# Compile Inno Setup installer (requires Inno Setup 6)
uv run python scripts/build_installer.py --version=1.2.3
```
Output locations:
- Portable directory: `dist/FOSSEverything/`
- Installer executable: `installer/Output/FOSSEverything-Setup.exe`

### macOS Application Bundle
```bash
uv run python scripts/build_executable.py
```
Output location: `dist/FOSSEverything.app`

### Linux Standalone Binary
```bash
uv run python scripts/build_executable.py
```
Output location: `dist/FOSSEverything`

---

### Releases and CI

`.github/workflows/build-exe.yml` runs on every push to `main`, every `v*` tag, and pull requests:

1. `version` computes `MAJOR.MINOR.RUN_NUMBER` from `version` in `pyproject.toml` (bump major or minor there), or uses the tag for `vX.Y.Z` pushes.
2. Windows, Linux, and macOS jobs run the tests, build with PyInstaller, smoke test the frozen app (`--configure`), and package. Windows also silently installs and uninstalls the setup wizard and checks its options.
3. `release` (push to `main` or a tag only) publishes a GitHub release with every asset plus `SHA256SUMS.txt`, and marks it latest. The README links use `releases/latest/download/<asset>`, so they never need editing.

Asset names are fixed: `FOSSEverything-Setup.exe`, `FOSSEverything-Portable-win64.zip`, `FOSSEverything-macos.dmg`, `FOSSEverything-Portable-macos.zip`, `FOSSEverything-Portable-linux64.tar.gz`. `tests/test_installer_and_release.py` fails if the workflow, installer script, and README drift apart.

Installer-only flags (used by the setup wizard and `install.sh`): `FOSSEverything --configure --theme=<id> --ui-scale=<0.5-2.5>` writes first-run preferences and exits.
## 6. Extending Tools & Workspaces

To add a new tool or workspace:
1. Implement headless logic under `app/features/<tool_name>/ops.py`.
2. Add corresponding API methods in `app/web/api/tool_<tool_name>.py` and include the mixin in `app/web/api/__init__.py`.
3. Create the tool UI in `app/web/js/tools/<tool_name>.js` and declare view routes in `app/web/js/core/router.js`.
4. Register search terms and keyword aliases in `app/core/tool_registry.py`.
5. Add unit test coverage under `tests/test_<tool_name>_ops.py`.
