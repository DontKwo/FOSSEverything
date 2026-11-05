<!-- noqa: 19 -->
# FOSSEverything Implementation Status and Remaining Work

This document tracks remaining work on the `redesign-next` branch. Items confirmed implemented are removed.
Agents: follow Section 0 invariants before touching any code.

---

## Section 0: Hard Invariants

Every coding agent must obey all constraints below without exception.

### 0.1 Python Execution and Virtual Environment
1. Run Python only through `uv --no-project` with the workspace venv:
   - Windows: `uv run --no-project --python "C:\Users\Josh\projects\FOSSEverything\.venv\Scripts\python.exe" python -m pytest`
   - Linux/container: `uv run --no-project --python ".venv/bin/python" python -m pytest`
2. Never run bare `uv run`, `uv venv`, `python -m venv`, or `pip install` without explicit user permission.
3. Write code only for current target behavior. No dead branches or obsolete wrappers.
4. Every Python function and endpoint must have explicit parameter type annotations and a return type annotation.
5. Inline comments: at most 2 lines, state what code does now.

### 0.2 Mandatory Linter Gate
After every code change:
```powershell
uv run --no-project python C:\Users\Josh\projects\josh-ai-tools\scripts\claudemd_linter.py . --level strict
```
Fix every violation. Re-run until output reads `None. Lint clean.`

Source standards (enforced by linter):
- Pure 7-bit ASCII in all files under `app/` and `tests/` (excluding `app/web/vendor/`). Use `\uXXXX` escapes in JS string literals.
- No em dashes, curly quotes, negative parallelisms, copulative constructions, or hype words.

### 0.3 Static, Contract, and UI Test Guards
1. `tests/test_web_static.py`:
   - Zero inline styles in HTML files.
   - Exact stylesheet link order in `app/web/index.html`: `["tokens.css", "themes.css", "base.css", "layout.css", "components.css", "tools.css"]`.
   - In JS files, never write `el.style.cssText = ...`, `el.setAttribute("style", ...)`, or bare `el.style.<prop> = ...` (only `el.style.transform` is allowed).
   - Zero raw hex colors and raw `rgb()`/`rgba()` in CSS outside `tokens.css` and `themes.css`.
   - Zero `px` units in CSS outside `1px`, `0.5px`, and `@media` queries.
   - In `app/web/js/tools/<tool_id>.js`, every `data-testid` must start with `<tool_id>-`.
2. `tests/test_api_contract.py`:
   - Every public method on `WebApi` and its mixins must carry `@api_method` with signature `def method_name(self, params: dict[str, Any]) -> dict[str, Any]:`.
   - Calling `api.<method>({})` with an empty dict must never raise an unhandled exception.

### 0.4 Component Wrapper Unpacking Rule
Component factory functions (`slider`, `codeEditor`, `filePicker`, `progress`, `segmented`, `switch`, `table`) return `{ el: wrap, getValue: ..., ... }` not a bare `HTMLElement`. Always append `component.el`, never the component object itself.

### 0.5 Save As Rule: Extensionless Default Name + Type Dropdown
- `default_name` must be a clean base name without extension (e.g. `"resume"`, not `"resume.docx"`).
- Always supply `file_types` with human-readable descriptions and extension arrays.
- `app/web/api/base.py:select_save_path` strips accidental extensions from `default_name` and appends the correct extension after the user confirms.

### 0.6 Viewport Boundary Containment
- Every split pane must enforce minimum widths: left pane 15rem, right pane 18rem.
- Resizer clamps drag positions using `clampSplitPx` to prevent right-pane cutoff.
- All split containers carry `min-width: 0; max-width: 100%; overflow-x: hidden; box-sizing: border-box;`.

---

## Section 1: Confirmed Implemented (Reference Only)

The following items were verified working as of the current state of `redesign-next`. Do not re-implement.

