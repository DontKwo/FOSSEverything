# AI Agent Operational Reference (AGENTS.md)

This file contains operational details, guidelines, and context about the FOSSEverything codebase intended for autonomous and AI agents working on the project.

## Web Application Architecture

FOSSEverything uses a decoupled architecture with a strict separation between domain logic and presentation:
- **Backend**: Python-based headless domain logic. The entry point is `main.py`, orchestrating local file operations.
- **Frontend Container**: The application utilizes `pywebview` to render the web interface natively on desktop operating systems (Edge WebView2 on Windows, WebKit on macOS and Linux).
- **Web Interface**: Located entirely in `app/web/`. It uses vanilla HTML5, CSS3, and JavaScript, strictly adhering to zero external framework dependencies to ensure a 100% offline capability.

## Database Schemas

The application primarily uses file-based processing. However, a local database is implemented for specific features:
- **Network Monitor Database (`app/features/network_monitor/db.py`)**: Uses a local SQLite file to record history.
  - `destinations`: Tracks target IP addresses and domains (`ip TEXT PRIMARY KEY`, `domain TEXT`, `known BOOLEAN`, `first_seen TIMESTAMP`, `last_seen TIMESTAMP`).
  - `connection_log`: Records connection events (`timestamp TIMESTAMP`, `local_port INTEGER`, `remote_ip TEXT`, `remote_port INTEGER`, `process_name TEXT`, `status TEXT`).

## Search Indexing

Search functionality operates completely offline without AI or cloud dependencies.
- **Tool Registry (`app/core/tool_registry.py`)**: Tools register capabilities using keyword aliases. The search normalizes text queries and computes simple SequenceMatcher ratios and intersection matching.
- **Tooltips (`app/core/tooltips.py`)**: Searchable index of interactive elements and their corresponding help text.

## Static Asset Pipeline

All frontend assets are static and served directly:
- **Location**: `app/web/`
- **Components**: `index.html` serves as the single-page application host, `js/` contains module logic separated by component (e.g., `js/tools/`, `js/core/`), and `css/` houses stylesheet modules.
- **No Build Step**: JS and CSS are loaded as-is without transpilation or minification steps in the source repo, allowing direct edits to take effect immediately in development (`main.py --dev`).

## API Endpoints

The bridge between JS and Python uses a mixin-based WebApi pattern defined in `app/web/api/__init__.py`.
- **Definition**: Endpoints are defined using `@api_method` and return dictionary structures via `ok(data)` or `fail(message)`.
- **Invocation**: From frontend via `window.FOSS.api('method_name', {params})`.
- **Lazy Loading**: Heavy mixins are initialized on demand using `LazyMethod` to reduce the application boot time footprint.

## Verification Commands for Test Suites and Linting

Before any commit or submission, all invariants must be verified to prevent regressions:

- Run complete pytest suite:
  ```bash
  uv run pytest
  ```
- Run static checks, API contracts, and theme validations directly:
  ```bash
  uv run pytest tests/test_api_contract.py tests/test_web_static.py
  ```
