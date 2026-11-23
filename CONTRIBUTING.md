# Contributing to FOSSEverything

FOSSEverything is a local-first, offline desktop utility suite licensed under the [MIT License](LICENSE). See [Third-Party Notices](THIRD_PARTY_NOTICES.md) for dependency details.

## Development Setup

Prerequisites: Python 3.11+ and [Astral uv](docs/UV_INSTALLATION.md).

```bash
uv sync
uv run python main.py
```

`uv sync` installs the pinned dependencies from `uv.lock`. Use `uv add <package>` when adding dependencies so `uv.lock` stays synchronized.

## Architecture

The project separates headless domain logic from presentation:

1. **Domain Logic (`app/features/<feature>/ops.py`)**: Pure Python file and data operations without GUI dependencies.
2. **Web API (`app/web/api/`)**: Typed API mixins decorated with `@api_method` returning structured JSON via `ok()` or `fail()`.
3. **Frontend (`app/web/`)**: Vanilla HTML5, CSS3, and JavaScript inside `pywebview`.
4. **Tooltips & Discovery**: Tools register in `app/core/tool_registry.py` with tooltips in `app/core/tooltips.py`.

## Verification Commands

```bash
uv run pytest
uv run pytest tests/test_api_contract.py tests/test_web_static.py tests/test_theme_contrast.py
```

Contributions submitted via pull request are licensed under the [MIT License](LICENSE).

## Related Documentation

- [Project Overview](README.md)
- [Developer Guide](docs/DEVELOPMENT.md)
- [Developer uv Installation Guide](docs/UV_INSTALLATION.md)
- [AI Agent Reference](AGENTS.md)
- [Security Policy](SECURITY.md)
