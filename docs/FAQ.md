# FOSSEverything FAQ

## Directory Indexing Criteria

**Q: How does FOSSEverything index and search capabilities internally?**

A: FOSSEverything uses a completely offline, heuristic-based search engine implemented in `app/core/tool_registry.py` and `app/core/tooltips.py`. There are no cloud indexers or vector databases used. Instead:
- Tools register intent-based keywords and aliases (e.g. `shrink` maps to `compress`).
- When a user performs a search, the text is split into lowercase words.
- The engine computes a `difflib.SequenceMatcher` ratio against known terms.
- Tooltips and elements are filtered via intersection matching to suggest the relevant UI actions instantly.

## Licensing Requirements

**Q: What license is FOSSEverything distributed under?**

A: FOSSEverything is licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later).

**Q: Why AGPL-3.0-or-later?**

A: FOSSEverything integrates several dependencies with strong copyleft requirements. Specifically:
- **PyMuPDF**: Essential for PDF manipulation and Tesseract OCR integration, licensed under AGPL-3.0-or-later.
- **mutagen** and **language-tool-python**: Licensed under GPL v2/v3 terms.

To comply with the distribution obligations of these foundational dependencies without requiring commercial licenses, the combined work must be distributed under compatible AGPL-3.0-or-later terms. See the `LICENSE` and `NOTICES.md` files for full details on third-party licenses.

## API Access

**Q: How does the frontend communicate with the backend? Can I access the API externally?**

A: FOSSEverything does not expose an open HTTP server or REST API to the local network or the internet.

Instead, the UI uses the `pywebview` JavaScript bridge to communicate directly with the local Python runtime.
- In Python, API methods are defined on `WebApi` (located in `app/web/api/__init__.py`) using lazy-loaded mixins and the `@api_method` decorator.
- In JavaScript, these are invoked via `window.FOSS.api('method_name', { parameters })`.

This ensures 100% offline, secure, native local processing without exposing data outside the immediate application process.
