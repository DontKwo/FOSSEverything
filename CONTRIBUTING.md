# Contributing to FOSSEverything

FOSSEverything is a local-first, offline desktop utility suite licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later). See [LICENSE](LICENSE) and [NOTICES.md](NOTICES.md).

## Development Setup

Prerequisites: Python 3.11+ and [uv](https://astral.sh/uv).

```bash
git clone https://github.com/DontKwo/FOSSEverything.git
cd fosseverything
uv sync
uv run python main.py
```

`uv sync` installs the pinned dependencies from `uv.lock`. Use `uv add <package>` to add dependencies so `uv.lock` remains synchronized.

## Architecture

The project maintains a strict separation between domain operations and presentation:

1. **Domain Logic (`app/features/<feature>/ops.py`)**:
   Headless Python modules containing pure computational and file operations. These modules import no GUI libraries and remain independently testable.
2. **Web API (`app/web/api/`)**:
   Typed API mixins decorated with `@api_method` that validate incoming parameters, invoke domain functions, and return structured JSON responses via `ok()` or `fail()`.
3. **Frontend (`app/web/`)**:
   Vanilla HTML5, CSS3, and JavaScript running inside pywebview (Edge WebView2 on Windows, WebKit on macOS and Linux). Tools reside in `app/web/js/tools/<tool_id>.js`.
4. **Tooltips and Registration**:
   Tools register in `app/core/tool_registry.py` and map user-facing action tooltips through `app/core/tooltips.py`.

## Running Tests

Run the test suite through uv:

```bash
# Run feature and ops unit tests
uv run pytest

# Run API contract, styling, and web static validation tests
uv run pytest tests/test_api_contract.py tests/test_web_static.py tests/test_theme_contrast.py
```

## Code Style and Verification

Before submitting changes, ensure the codebase complies with project rules:

1. Every Python function requires explicit parameter and return type annotations.
2. Comments must be two lines or fewer and describe current behavior.
3. Web assets and markdown documentation must use pure ASCII characters. Avoid em dashes, Unicode quotes, and decorative banners.
4. Run the mandatory strict linter and resolve all reported items:

```bash
uv run --no-project python C:\Users\Josh\projects\josh-ai-tools\scripts\claudemd_linter.py . --level strict
```

## Contribution Licensing

Contributions submitted via pull request are licensed under the AGPL-3.0-or-later license as specified in [LICENSE](LICENSE).
