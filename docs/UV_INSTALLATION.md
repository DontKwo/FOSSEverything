# Developer uv Installation Guide

> **For Everyday Users**: You do **not** need `uv`, Python, or command-line tools to run `FOSSEverything`. Download the standalone desktop installer from the [Download Table](../README.md#download).

Developers building from source, running `pytest`, or executing the strict repository linter use [Astral `uv`](https://docs.astral.sh/uv/) for locked Python dependency management.

---

## Platform Instructions

### Windows

Install `uv` using PowerShell or winget:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
winget install --id=astral-sh.uv -e
```

---

### macOS

Install `uv` using the standalone installer or Homebrew:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
brew install uv
```

---

### Linux

Install `uv` using the standalone installer:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Confirm installation with `uv --version`.

---

## Related Documentation

- [Project Overview](../README.md)
- [Developer Guide](DEVELOPMENT.md)
- [Desktop Installation Guide](INSTALLATION.md)
- [Security Policy](../SECURITY.md)
