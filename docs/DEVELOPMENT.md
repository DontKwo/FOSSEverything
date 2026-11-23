# Developer Guide & Architecture

Setup, test, lint, and package FOSSEverything from source across Windows, macOS, and Linux.

## Prerequisites

- **Python 3.11+**
- **[Astral `uv`](UV_INSTALLATION.md)**
- **Git**

---

### Windows

```powershell
uv sync --dev
uv run python main.py
uv run pytest --ignore=tests/ui -q
uv run python scripts/build_executable.py
.\dist\FOSSEverything\FOSSEverything.exe --self-test
```

For Windows installer builds, install Inno Setup 6 and run `uv run python scripts/build_installer.py`.

---

### macOS

```bash
uv sync --dev
uv run python main.py
uv run pytest --ignore=tests/ui -q
uv run python scripts/build_executable.py
```

Output bundle: `dist/FOSSEverything.app`.

---

### Linux

```bash
uv sync --dev
uv run python main.py
uv run pytest --ignore=tests/ui -q
uv run python scripts/build_executable.py
```

Output directory: `dist/FOSSEverything/`.

---

## Architecture Overview

1. **Python Domain Layer (`app/features/`)**: Headless pure-Python processing modules with zero GUI dependencies.
2. **Frontend Container (`main.py` + `pywebview`)**: Native OS webview host with drag-and-drop routing, single-instance IPC (`127.0.0.1:47891`), and `--self-test` / `--configure` flags.
3. **Web Interface (`app/web/`)**: Vanilla HTML5, CSS3, and JavaScript loaded locally.
4. **RPC Bridge (`app/web/api/`)**: Mixin-based `WebApi` methods exposed via `@api_method` returning `ok()` or `fail()`.

---

## Verification, Strict Linting & Releases

```bash
uv run pytest
uv run pytest tests/test_api_contract.py tests/test_web_static.py tests/ui/test_ui_shell.py tests/ui/test_ui_tools.py
uv run --no-project python ../ai-dev-tools/scripts/claudemd_linter.py . --level strict --full
uv run --no-project python ../ai-dev-tools/scripts/link_checker.py .
```

The consolidated CI workflow publishes single-platform assets (`FOSSEverything-Windows.exe`, `FOSSEverything-macOS.dmg`, `FOSSEverything-Linux.tar.gz`) under monotonic `vX.Y.Z` tags.

---

## Related Documentation

- [Project Overview](../README.md)
- [Developer uv Installation Guide](UV_INSTALLATION.md)
- [Desktop Installation Guide](INSTALLATION.md)
- [User Guide](USER_GUIDE.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
- [AI Agent Reference](../AGENTS.md)
- [Security Policy](../SECURITY.md)