- **Settings page**: `settings.js` syntax error fixed. Settings renders correctly.
- **Favorites system**: `store.toggleFavorite` dispatches `foss:favorites-changed`. `router.js` reads `store.get("favorites", [])` dynamically for sidebar. `home.js` filters by `isFavorite` when category is Favorites. Empty state shown when no tools are starred.
- **Distinct tool icons**: All 21 tools have unique SVG paths in `icons.js` and register their icon name in the tool JS file.
- **3D Model Studio resizer**: CSS uses `var(--split-right, 22rem)`. Divider instantiated with `side: "right"`. Resizer clamps both sides.
- **Audio/Video Studio streaming**: `stream_server.py` implements HTTP 206 Partial Content. `media_get_file_url` returns `http://127.0.0.1:<port>/api/media_stream?path=...`. Server starts lazily on first file registration.
- **Resizer clamping**: `clampSplitPx` enforces `minLeftPx = 15 * rootFs`, `minRightPx = 18 * rootFs`. Window resize triggers `reclampSplits`.
- **OCR workbench layout**: `ocr-workbench-split` uses `grid-template-columns: var(--split-left, 24rem) 0.5rem minmax(18rem, 1fr)`.
- **Code editor fill height**: `code-editor-fill` CSS enforces `flex: 1 1 0%; height: 100%; min-height: 0;`. `data.js`, `encoding.js`, `text_tools.js` use `fillHeight: true`.
- **Save-as rule**: `select_save_path` in `base.py` strips extension from `default_name` and passes `file_types` to dialog. Resume uses `default_name: "resume"`. All other tools confirmed to use extensionless names.
- **Resume preview**: `resume-workbench-split` grid: `var(--split-left, 24rem) 0.5rem minmax(18rem, 1fr)`. Sheet uses `width: min(100%, 65rem)`.
- **Network monitor sorting**: Column headers toggle ascending/descending sort. Both "Mark as Known" and "Mark as Unknown" buttons present.
- **Per-app defaults**: `tool_defaults.js` loaded in `index.html`. All 20 tools have `defaults: [...]` in registration object. `router.js` auto-calls `toolDefaults.define(toolDef.id, toolDef.defaults)`. Settings "Per-App Defaults" tab renders tool selector and form.
- **Parity tests**: `test_parity_ops.py` and `test_parity_gui_coverage` both pass.
- **Test data directory**: `tests/test_data/` contains 19 sample files (docx, pdf, txt, md, json, yaml, csv, xml, h5, hdf5, png, jpg, webp, stl, mp4, wav, m3u8, binary stl, scanned pdf).
- **UI walkthrough tests**: All 21 tool walkthroughs exist in `tests/ui/scenarios/` and `tests/ui/scenarios/test_<tool>_walkthrough.py`.

---

## Section 2: Remaining Work

### 2.1 Collage and Palette Tool Defaults Hook Completion

**Issue**: `collage.js` and `palette.js` listen to `foss:tool-defaults-changed` via `applyDefaultsHook` but do not appear to call `window.FOSS.toolDefaults.openEditor(...)` from a gear/defaults button in their topbars.

**Verify** by checking if each tool renders a `data-testid="<tool_id>-defaults-btn"` button in the topbar. If missing, add:
```javascript
window.FOSS.dom.el("button", {
  className: "btn btn-icon btn-ghost btn-sm",
  "data-testid": "<tool_id>-defaults-btn",
  "aria-label": "Tool defaults",
  title: "Edit defaults",
  onClick: function () {
    window.FOSS.toolDefaults.openEditor("<tool_id>", "<Tool Title>");
  }
}, [window.FOSS.icons.el("settings", 16)])
```

Run `tests/test_web_static.py::test_tool_data_testids` to verify testid prefix compliance after adding.

### 2.2 Resume Defaults Gear Button

**Issue**: `resume.js` calls `loadDefaults()` on init and has a `defaultsLoaded` flag but it is unclear if the gear button (`resume-defaults-btn`) exists in the topbar.

**Verify**: Search for `"resume-defaults-btn"` in `resume.js`. If missing, add the gear button to the resume topbar exactly as described in 2.1.

### 2.3 Network Monitor Defaults Gear Button

**Issue**: `network_monitor.js` reads defaults via `window.FOSS.toolDefaults.get(...)` but may not expose a `network_monitor-defaults-btn` topbar button.

**Verify** and add if missing, following the same pattern as 2.1.

---

## Section 3: Test Suite Verification Gate

Execute all verification commands in order. All must pass before marking work complete.

1. Static invariants and contracts:
   ```powershell
   uv run --no-project --python "C:\Users\Josh\projects\FOSSEverything\.venv\Scripts\python.exe" python -m pytest tests/test_api_contract.py tests/test_web_static.py tests/test_parity_ops.py -v
   ```
2. Full feature test suite (508 tests expected):
   ```powershell
   uv run --no-project --python "C:\Users\Josh\projects\FOSSEverything\.venv\Scripts\python.exe" python -m pytest tests/ --ignore=tests/ui -v
   ```
3. Strict linter:
   ```powershell
   uv run --no-project python C:\Users\Josh\projects\josh-ai-tools\scripts\claudemd_linter.py . --level strict
   ```
   Must output: `None. Lint clean.`
