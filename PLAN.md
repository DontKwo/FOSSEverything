<!-- noqa: 19 -->
# FOSSEverything Master UI/UX Redesign and Implementation Specification

This document is the comprehensive, step-by-step master implementation specification for coding agents (specifically structured for non-reasoning models) to resolve all UI/UX friction points, layout defects, unpolished designs, missing features, and broken interactions across `FOSSEverything`.

Follow every phase in exact numerical order (`Section 0` through `Section 8`). Do not skip steps, invent alternate file names, alter public API signatures, or leave partial stubs.

---

## Section 0: Master Operating Manual and Hard Invariants

Every coding agent working on this codebase must obey all constraints in this section without exception.

### 0.1 Python Execution and Virtual Environment Rules
1. Run Python commands only through `uv` with `--no-project` and the workspace virtual environment:
   - Windows test runner: `uv run --no-project --python "C:\Users\Josh\projects\FOSSEverything\.venv\Scripts\python.exe" python -m pytest`
   - Linux/container test runner: `uv run --no-project --python ".venv/bin/python" python -m pytest`
2. Never run bare `uv run`, `uv venv`, `python -m venv`, or `pip install` without explicit user permission.
3. Write code only for current target behavior. Avoid obsolete wrapper functions or dead execution branches.
4. Every Python function, method, and endpoint signature must include explicit parameter type annotations and an explicit return type annotation (`-> ReturnType`).
5. Keep inline comments to at most 2 lines stating strictly what the code does now.

### 0.2 Mandatory Repository Linter Gate
After every code change, execute the strict linter:
```powershell
uv run --no-project python C:\Users\Josh\projects\josh-ai-tools\scripts\claudemd_linter.py . --level strict
```
- If violations are reported, open the generated `lint_report.txt` path printed in the terminal, resolve every violation, and re-run until the output reads `None. Lint clean.`.
- Source file standards enforced across Python, JS, CSS, HTML, and Markdown files:
  - Pure 7-bit ASCII characters only (`0x00` through `0x7F`) in all source files under `app/` and `tests/` (excluding `app/web/vendor/`). In JS string literals, use `\uXXXX` escape sequences (such as `\u2022` or `\u00d7`) instead of literal non-ASCII characters.
  - Never use em dashes (rewrite sentences cleanly), en dashes, curly quotes, negative parallelisms, copulative avoidance ('serves as', 'stands as'), or hype words ('robust', 'seamlessly', 'pivotal', 'delve', 'furthermore').

### 0.3 Automated Static, Contract, and UI Test Guards
1. **`tests/test_web_static.py`**:
   - Zero inline styles in `app/web/index.html` or any `.html` file.
   - Exact stylesheet link order in `app/web/index.html`: `["tokens.css", "themes.css", "base.css", "layout.css", "components.css", "tools.css"]`.
   - In JS files, never write `el.style.cssText = ...`, `el.setAttribute("style", ...)`, or `el.style.<prop> = ...` (only `el.style.transform` is allowed for direct property assignment). Always use `el.style.setProperty("prop-name", value)` or toggle CSS classes.
   - Zero raw hex colors and zero raw `rgb()`/`rgba()` in CSS outside `tokens.css` and `themes.css`. Always use `var(--token-name)`.
   - Zero `px` units in CSS outside `1px`, `0.5px`, and `@media` queries. Use `rem`, `%`, `vh`, `vw`, or unitless values.
   - In `app/web/js/tools/<tool_id>.js`, every `data-testid` attribute must start with `<tool_id>-`.
2. **`tests/test_api_contract.py`**:
   - Every public method on `WebApi` and its mixins must be decorated with `@api_method` and have signature `def method_name(self, params: dict[str, Any]) -> dict[str, Any]:`.
   - Internal helper methods on mixins must begin with an underscore `_` or live at the module level.
   - Calling `api.<method>({})` with an empty dict must never raise an unhandled exception.
3. **`tests/ui/audit.js` DOM and Pixel Invariants (`A1` through `A22`)**:
   - `A1`: Zero document-level scrollbars (`html` and `body` stay locked to `100vw x 100vh`).
   - `A4-A7`: Zero child overflow or sibling overlap across `800x600`, `1280x720`, and `1920x1080`.
   - `A9`: Truncated elements must carry `data-truncate-ok="true"` and a valid `title` attribute.
   - `A10`: Text inside `button`, `[role="tab"]`, `.nav-item`, `.chip`, and `label` must not wrap (`white-space: nowrap`).
   - `A12`: Interactive controls inside `#view-root` must measure at least `2rem x 2rem` (or carry `data-dense="true"`).

### 0.4 Universal Component Wrapper Unpacking Rule
Component factory functions (`slider`, `codeEditor`, `filePicker`, `progress`, `segmented`, `switch`, `table`) return an object dictionary `{ el: wrap, getValue: ..., ... }` instead of a bare `HTMLElement`.
1. In `app/web/js/core/dom.js`, ensure `window.FOSS.dom.el` automatically unpacks `child.el` if present:
   ```javascript
   if (child.nodeType) {
     element.appendChild(child);
   } else if (child.el && child.el.nodeType) {
     element.appendChild(child.el);
   }
   ```
2. Provide a helper `window.FOSS.dom.append(parent, child)`:
   ```javascript
   window.FOSS.dom.append = function (parent, child) {
     if (!parent || !child) return;
     var node = child.nodeType ? child : (child.el && child.el.nodeType ? child.el : null);
     if (node) parent.appendChild(node);
   };
   ```
3. Whenever a tool appends a component instance directly via native `appendChild`, always append `component.el`.

### 0.5 Universal Save Path Prompt and Automatic File Extension Rule
No application tool may ever save a file silently or assume an output directory.
1. Always invoke `window.FOSS.api("select_save_path", { title: ..., default_name: ..., file_types: ... })`. If the user cancels the dialog, immediately abort without error.
2. In `app/web/api/base.py:select_save_path`:
   - If `default_name` contains an extension, automatically verify that the selected path ends with that extension. If the user omitted the extension, append it automatically:
     ```python
     if default_name and "." in default_name:
         expected_ext = "." + default_name.rsplit(".", 1)[-1].lower()
         if not p_str.lower().endswith(expected_ext):
             p_str = p_str + expected_ext
     ```
3. In tool JavaScript, verify the selected path has the correct extension before submitting the processing job.

---

## Section 1: Post-Implementation Forensic Evaluation of Prior AI Work

This section documents the specific failure modes discovered during the forensic audit of prior agent changes. Lower-level coding models must read this section to avoid repeating these exact mistakes.

### 1.1 Premature Reintroduction of Deleted Tools
- **The Mistake**: Prior agents re-added `screenshot.js`, `hash.js`, `tool_screenshot.py`, and `tool_hash.py` and placed them back into `DEFAULT_SECTIONS`, `DEFAULT_APPS`, `index.html`, and `WebApi`.
- **The Consequence**: The user explicitly forbade screen capture and hashing tools. Having them present violates core product requirements.
- **The Correct Rule**: Erase every trace of `screenshot` and `hash`. There are exactly 21 canonical tools in the application.

### 1.2 Duplicate Settings Access Points
- **The Mistake**: Prior agents left `.sidebar-footer` containing `nav-settings` at the bottom-left of the sidebar while also maintaining `topbar-settings-btn` in the topbar.
- **The Consequence**: Cluttered navigation and confusion about settings location.
- **The Correct Rule**: The topbar gear icon (`topbar-settings-btn`) must be the sole access point to Settings.

### 1.3 UI Scale Slider Feedback Oscillation (Slider Freakout)
- **The Mistake**: In `app/web/js/settings.js`, the zoom slider fired `window.FOSS.theme.setScale(val)` on every raw `input` tick. Because `html` font-size is `calc(var(--font-base) * var(--ui-scale))`, changing `--ui-scale` mid-drag immediately resized the slider container.
- **The Consequence**: The slider track expanded or contracted underneath the user's stationary mouse cursor, moving the slider thumb away from the cursor and creating wild displacement and runaway feedback.
- **The Correct Rule**: During active slider dragging, update only the percentage text label. Apply the actual scale transform only on pointer release or debounced change (`150ms`).

### 1.4 Viewport Boundary Collapse at High Zoom
- **The Mistake**: At scale factors above `1.30` (up to `2.50`), parent containers (`.app`, `.main`, `.scroll-main`, `.page`) lacked `overflow-y: auto` and minimum bounds containment.
- **The Consequence**: Settings content overflowed below the screen, pushing the zoom slider off-screen (measured at `y=1676px` in an `820px` window), locking users out of zooming back without keyboard shortcuts.
- **The Correct Rule**: Enforce `overflow-y: auto; min-height: 0; min-width: 0;` on all main scroll containers and keep the topbar pinned (`position: sticky; top: 0; z-index: var(--z-topbar)`).

### 1.5 Duplicate Settings Panels on Section Deletion
- **The Mistake**: In `settings.js:renderSidebarCustomizer(panel)`, `persistAndRefresh()` called `renderSidebarCustomizer(panel)` without first clearing `panel.innerHTML = ''`.
- **The Consequence**: Deleting or reordering a section appended a new copy of the customizer below the existing one, duplicating the Settings UI repeatedly.
- **The Correct Rule**: The first line of `renderSidebarCustomizer(panel)` must be `panel.innerHTML = '';`.

### 1.6 Clunky Dropdowns and Single-Section App Locking
- **The Mistake**: Prior agents rendered a `<select>` dropdown ('Move to...') on every app row and enforced `seen[it.id] = true` in `router.js:resolveSidebarLayout`.
- **The Consequence**: Ugly interface, tedious navigation, and inability to place a tool in both `Favorites` and its category section.
- **The Correct Rule**: Use pure HTML5 drag-and-drop with mini SVG icons matching the sidebar. Allow apps to exist in multiple sections.

### 1.7 Static Read-Only Keybindings Table
- **The Mistake**: Keybindings were hardcoded in `shortcuts.js` with a static HTML table in `settings.js`.
- **The Consequence**: Users could not customize or rebind shortcuts.
- **The Correct Rule**: Implement an interactive key recorder UI that captures key combinations and persists them to `store.get('custom_keybindings')`.

### 1.8 Persistent First-Run Startup Modal
- **The Mistake**: `app.js:showFirstRunWelcome` prompted users to register Windows Explorer context menus on startup.
- **The Consequence**: Annoying popup on launch.
- **The Correct Rule**: Delete `showFirstRunWelcome` completely. Context menu registration belongs only inside Settings.

### 1.9 Resume DOCX Style Conflicts and Bullet Offsets
- **The Mistake**: In `app/features/resume/ops.py:export_docx`, the agent applied `doc.add_paragraph(style='List Bullet')` while simultaneously setting `paragraph_format.left_indent = Inches(0.125)`. They also used 4 literal spaces (`'    '`) instead of tab stops for dates, and concatenated job title, company, and date on a single line separated by commas.
- **The Consequence**: `style='List Bullet'` already contains Microsoft Word list formatting (`w:numPr`). Adding manual indentation created double indents, misaligned bullet glyphs, pushed text far to the right, and caused the document to spill onto a second page.
- **The Correct Rule**: Apply style `'Normal'` to bullet paragraphs with `left_indent = Pt(9.0)`, `first_line_indent = Pt(-9.0)`, explicit bullet glyph `\u25cf\t` in Arial 8.5pt, tab stop at `Pt(9.0)`, and tight single line spacing (`1.0`). Use a right-aligned tab stop at `7.0 inches` (`Pt(504)`) for dates. Guarantee exact 1-page fit.

### 1.10 Silent Auto-Saving in Collage
- **The Mistake**: In `collage.js:handleSave`, the agent constructed an output path automatically (`outPath = dir + '/collage' + flatExt`) without prompting the user.
- **The Consequence**: Files were written silently to disk without letting the user choose the destination or name.
- **The Correct Rule**: Always call `window.FOSS.api('select_save_path', ...)` and await the user's explicit selection.

### 1.11 3D Model Studio Resizing and Dummy Tabs
- **The Mistake**: The agent created dummy `scale` and `measure` tabs in `model3d.js` that routed back to the inspector. The 3D canvas also captured pointer events during sidebar divider drag, breaking resizer tracking.
- **The Consequence**: Broken tabs and unresizable sidebars with properties hidden behind fixed containers.
- **The Correct Rule**: Delete `scale` and `measure` tabs from the router tabs array. Integrate scale and measurement directly inside `Inspector & Tools`. Set `pointer-events: none` on canvases during resizer drag. Ensure sidebar has `overflow-y: auto`.

### 1.12 Missing PascalCase Support
- **The Mistake**: The frontend had a `PascalCase` button, but `app/web/api/tool_text_tools.py:text_tools_case` lacked a branch for `pascal`, and `app/features/text_tools/ops.py` lacked `to_pascal_case`.
- **The Consequence**: Clicking the button threw `Unsupported case mode: pascal`.
- **The Correct Rule**: Implement `to_pascal_case` in ops and handle `pascal` in the API handler.

### 1.13 Inverted Unit Converter Layout and Pint Mentions
- **The Mistake**: The agent placed conversion options and category selectors at the top of the sidebar, burying From Unit, To Unit, and the Convert button at the bottom. The UI also displayed 'Pint-backed dimensional analysis'.
- **The Consequence**: Inconvenient user workflow and forbidden backend terminology in user-facing text.
- **The Correct Rule**: Move Quantity Value, From Unit, Swap button, To Unit, and Convert button to the top. Move options to the bottom. Eradicate the word 'Pint' completely.

### 1.14 Tiny Fixed Textboxes in Data Studio and Encoding
- **The Mistake**: Monospace editors were instantiated without `fillHeight: true`, and intermediate grid containers collapsed to zero height.
- **The Consequence**: Tiny 4-line textboxes surrounded by massive empty whitespace.
- **The Correct Rule**: Configure `fillHeight: true` on all code editors and apply `height: 100%; flex: 1 1 0%; min-height: 20rem;` in CSS.

### 1.15 Converter Quality Slider appendChild Exception
- **The Mistake**: In `converter.js:180`, `contextualOptionsContainer.appendChild(qualitySlider)` was invoked on a component dictionary object `{ el: wrap, getValue: ... }` instead of the DOM node.
- **The Consequence**: Threw `TypeError: Failed to execute 'appendChild' on 'Node': parameter 1 is not of type 'Node'` whenever users selected JPEG or WEBP.
- **The Correct Rule**: Unpack `qualitySlider.el` and use `window.FOSS.dom.append`.

---

## Section 2: Complete Erasure of Screen Capture (`screenshot`) and Checksums (`hash`)

Execute this section first to clean the codebase of forbidden tools.

### 2.1 File Deletions
Delete the following files and directories from the repository:
1. `app/features/screenshot/ops.py`
2. `app/features/screenshot/__init__.py`
3. Remove directory: `app/features/screenshot/`
4. `app/web/api/tool_screenshot.py`
5. `app/web/js/tools/screenshot.js`
6. `app/web/assets/home/screenshot.png`
7. `tests/ui/scenarios/screenshot.py`
8. `app/features/hash/ops.py`
9. `app/features/hash/__init__.py`
10. Remove directory: `app/features/hash/`
11. `app/web/api/tool_hash.py`
12. `app/web/js/tools/hash.js`
13. `app/web/assets/home/hash.png`
14. `app/web/assets/home/hash.svg`
15. `tests/ui/scenarios/hash.py`
16. `tests/test_hash_ops.py` (if present)

### 2.2 Make Archive Operations Self-Contained
In `app/features/archive/ops.py`:
- Remove any import from `app.features.hash`.
- Add self-contained standard library SHA-256 calculation:
```python
import hashlib

def compute_file_sha256(path: str) -> str:
    # Compute SHA-256 digest of file for archive verification.
    hasher = hashlib.sha256()
    with open(path, "rb") as stream:
        while chunk := stream.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()
```

### 2.3 Backend API Mixin Cleanups
1. In `app/web/api/__init__.py`:
   - Delete `from app.web.api.tool_screenshot import ScreenshotApiMixin`
   - Delete `from app.web.api.tool_hash import HashApiMixin`
   - In `class WebApi(...)`, delete `ScreenshotApiMixin` and `HashApiMixin`.
2. In `app/core/home_apps.py`:
   - Delete `'screenshot'` and `'hash'` dictionaries from the catalog list.
3. In `tests/test_api_contract.py`:
   - Remove `ScreenshotApiMixin` and `HashApiMixin` from imports and from `ALL_MIXINS`.

### 2.4 Frontend Shell Cleanups
1. In `app/web/index.html`:
   - Delete `<script src="js/tools/screenshot.js"></script>`
   - Delete `<script src="js/tools/hash.js"></script>`
2. In `app/web/js/core/router.js`:
   - In `DEFAULT_SECTIONS`, remove `{ id: "screenshot", visible: true }` and `{ id: "hash", visible: true }`.
3. In `app/web/js/home.js`:
   - In `DEFAULT_APPS`, delete entries for `screenshot` and `hash`.

### 2.5 Parity Inventories and Build Specifications
1. In `tests/parity/ops_inventory.json`:
   - Delete keys `"app/features/screenshot/ops.py"` and `"app/features/hash/ops.py"`.
2. In `tests/parity/feature_map.json`:
   - Delete keys `"screenshot"` and `"hash"`.
3. In `tests/parity/allowlist.json` and `tests/parity/tab_calls.json`:
   - Delete references to `screenshot` and `hash`.
4. In `FOSSEverything.spec` and `scripts/build_executable.py`:
   - Remove references to `tool_screenshot`, `tool_hash`, `screenshot.js`, and `hash.js`.

---

## Section 3: Shell, Topbar, Settings, Zoom Engine & Navigation Overhaul

### 3.1 Single Settings Access Point
1. In `app/web/js/core/router.js`:
   - Locate `renderSidebar()`.
   - Remove lines creating `settingsItem` and `footer`:
     ```javascript
     // DELETE THIS BLOCK:
     var settingsItem = window.FOSS.dom.el("button", {
       className: "nav-item sidebar-bottom ...",
       "data-testid": "nav-settings",
       ...
     });
     var footer = window.FOSS.dom.el("div", { className: "sidebar-footer" }, [settingsItem]);
     sidebar.appendChild(footer);
     ```
   - Do not append any bottom footer to `sidebar`.
2. In `renderTopbar()`:
   - Ensure `topbar-settings-btn` remains the sole access point to Settings.

### 3.2 Remove First-Run Startup Context Menu Popup
1. In `app/web/js/app.js`:
   - Locate `init()` (around line 23).
   - Delete:
     ```javascript
     if (!window.FOSS.store.get("first_run_done", false)) {
       showFirstRunWelcome();
     }
     ```
   - Delete the entire `function showFirstRunWelcome() { ... }` block (lines 31-43).
   - Context menu registration remains accessible in Settings under Windows Shell integration.

### 3.3 Zoom Slider Freakout Fix and Viewport Containment
1. In `app/web/js/settings.js:renderScaleCustomizer(panel)`:
   - Rewrite the slider event handling:
     ```javascript
     var scaleDebounceTimer = null;
     var scaleInput = window.FOSS.dom.el("input", {
       type: "range",
       id: "settings-scale-slider",
       min: "0.50",
       max: "2.50",
       step: "0.05",
       value: String(currentScale),
       "data-testid": "settings-ui-scale-slider",
       "aria-label": "UI font and scale factor",
       onInput: function (e) {
         var val = parseFloat(e.target.value);
         scaleOutput.textContent = Math.round(val * 100) + "%";
         if (scaleDebounceTimer) clearTimeout(scaleDebounceTimer);
         scaleDebounceTimer = setTimeout(function () {
           window.FOSS.theme.setScale(val);
         }, 150);
       },
       onChange: function (e) {
         if (scaleDebounceTimer) clearTimeout(scaleDebounceTimer);
         var val = parseFloat(e.target.value);
         window.FOSS.theme.setScale(val);
       }
     });
     ```
   - Add step up and step down buttons next to the slider:
     - `settings-scale-step-down`: decrement by `0.05`
     - `settings-scale-step-up`: increment by `0.05`
2. Global zoom via `Ctrl + Wheel` in `app/web/js/core/shortcuts.js`:
   - Ensure `window.addEventListener("wheel", ...)` checks `e.ctrlKey` and calls `window.FOSS.theme.stepScale(e.deltaY < 0 ? 1 : -1)`.
   - Ensure the zoom HUD overlay indicates the current zoom level and fades out after `1.2` seconds.
3. Viewport Containment in `app/web/css/layout.css`:
   - Ensure `.app`, `.main`, `.scroll-main`, `.page`, and `.settings-page` have:
     ```css
     min-height: 0;
     min-width: 0;
     overflow-y: auto;
     overflow-x: auto;
     ```
   - Ensure `.topbar` has `position: sticky; top: 0; z-index: var(--z-topbar); flex-shrink: 0;` so it remains reachable at all scales up to `2.50`.

### 3.4 Sidebar Customizer Redesign
1. In `app/web/js/settings.js:renderSidebarCustomizer(panel)`:
   - Begin function immediately with `panel.innerHTML = "";`.
   - Remove the `<select class="select">` ("Move to...") dropdown.
   - Make each app row within a section draggable:
     - Set `draggable: "true"`.
     - On `dragstart`: store `{ type: "app", appId: item.id, fromSec: sec.id }` in `e.dataTransfer`.
     - On drag over another section or app row: apply `.drop-target-above`.
     - On `drop`: reorder within the section or move to another section.
   - Render mini SVG icons matching the sidebar:
     ```javascript
     var iconEl = window.FOSS.icons.el(tool ? tool.icon || "file" : "file", 18);
     ```
   - Add an 'Add App to Section' dropdown or picker on each section card so users can pin an app to multiple sections.
2. In `app/web/js/core/router.js:resolveSidebarLayout()`:
   - Remove `seen[it.id] = true` filtering so that apps can exist in multiple sections simultaneously.

### 3.5 Home Category Filter Chips Synced with Sidebar Sections & Favorites at Top
1. In `app/web/js/core/router.js:DEFAULT_SECTIONS`:
   - Position `Favorites` as the first section at the very top:
     ```javascript
     {
       id: "sec_favorites",
       name: "Favorites",
       collapsed: false,
       items: [
         { id: "pdf", visible: true },
         { id: "converter", visible: true },
         { id: "ocr", visible: true }
       ]
     }
     ```
2. In `app/web/js/home.js:render()`:
   - Generate filter chips dynamically from `window.FOSS.router.resolveSidebarLayout().sections`:
     ```javascript
     var layout = window.FOSS.router.resolveSidebarLayout();
     var sectionNames = (layout.sections || [])
       .filter(function (s) { return (s.items || []).some(function (it) { return it.visible; }); })
       .map(function (s) { return s.name; });
     var cats = ["All"].concat(sectionNames);
     ```
   - Clicking a filter chip filters the Home grid to display tools assigned to that section.

### 3.6 Interactive Keyboard Shortcuts Editor
1. In `app/web/js/core/shortcuts.js`:
   - Define default shortcut map:
     ```javascript
     var DEFAULT_KEYMAP = {
       "open_palette": { label: "Command Palette", key: "k", ctrl: true, alt: false, shift: false, display: "Ctrl+K" },
       "go_home": { label: "Navigate to Home", key: "Home", ctrl: false, alt: true, shift: false, display: "Alt+Home" },
       "open_settings": { label: "Open Settings", key: "s", ctrl: false, alt: true, shift: false, display: "Alt+S" },
       "toggle_fullscreen": { label: "Toggle Fullscreen", key: "F11", ctrl: false, alt: false, shift: false, display: "F11" },
       "zoom_in": { label: "Zoom In", key: "=", ctrl: true, alt: false, shift: false, display: "Ctrl+=" },
       "zoom_out": { label: "Zoom Out", key: "-", ctrl: true, alt: false, shift: false, display: "Ctrl+-" },
       "zoom_reset": { label: "Reset Zoom", key: "0", ctrl: true, alt: false, shift: false, display: "Ctrl+0" }
     };
     ```
   - Load keymap from `window.FOSS.store.get("custom_keybindings", DEFAULT_KEYMAP)`.
   - Dispatch matching actions dynamically in `handleKeyDown`.
2. In `app/web/js/settings.js:renderKeybindings(panel)`:
   - Render an interactive table where each shortcut row features:
     - Action name
     - Key badge (`<kbd class='kbd'>`)
     - Rebind button (`data-testid='settings-rebind-<action>'`)
     - Clear button
   - Clicking Rebind enters listening mode, captures the next key combination, updates the binding, and persists to `window.FOSS.store.set("custom_keybindings", keymap)`.
   - Provide a "Reset to Defaults" button (`data-testid="settings-reset-shortcuts-btn"`).

---

## Section 4: Universal Component Hardening, DOM Utilities & Space Expansion

### 4.1 Component Wrapper Unpacking in `dom.js`
1. Open `app/web/js/core/dom.js`.
2. Update children appending logic:
   ```javascript
   if (children) {
     if (!Array.isArray(children)) children = [children];
     for (var i = 0; i < children.length; i++) {
       var child = children[i];
       if (!child) continue;
       if (typeof child === "string" || typeof child === "number") {
         element.appendChild(document.createTextNode(String(child)));
       } else if (child.nodeType) {
         element.appendChild(child);
       } else if (child.el && child.el.nodeType) {
         element.appendChild(child.el);
       }
     }
   }
   ```
3. Add `window.FOSS.dom.append(parent, child)` helper.
4. In `app/web/js/tools/converter.js:180`, change `contextualOptionsContainer.appendChild(qualitySlider)` to `contextualOptionsContainer.appendChild(qualitySlider.el)`.

### 4.2 Full Space Expansion for Monospace Textboxes
1. In `app/web/css/tools.css`:
   ```css
   .code-editor-fill {
     display: flex;
     flex-direction: column;
     flex: 1 1 0%;
     min-height: 0;
     height: 100%;
     width: 100%;
   }
   .code-editor-fill textarea.code-editor {
     flex: 1 1 0%;
     min-height: 20rem;
     height: 100%;
     width: 100%;
     resize: vertical;
     box-sizing: border-box;
   }
   ```
2. In `app/web/js/tools/data.js`, `encoding.js`, and `text_tools.js`:
   - Pass `fillHeight: true` to every `codeEditor` instantiation.
   - Set intermediate split containers to `height: 100%; flex: 1 1 0%; min-height: 0;`.

### 4.3 Universal Panel Resizing in `resizer.js`
1. In `app/web/js/core/resizer.js`:
   - During active split divider drag, set `pointer-events: none` on all `canvas` and `iframe` elements.
   - Restore pointer events on mouseup.
   - Clamp dragged widths between `15rem` and `80%` of container width.

---

## Section 5: Tool-by-Tool Detailed UX Friction Audit & Concrete Implementation Plan

There are exactly 21 canonical tools in the application. Every coding agent must implement the exact specifications below for each tool.

### Tool 1: PDF Tools (`pdf`)
- **Source Files**: `app/web/js/tools/pdf.js`, `app/features/pdf/ops.py`, `app/web/api/tool_pdf.py`.
- **UI/UX Friction Analysis**:
  1. The Combine PDF tool relied on clunky 'Move Up' and 'Move Down' buttons that required dozens of clicks to reorder pages across multi-page documents.
  2. The PDF Organizer existed as a redundant, separate interface when its page manipulation capabilities naturally belong directly inside the Combine/Merge workflow.
  3. Imported multi-page documents were flattened immediately into disconnected page lists, losing document boundary context.
  4. The Splitter interface had a redundant 'single page' mode that duplicated the functionality of the page range mode (which handles single pages by entering '1').
  5. The Splitter contained a blank, non-functional tool tab that caused visual confusion.
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/pdf.js:renderCombineOrganize`:
     - Eliminate all 'Move Up' and 'Move Down' buttons. Replace entirely with HTML5 drag-and-drop cards.
     - When a PDF is imported, wrap it by default into a collapsible Document Group Card showing the file name, page count, and an 'Ungroup into Pages' button (`data-testid='pdf-ungroup-btn'`).
     - When ungrouped, render individual page thumbnail cards with drag handles (`window.FOSS.icons.el('grip', 14)`).
     - Allow arbitrary grouping: provide a 'Group Selected Pages' button and allow naming/renaming custom groups.
     - On each page card, include direct action buttons:
       - Rotate 90 deg clockwise (`data-testid='pdf-page-rotate'`, calls `pdf_rotate_pages`).
       - Delete page (`data-testid='pdf-page-delete'`).
       - Duplicate page (`data-testid='pdf-page-duplicate'`).
     - Implement drag reordering that works both between groups and within groups, preserving overall page sequence.
  2. In `renderSplit`:
     - Remove the 'Single Page' tab/mode.
     - Remove the blank tool tab from router tabs registration.
     - Ensure the Page Range input (`data-testid='pdf-split-range-input'`) supports ranges and discrete pages (such as `1-5, 8, 11-14`).
  3. Universal Save Path Rule:
     - Always call `window.FOSS.api('select_save_path', { title: 'Save Combined PDF', default_name: 'combined.pdf', file_types: [{ name: 'PDF', extensions: ['pdf'] }] })`.

### Tool 2: OCR Studio (`ocr`)
- **Source Files**: `app/web/js/tools/ocr.js`, `app/features/ocr/ops.py`, `app/web/api/tool_ocr.py`.
- **UI/UX Friction Analysis**:
  1. The tool indiscriminately ran optical character recognition over entire PDFs, overwriting existing vector text streams in documents that were already digitally searchable.
  2. Users could not specify page ranges or discrete lists of pages to process.
  3. Batch OCR accepted only individual file selections, lacking the ability to select an entire folder recursively.
  4. Tab headers and section titles displayed unprofessional lowercase typography (such as 'batch ocr' and 'ocr preview').
  5. The preview canvas was constrained to a small fixed height (`max-height: 260px`), making text illegible without external tools.
- **Step-by-Step Implementation Instructions**:
  1. In `app/features/ocr/ops.py:create_searchable_pdf`:
     - Inspect each page text stream using `page.get_text().strip()`. If length exceeds 15 characters and `force_reocr` is False, preserve the existing text layer and skip OCR rasterization on that page.
     - Add a `force_reocr` boolean parameter (default False) exposed to the frontend as a checkbox (`data-testid='ocr-force-reocr-check'`).
     - Implement page range parsing via `parse_page_selection(pages_str, total_pages)` supporting `all`, ranges (`1-5`), and lists (`1, 3, 7`).
  2. In `app/web/js/tools/ocr.js`:
     - Capitalize all interface labels: change 'batch ocr' to 'Batch OCR', 'document ocr' to 'Document OCR', and 'ocr preview' to 'OCR Preview'.
     - In Batch OCR, add an 'Add Folder...' button (`data-testid='ocr-batch-add-folder-btn'`) calling `select_folder` and expanding all supported image and PDF files.
     - Expand the preview canvas container to `min-height: 26rem; max-height: 40rem;` and provide zoom in, zoom out, and reset zoom controls.
     - Always prompt `select_save_path` with `.pdf` or `.txt` filter before writing files.

### Tool 3: Markdown Studio (`markdown`)
- **Source Files**: `app/web/js/tools/markdown.js`, `app/features/markdown/ops.py`, `app/web/api/tool_markdown.py`.
- **UI/UX Friction Analysis**:
  1. Users had to toggle between 'Editor' and 'Preview' tabs or switch modes manually, breaking immediate visual feedback during authoring.
  2. The parser flavor was hardcoded without allowing the user to select between GitHub Flavored Markdown, CommonMark, or strict standard Markdown.
  3. Advanced syntax such as nested sub-bullets, task list checkboxes (`- [x]`), syntax-highlighted code blocks, tables, and KaTeX math formulas were inconsistently rendered.
  4. The editor textarea was vertically constrained instead of filling the full window height.
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/markdown.js`:
     - Remove the mode toggle tabs. Enforce a permanent, side-by-side split workbench layout: left pane contains the raw Markdown editor, right pane contains the live rendered preview.
     - Add a Parser Flavor dropdown (`data-testid='markdown-flavor-select'`):
       - `GitHub Flavored Markdown (Default)`
       - `CommonMark`
       - `Strict Standard Markdown`
     - Default parser to GitHub Flavored Markdown (`marked.js` with `gfm: true, breaks: true`).
     - Support full task list checkbox interactions, tables, sub-bullets, blockquotes, and KaTeX math formulas.
     - Configure both panes with `height: 100%; flex: 1 1 0%; min-height: 0;` using `.code-editor-fill`.
     - Prompt `select_save_path` with `.md` or `.html` filters.

### Tool 4: Resume Studio (`resume`)
- **Source Files**: `app/web/js/tools/resume.js`, `app/features/resume/ops.py`, `app/web/api/tool_resume.py`.
- **UI/UX Friction Analysis**:
  1. The exported `.docx` document severely diverged from the canonical target specification at `C:\Users\Josh\Downloads\spacex_gnc_resume.pdf`.
  2. Bullet paragraphs applied `style='List Bullet'` while simultaneously setting `paragraph_format.left_indent`, creating doubled margins, misplaced bullet glyphs, and awkward text wrapping.
  3. Dates were aligned using 4 literal spaces instead of right-aligned tab stops, causing date text to collide with titles or wrap onto new lines.
  4. Section headers lacked the required 2.0pt solid black bottom dividing line.
  5. The document spilled over onto a second page instead of fitting strictly onto 1 page.
  6. The live preview sheet was rendered too small (`max-width: 46rem`), making typography hard to review.
  7. The save dialog did not automatically append `.docx` if omitted by the user.
- **Step-by-Step Implementation Instructions**:
  1. In `app/features/resume/ops.py:export_docx`:
     - **Page Setup**: Page width `8.5 in`, height `11.0 in`. Left margin `0.75 in` (`Pt(54)`), right margin `0.75 in`, top margin `0.65 in`, bottom margin `0.65 in`. Printable width `7.0 in` (`Pt(504)`).
     - **Normal Style**: Configure font `Calibri`, size `10.5 pt`, tight single line spacing `1.0`, `space_before = Pt(0)`, `space_after = Pt(0)`.
     - **Header Name**: Centered, `20 pt Bold`, Calibri, black.
     - **Contact Subtitle**: Centered, `9.5 pt Regular`, items joined with ` | `.
     - **Section Dividers**: `11 pt Bold`, Calibri, uppercase, `space_before = Pt(6)`, `space_after = Pt(2)`. Add bottom border XML: `<w:pBdr><w:bottom w:val='single' w:sz='16' w:space='2' w:color='000000'/></w:pBdr>`.
     - **Titles and Dates**: Left-aligned job title and organization. Set right-aligned tab stop at `Inches(7.0)` (`Pt(504)`). Place date string after `\t` in bold.
     - **Bullet Points**: Do NOT use `style='List Bullet'`. Use style `'Normal'` with:
       - `left_indent = Pt(9.0)`
       - `first_line_indent = Pt(-9.0)`
       - Tab stop at `Pt(9.0)`
       - Explicit bullet character `\u25cf\t` in Arial 8.5pt.
       - Content run in Calibri 10.5pt.
       - Line spacing `1.0`, `space_before = Pt(0)`, `space_after = Pt(1.5)`.
     - Strictly guarantee all content fits onto exactly 1 page.
  2. In `app/web/js/tools/resume.js`:
     - Enforce `default_name: 'resume.docx'` and filter `*.docx` in save dialog.
     - Expand live preview sheet to `max-width: 58rem;` with zoom scale controls.

### Tool 5: Image Studio (`images`)
- **Source Files**: `app/web/js/tools/images.js`, `app/features/image/ops.py`, `app/web/api/tool_image.py`.
- **UI/UX Friction Analysis**:
  1. AI background removal models were saved unpredictably across multiple directories without a unified cache location.
  2. Users had no visibility into model download sizes or which models were already present on disk versus requiring download.
  3. File format conversion did not prompt for save destination.
- **Step-by-Step Implementation Instructions**:
  1. In `app/features/image/ops.py`:
     - Store all Rembg ONNX models in a single unified directory at `~/.u2net/`.
     - Provide catalog information for each model:
       - `u2net` (Standard General, ~176 MB)
       - `u2netp` (Lightweight Mobile, ~4 MB)
       - `u2net_human_seg` (Human Portrait Segmentation, ~176 MB)
       - `isnet-general-use` (High Precision Object Cutout, ~174 MB)
     - Implement `image_get_rembg_models` returning download size, local cache status, and description for each model.
  2. In `app/web/js/tools/images.js`:
     - Render a model selection card featuring status badges (`Downloaded` in green, `Not Downloaded` in amber) and file sizes.
     - Prompt `select_save_path` before starting transformations or background removal.

### Tool 6: Photo Collage (`collage`)
- **Source Files**: `app/web/js/tools/collage.js`, `app/features/collage/ops.py`, `app/web/api/tool_collage.py`.
- **UI/UX Friction Analysis**:
  1. The application silently saved output collage files directly to the input directory without prompting the user for destination or name.
  2. Freeform layouts lacked layer stacking controls, preventing users from layering images on top of one another or adjusting z-index.
  3. Users could not adjust layer opacity or toggle layer visibility.
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/collage.js:handleSave`:
     - Delete the silent path construction logic.
     - Always call `window.FOSS.api('select_save_path', { title: 'Save Collage', default_name: 'collage.png', file_types: [{ name: 'PNG Image', extensions: ['png'] }, { name: 'JPEG Image', extensions: ['jpg', 'jpeg'] }] })`.
  2. In Freeform Mode:
     - Implement an active layer stack editor where each imported image is a draggable layer card.
     - Add layer controls: Bring to Front (`data-testid='collage-layer-front'`), Send to Back (`data-testid='collage-layer-back'`), Move Up, Move Down.
     - Provide an opacity slider (`0` to `100%`) and visibility toggle per layer.

### Tool 7: Color Palette (`palette`)
- **Source Files**: `app/web/js/tools/palette.js`, `app/features/palette/ops.py`, `app/web/api/tool_palette.py`.
- **UI/UX Friction Analysis**:
  1. The layout contained massive dead whitespace caused by undefined CSS grid classes (`grid-cols-2`).
  2. Swatch cards lacked copy buttons for color values in alternate color spaces (RGB and HSL).
  3. Section headers used uncapitalized typography.
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/palette.js`:
     - Replace invalid grid classes with `row gap-2 flex-wrap`.
     - Capitalize all headers: 'Dominant Color Palette', 'Color Harmonizer', and 'Image Extraction'.
     - On each color swatch card, render one-click copy buttons for HEX (`#RRGGBB`), RGB (`rgb(r, g, b)`), and HSL (`hsl(h, s%, l%)`).
     - Display luminance and contrast ratios against white and black for accessibility compliance.

### Tool 8: 3D Model Studio (`model3d`)
- **Source Files**: `app/web/js/tools/model3d.js`, `app/features/model3d/ops.py`, `app/web/api/tool_model3d.py`.
- **UI/UX Friction Analysis**:
  1. The router registered dummy 'scale' and 'measure' tabs that simply redirected back to the inspector, confusing users.
  2. The sidebar containing mesh properties and transformations had fixed heights that cut off content on standard resolutions.
  3. Dragging the sidebar resizer failed because the underlying WebGL canvas intercepted pointer events.
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/model3d.js`:
     - Remove `scale` and `measure` tabs from router registration. Retain exactly 3 tabs:
       1. `inspector` ('Inspector & Tools')
       2. `cut` ('Cut Plane')
       3. `export` ('Export & Convert')
     - Integrate scale transformation inputs (uniform scale, X/Y/Z factors) and point-to-point measurement tools directly into the Inspector sidebar pane.
  2. In `app/web/css/tools.css`:
     - Ensure `.model3d-sidebar-pane` has `overflow-y: auto; max-height: 100%; min-width: 0;` so geometry properties are never hidden.
     - During resizer drag, set `pointer-events: none` on the Three.js canvas element.

### Tool 9: Audio & Video Studio (`media`)
- **Source Files**: `app/web/js/tools/media.js`, `app/features/media/ops.py`, `app/web/api/tool_media.py`.
- **UI/UX Friction Analysis**:
  1. The media player preview, scrub controls, and timecode readouts were crammed horizontally, causing overflow on smaller viewports.
  2. Users lacked intuitive buttons to extract audio tracks directly to MP3 or generate subtitle transcriptions.
  3. Save paths were guessed automatically without prompting the user.
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/media.js`:
     - Stack preview video player and audio waveform vertically above parameter controls.
     - Provide dedicated action cards:
       - Trim Video (`data-testid='media-trim-btn'`)
       - Extract Audio to MP3 (`data-testid='media-extract-audio-btn'`)
       - Transcribe Subtitles (`data-testid='media-transcribe-btn'`)
       - Create Animated GIF (`data-testid='media-create-gif-btn'`)
     - Always invoke `select_save_path` before dispatching FFmpeg encoding operations.

### Tool 10: Playlist Porter (`playlist`)
- **Source Files**: `app/web/js/tools/playlist.js`, `app/features/playlist/ops.py`, `app/web/api/tool_playlist.py`.
- **UI/UX Friction Analysis**:
  1. When remote playlist URLs failed to download due to network issues, the UI hung in an indeterminate loading state without error toasts.
  2. Track tables lacked horizontal scrolling wrappers, overflowing on narrow screens.
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/playlist.js`:
     - Wrap track listing in `.table-wrap.scroll-x` container.
     - Catch fetch errors and display a toast notification with the exact failure cause.
     - Prompt `select_save_path` when exporting to M3U8, CSV, or JSON.

### Tool 11: Universal File Converter (`converter`)
- **Source Files**: `app/web/js/tools/converter.js`, `app/features/converter/ops.py`, `app/web/api/tool_converter.py`.
- **UI/UX Friction Analysis**:
  1. Selecting JPEG or WEBP formats threw `TypeError: Failed to execute 'appendChild' on 'Node': parameter 1 is not of type 'Node'` because `qualitySlider` was passed as an object instead of its DOM element.
  2. Batch converter supported adding files one by one, but had no option to select an entire folder.
  3. Office document conversions were missing from the universal converter.
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/converter.js:180`:
     - Fix the `appendChild` call by passing `qualitySlider.el`:
       ```javascript
       if (["JPEG", "JPG", "WEBP"].indexOf(fmt) >= 0) {
         contextualOptionsContainer.appendChild(qualitySlider.el);
       }
       ```
  2. In Batch Converter:
     - Add an 'Add Folder...' button (`data-testid='converter-batch-add-folder-btn'`).
  3. In `app/features/converter/ops.py`:
     - Support DOCX to PDF, XLSX to CSV/PDF, and PPTX to PDF.

### Tool 12: File Compressor (`compressor`)
- **Source Files**: `app/web/js/tools/compressor.js`, `app/features/compressor/ops.py`, `app/web/api/tool_compressor.py`.
- **UI/UX Friction Analysis**:
  1. Inconsistent compression profiles across file types.
  2. Users could not see estimated size savings prior to compression.
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/compressor.js`:
     - Standardize profile presets: 'Low (Fast)', 'Medium (Balanced)', 'High (Maximum Compression)'.
     - Render estimated compression ratio readout before job execution.
     - Prompt `select_save_path` before processing.

### Tool 13: Archive Studio (`archive`)
- **Source Files**: `app/web/js/tools/archive.js`, `app/features/archive/ops.py`, `app/web/api/tool_archive.py`.
- **UI/UX Friction Analysis**:
  1. The UI included redundant backup and protect stubs.
  2. Archive verification depended on an external hash module.
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/archive.js`:
     - Restructure into 3 clear tabs:
       1. `create` (Create ZIP, TAR, TAR.GZ)
       2. `extract` (Safe extraction with path sanitization against zip-slip)
       3. `inspect` (Table of contents viewer)
  2. In `app/features/archive/ops.py`:
     - Use standard library `hashlib.sha256` for integrity checks.
     - Prompt `select_save_path` when creating archives.

### Tool 14: Batch Renamer (`renamer`)
- **Source Files**: `app/web/js/tools/renamer.js`, `app/features/renamer/ops.py`, `app/web/api/tool_renamer.py`.
- **UI/UX Friction Analysis**:
  1. Simple rename operations forced users to craft complex regex statements.
  2. Accidental renames were irreversible without manual recovery.
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/renamer.js`:
     - Provide visual rule blocks: Replace Text, Add Prefix/Suffix, Number Sequence, Change Case, and Date Stamp.
     - Render a live before-and-after preview table flagging file collisions.
     - Add a one-click Undo button (`data-testid='renamer-undo-btn'`) that reverses the last rename batch.

### Tool 15: Metadata Stripper (`metadata`)
- **Source Files**: `app/web/js/tools/metadata.js`, `app/features/metadata/ops.py`, `app/web/api/tool_metadata.py`.
- **UI/UX Friction Analysis**:
  1. Office document metadata sanitization was missing from the tool.
- **Step-by-Step Implementation Instructions**:
  1. In `app/features/metadata/ops.py`:
     - Support DOCX, XLSX, and PPTX metadata sanitization (author, company, revision notes, comments) in addition to image EXIF and PDF metadata.
  2. In `app/web/js/tools/metadata.js`:
     - Display sanitized fields in the preview table and prompt `select_save_path`.

### Tool 16: QR and Barcodes (`qr`)
- **Source Files**: `app/web/js/tools/qr.js`, `app/features/qr/ops.py`, `app/web/api/tool_qr.py`.
- **UI/UX Friction Analysis**:
  1. Generator inputs wrapped awkwardly on standard desktop displays.
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/qr.js`:
     - Cleanly segment generator tabs: URL, Plain Text, Contact vCard, and Wi-Fi Network.
     - Support 1D barcode generation (Code128, EAN13) and webcam/file decoding.
     - Prompt `select_save_path` for PNG and SVG exports.

### Tool 17: Network Traffic Monitor (`network_monitor`)
- **Source Files**: `app/web/js/tools/network_monitor.js`, `app/features/network_monitor/resolver.py`, `app/features/network_monitor/db.py`, `app/web/api/tool_network_monitor.py`.
- **UI/UX Friction Analysis**:
  1. Connections only showed raw IP addresses and process names without identifying the software category or trustworthiness rating.
  2. Users could not easily distinguish legitimate operating system traffic from external or unverified connections.
- **Step-by-Step Implementation Instructions**:
  1. In `app/features/network_monitor/resolver.py`:
     - Implement `classify_connection_trust(process_name, remote_ip, remote_domain)`:
       - Windows System (`svchost.exe`, `lsass.exe`, `explorer.exe`) -> Identity: `Windows System`, Trust: `Trusted System`.
       - Web Browser (`msedge.exe`, `chrome.exe`, `firefox.exe`) -> Identity: `Web Browser`, Trust: `Trusted App`.
       - Developer Tool (`python.exe`, `node.exe`, `git.exe`) -> Identity: `Developer Tool`, Trust: `Local Dev`.
       - Local Subnet (`127.`, `10.`, `192.168.`, `::1`) -> Identity: `Local Subnet`, Trust: `Local Safe`.
       - Verified CDN (Microsoft, Google, GitHub, Cloudflare) -> Identity: `Verified CDN`, Trust: `Trusted Service`.
       - Unknown external IP -> Identity: `External IP`, Trust: `Unverified`.
  2. In `app/web/js/tools/network_monitor.js`:
     - Add 'Source Identity' and 'Trust Level' columns with colored badge indicators to live and history tables.

### Tool 18: Unit Converter (`unit_converter`)
- **Source Files**: `app/web/js/tools/unit_converter.js`, `app/features/unit_converter/ops.py`, `app/web/api/tool_unit_converter.py`.
- **UI/UX Friction Analysis**:
  1. The layout was inverted: configuration options were placed at the top, pushing the primary input value, From/To units, and Convert button to the bottom.
  2. The interface exposed internal backend terminology ('Pint-backed dimensional analysis').
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/unit_converter.js`:
     - Place the primary conversion controls at the very top:
       - Input Value, From Unit, Swap button, To Unit, Convert button, and Result banner.
     - Move physical dimension, prefix multiplier, notation, and precision to the bottom card.
     - Eradicate every mention of 'Pint' across the UI and documentation.

### Tool 19: Data Studio (`data`)
- **Source Files**: `app/web/js/tools/data.js`, `app/features/data/ops.py`, `app/web/api/tool_data.py`.
- **UI/UX Friction Analysis**:
  1. Monospace code editors were rendered in tiny fixed-height textboxes with extensive wasted whitespace.
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/data.js`:
     - Instantiate all code editors with `fillHeight: true`.
     - Apply `.code-editor-fill` to parent containers so editors expand to 100% width and height.
     - Support JSON, CSV, YAML, TOML, and SQL conversions with save path prompt.

### Tool 20: Text Tools (`text_tools`)
- **Source Files**: `app/web/js/tools/text_tools.js`, `app/features/text_tools/ops.py`, `app/web/api/tool_text_tools.py`.
- **UI/UX Friction Analysis**:
  1. Clicking `PascalCase` failed with `Unsupported case mode: pascal` because backend ops and API handlers lacked support.
  2. Diff viewer and text transformation textareas were vertically cramped.
- **Step-by-Step Implementation Instructions**:
  1. In `app/features/text_tools/ops.py`:
     - Add `to_pascal_case(text: str) -> str` capitalizing each word.
  2. In `app/web/api/tool_text_tools.py:text_tools_case`:
     - Support `pascal` and `pascalcase` modes.
  3. Expand diff viewer and word counter textareas to 100% height (`fillHeight: true`).

### Tool 21: Encoding / Decoding (`encoding`)
- **Source Files**: `app/web/js/tools/encoding.js`, `app/features/encoding/ops.py`, `app/web/api/tool_encoding.py`.
- **UI/UX Friction Analysis**:
  1. Input and output textareas were confined to small boxes with surrounding dead whitespace.
- **Step-by-Step Implementation Instructions**:
  1. In `app/web/js/tools/encoding.js`:
     - Pass `fillHeight: true` to input and output code editors.
     - Support Base64, Hex, URL, HTML entities, and binary encodings.
     - Prompt `select_save_path` when saving encoded or decoded payloads.

---

## Section 6: Comprehensive End-to-End GUI Walkthrough Test Suite

The user explicitly demands that EVERY tool in FOSSEverything has a full automated GUI walkthrough test. These tests must click every button from start to finish via Playwright, interact with all options, and verify the resulting saved output file on disk. Pure function calls are forbidden for these scenario tests.

### 6.1 Test Environment Architecture and pywebview Mocking
1. The test runner uses Playwright with headless Chromium/Edge via `tests/ui/harness.py`.
2. Real backend execution is wired through `WebApi` with pywebview bridge emulation (`window.pywebview.api`).
3. File dialog prompts are answered deterministically by populating `api._dialog_answers = [chosen_path1, chosen_path2, ...]` before clicking UI buttons.
4. All test runs operate in an isolated temporary directory created by pytest (`tmp_path`) to prevent polluting workspace files.

### 6.2 Test Fixtures Inventory (`tests/ui/_fixtures/`)
Ensure `tests/fixtures.py:make_fixtures` generates all necessary test assets:
- `sample.pdf`: Multi-page text PDF for PDF and compression tools.
- `scan.pdf`: Rasterized image PDF for OCR text extraction tests.
- `sample.png` and `sample2.png`: RGBA test patterns for converter, collage, and palette.
- `sample.docx`: Microsoft Word document for converter and metadata stripping.
- `cube.stl`: 3D triangular mesh for 3D Model Studio tests.
- `clip.mp4`: Short video stream with audio track for media tests.
- `tone.wav`: Audio waveform for media player tests.
- `data.json` and `data.csv`: Structured tables for Data Studio tests.
- `playlist.m3u8`: Playlist manifest for Playlist Porter tests.

### 6.3 Tool-by-Tool GUI Walkthrough Test Scenarios

#### Walkthrough 1: PDF Tools (`pdf`)
1. **Setup**: Queue `sample.pdf` and `out_combined.pdf` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('pdf', 'merge')`.
   - Click `[data-testid='pdf-merge-add-btn']` to import the PDF.
   - Click `[data-testid='pdf-ungroup-btn']` to expand document into individual pages.
   - Click `[data-testid='pdf-page-rotate']` on page 1 to rotate 90 degrees.
   - Click `[data-testid='pdf-page-duplicate']` on page 2.
   - Click `[data-testid='pdf-merge-save-btn']` to trigger save.
3. **Assertion**:
   - Verify `out_combined.pdf` exists on disk.
   - Verify output file size is greater than 0 bytes and readable by `pymupdf.open()`.

#### Walkthrough 2: OCR Studio (`ocr`)
1. **Setup**: Queue `sample.png` and `out_ocr.pdf` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('ocr', 'document')`.
   - Click `[data-testid='ocr-choose-file']`.
   - Fill `[data-testid='ocr-page-range']` with `'1'`.
   - Click `[data-testid='ocr-run-btn']` to start recognition.
   - Wait for status indicator to show `'Complete'`.
   - Click `[data-testid='ocr-export-pdf-btn']`.
3. **Assertion**:
   - Verify `out_ocr.pdf` exists on disk and extracted text layer contains sample words.

#### Walkthrough 3: Markdown Studio (`markdown`)
1. **Setup**: Queue `out_doc.html` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('markdown', 'editor')`.
   - Fill editor textarea with `# SpaceX Mission\n\n- [x] Guidance\n- [ ] Propulsion`.
   - Select flavor `'GitHub Flavored Markdown'` in `[data-testid='markdown-flavor-select']`.
   - Verify preview container `[data-testid='markdown-preview']` renders `<h1>` and checkboxes.
   - Click `[data-testid='markdown-export-html-btn']`.
3. **Assertion**:
   - Verify `out_doc.html` exists on disk and contains rendered HTML.

#### Walkthrough 4: Resume Studio (`resume`)
1. **Setup**: Queue `out_resume.docx` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('resume', 'personal')`.
   - Fill `[data-testid='resume-name-input']` with `'ALEXANDER HAMILTON'`.
   - Fill `[data-testid='resume-title-input']` with `'GNC SYSTEMS ENGINEER'`.
   - Navigate to `window.FOSS.router.open('resume', 'preview')`.
   - Click `[data-testid='resume-export-docx-btn']`.
3. **Assertion**:
   - Verify `out_resume.docx` exists on disk.
   - Load document via `docx.Document(out_resume.docx)`.
   - Assert left and right margins equal `0.75 in` (`Inches(0.75)`).
   - Assert section headings have bottom border XML and bullets use Arial 8.5pt with hanging indent.

#### Walkthrough 5: Image Studio (`images`)
1. **Setup**: Queue `sample.png` and `out_transformed.webp` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('images', 'transform')`.
   - Click `[data-testid='images-choose-file']`.
   - Click `[data-testid='images-rotate-90-btn']`.
   - Select export format `'WEBP'`.
   - Click `[data-testid='images-save-btn']`.
3. **Assertion**:
   - Verify `out_transformed.webp` exists on disk.

#### Walkthrough 6: Photo Collage (`collage`)
1. **Setup**: Queue `[sample.png, sample2.png]` and `out_collage.png` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('collage', 'freeform')`.
   - Click `[data-testid='collage-add-images-btn']`.
   - Click `[data-testid='collage-layer-front']` on the first layer card.
   - Click `[data-testid='collage-export-btn']`.
3. **Assertion**:
   - Verify `out_collage.png` exists on disk with dimensions greater than 100x100.

#### Walkthrough 7: Color Palette (`palette`)
1. **Setup**: Queue `sample.png` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('palette', 'extract')`.
   - Click `[data-testid='palette-choose-file']`.
   - Wait for swatch grid `[data-testid='palette-swatch-grid']` to appear.
3. **Assertion**:
   - Assert at least 3 color swatches are rendered with copy buttons.

#### Walkthrough 8: 3D Model Studio (`model3d`)
1. **Setup**: Queue `cube.stl` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('model3d', 'inspector')`.
   - Click `[data-testid='model3d-load-file']`.
   - Verify exactly 3 tabs exist in router tabs (`inspector`, `cut`, `export`).
   - Verify scale input fields exist inside Inspector pane.
3. **Assertion**:
   - Assert WebGL canvas is mounted and status displays loaded vertex count.

#### Walkthrough 9: Audio & Video Studio (`media`)
1. **Setup**: Queue `clip.mp4` and `out_audio.mp3` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('media', 'audio')`.
   - Click `[data-testid='media-choose-file']`.
   - Click `[data-testid='media-extract-audio-btn']`.
3. **Assertion**:
   - Verify `out_audio.mp3` exists on disk.

#### Walkthrough 10: Playlist Porter (`playlist`)
1. **Setup**: Queue `playlist.m3u8` and `out_playlist.csv` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('playlist', 'import')`.
   - Click `[data-testid='playlist-choose-file']`.
   - Verify track table renders rows.
   - Click `[data-testid='playlist-export-csv-btn']`.
3. **Assertion**:
   - Verify `out_playlist.csv` exists on disk with header row.

#### Walkthrough 11: Universal File Converter (`converter`)
1. **Setup**: Queue `sample.png` and `out_converted.jpg` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('converter', 'single')`.
   - Click `[data-testid='converter-choose-file']`.
   - Select format `'JPEG'`.
   - Verify quality slider mounts cleanly without `appendChild` TypeError.
   - Click `[data-testid='converter-convert-btn']`.
3. **Assertion**:
   - Verify `out_converted.jpg` exists on disk.

#### Walkthrough 12: File Compressor (`compressor`)
1. **Setup**: Queue `sample.pdf` and `out_compressed.pdf` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('compressor', 'single')`.
   - Click `[data-testid='compressor-choose-file']`.
   - Click `[data-testid='compressor-run-btn']`.
3. **Assertion**:
   - Verify `out_compressed.pdf` exists on disk.

#### Walkthrough 13: Archive Studio (`archive`)
1. **Setup**: Queue `[sample.png, data.json]` and `out_archive.zip` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('archive', 'create')`.
   - Click `[data-testid='archive-add-files-btn']`.
   - Click `[data-testid='archive-create-btn']`.
3. **Assertion**:
   - Verify `out_archive.zip` exists on disk and contains added files.

#### Walkthrough 14: Batch Renamer (`renamer`)
1. **Setup**: Copy `sample.png` to `test_target.png` in temporary directory.
2. **Action**:
   - Queue `test_target.png` in `api._dialog_answers`.
   - Navigate via `window.FOSS.router.open('renamer', 'rules')`.
   - Click `[data-testid='renamer-add-files-btn']`.
   - Fill prefix input with `'renamed_'`.
   - Click `[data-testid='renamer-apply-btn']`.
   - Verify `renamed_test_target.png` exists on disk.
   - Click `[data-testid='renamer-undo-btn']`.
3. **Assertion**:
   - Assert test_target.png exists on disk and renamed_test_target.png does not exist.

#### Walkthrough 15: Metadata Stripper (`metadata`)
1. **Setup**: Queue `sample.docx` and `out_clean.docx` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('metadata', 'strip')`.
   - Click `[data-testid='metadata-choose-file']`.
   - Click `[data-testid='metadata-strip-btn']`.
3. **Assertion**:
   - Verify `out_clean.docx` exists on disk with author and revision properties empty.

#### Walkthrough 16: QR and Barcodes (`qr`)
1. **Setup**: Queue `out_qr.png` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('qr', 'generate')`.
   - Fill input `[data-testid='qr-text-input']` with `'https://foss.example.com'`.
   - Click `[data-testid='qr-save-png-btn']`.
3. **Assertion**:
   - Verify `out_qr.png` exists on disk.

#### Walkthrough 17: Network Traffic Monitor (`network_monitor`)
1. **Action**:
   - Navigate via `window.FOSS.router.open('network_monitor', 'live')`.
   - Verify table headers include `'Source Identity'` and `'Trust Level'`.
   - Verify trust badges render with valid classification colors.

#### Walkthrough 18: Unit Converter (`unit_converter`)
1. **Action**:
   - Navigate via `window.FOSS.router.open('unit_converter', 'standard')`.
   - Verify primary conversion card is at the top of the sidebar.
   - Fill value input with `'100'`.
   - Select from unit `'meter'`, to unit `'foot'`.
   - Click `[data-testid='unit_converter-convert-btn']`.
2. **Assertion**:
   - Assert result banner renders `'328.084'`.
   - Assert page text contains zero occurrences of the word `'Pint'`.

#### Walkthrough 19: Data Studio (`data`)
1. **Setup**: Queue `out_data.yaml` in `api._dialog_answers`.
2. **Action**:
   - Navigate via `window.FOSS.router.open('data', 'format')`.
   - Paste `'{"name": "Apollo", "active": true}'` into editor.
   - Click `[data-testid='data-convert-yaml-btn']`.
   - Click `[data-testid='data-save-btn']`.
3. **Assertion**:
   - Verify `out_data.yaml` exists on disk and contains valid YAML syntax.

#### Walkthrough 20: Text Tools (`text_tools`)
1. **Action**:
   - Navigate via `window.FOSS.router.open('text_tools', 'case')`.
   - Fill input textarea with `'guidance navigation and control'`.
   - Click `[data-testid='text_tools-pascal-btn']`.
2. **Assertion**:
   - Assert output textarea contains `'GuidanceNavigationAndControl'`.

#### Walkthrough 21: Encoding / Decoding (`encoding`)
1. **Action**:
   - Navigate via `window.FOSS.router.open('encoding', 'base64')`.
   - Fill input editor with `'Antigravity Rocket System'`.
   - Click `[data-testid='encoding-encode-btn']`.
   - Verify output editor contains Base64 encoded string.
   - Click `[data-testid='encoding-decode-btn']`.
2. **Assertion**:
   - Assert decoded output matches original input string.

---

## Section 7: Parity Inventory, Build Verification & Quality Gate

### 7.1 Parity Inventory Sync
Execute the parity audit tool:
```powershell
uv run --no-project python scripts/audit_ops_parity.py
```
Verify that:
1. Exactly 21 canonical tools are registered.
2. Zero references to `screenshot` or `hash` exist in `tests/parity/*.json`.

### 7.2 Full Test Suite Execution Gate
Run the complete automated test suite:
1. Static web invariants:
   ```powershell
   uv run --no-project --python "C:\Users\Josh\projects\FOSSEverything\.venv\Scripts\python.exe" python -m pytest tests/test_web_static.py
   ```
2. Backend API contract:
   ```powershell
   uv run --no-project --python "C:\Users\Josh\projects\FOSSEverything\.venv\Scripts\python.exe" python -m pytest tests/test_api_contract.py
   ```
3. End-to-end UI Playwright tests:
   ```powershell
   uv run --no-project --python "C:\Users\Josh\projects\FOSSEverything\.venv\Scripts\python.exe" python -m pytest tests/ui/test_ui_tools.py tests/ui/test_ui_shell.py
   ```
4. Strict linter audit:
   ```powershell
   uv run --no-project python C:\Users\Josh\projects\josh-ai-tools\scripts\claudemd_linter.py . --level strict
   ```
   Must output: `None. Lint clean.`.

### 7.3 Build Specifications and Packaging Audit
Verify `FOSSEverything.spec` and `scripts/build_executable.py` contain zero imports or data entries for `tool_screenshot`, `tool_hash`, `screenshot.js`, or `hash.js`.

---

## Section 8: Concrete Code Listings for Non-Reasoning Implementation Agents

This section provides the verbatim code changes required across critical modules so non-reasoning coding models can make surgical, error-free modifications.

### 8.1 Verbatim Code for `app/web/js/core/dom.js`
Replace the child-appending loop in `dom.el` (around lines 46-57):
```javascript
    if (children) {
      if (!Array.isArray(children)) children = [children];
      for (var i = 0; i < children.length; i++) {
        var child = children[i];
        if (!child) continue;
        if (typeof child === "string" || typeof child === "number") {
          element.appendChild(document.createTextNode(String(child)));
        } else if (child.nodeType) {
          element.appendChild(child);
        } else if (child.el && child.el.nodeType) {
          element.appendChild(child.el);
        }
      }
    }
```
And append to `window.FOSS.dom`:
```javascript
  window.FOSS.dom.append = function (parent, child) {
    if (!parent || !child) return;
    var node = child.nodeType ? child : (child.el && child.el.nodeType ? child.el : null);
    if (node) parent.appendChild(node);
  };
```

### 8.2 Verbatim Code for `app/web/js/tools/converter.js`
Locate line 180 in `updateContextualOptions()`:
```javascript
      if (["JPEG", "JPG", "WEBP"].indexOf(fmt) >= 0) {
        contextualOptionsContainer.appendChild(qualitySlider.el);
      }
```
In `renderSingle()` and `renderQueue()`, ensure every `appendChild` receiving a component passes `component.el`.

### 8.3 Verbatim Code for `app/web/api/base.py`
In `select_save_path(self, params: dict[str, Any]) -> dict[str, Any]`:
```python
        default_name = str(params.get("default_name", "")).strip()
        res = self._window.create_file_dialog(dialog_type=30, save_filename=default_name)
        if res:
            p_str = str(res) if isinstance(res, str) else str(res[0])
            if default_name and "." in default_name:
                expected_ext = "." + default_name.rsplit(".", 1)[-1].lower()
                if not p_str.lower().endswith(expected_ext):
                    p_str = p_str + expected_ext
            return ok(paths=[p_str], path=p_str, file_path=p_str, output_path=p_str, cancelled=False)
        return ok(paths=[], path="", file_path="", output_path="", cancelled=True)
```

### 8.4 Verbatim Code for `app/features/text_tools/ops.py` and `app/web/api/tool_text_tools.py`
In `app/features/text_tools/ops.py`:
```python
def to_pascal_case(text: str) -> str:
    # Convert text to PascalCase by capitalizing each word.
    words = _split_words(text)
    return "".join(word.capitalize() for word in words)
```
In `app/web/api/tool_text_tools.py:text_tools_case`:
```python
        elif mode in ("pascal", "pascalcase"):
            res = to_pascal_case(text)
```

### 8.5 Verbatim Code for `app/features/resume/ops.py:export_docx`
Replace the entire `export_docx` function:
```python
def export_docx(resume: MasterResume, output_path: str, theme: str = "gnc") -> str:
    # Export resume to Microsoft Word DOCX matching exact SpaceX GNC formatting.
    import os
    import docx
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = docx.Document()
    sec = doc.sections[0]
    sec.page_width = Inches(8.5)
    sec.page_height = Inches(11.0)
    sec.left_margin = Inches(0.75)
    sec.right_margin = Inches(0.75)
    sec.top_margin = Inches(0.65)
    sec.bottom_margin = Inches(0.65)

    style_normal = doc.styles["Normal"]
    style_normal.font.name = "Calibri"
    style_normal.font.size = Pt(10.5)
    style_normal.paragraph_format.line_spacing = 1.0
    style_normal.paragraph_format.space_before = Pt(0)
    style_normal.paragraph_format.space_after = Pt(0)

    # Header Name
    p_name = doc.add_paragraph()
    p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_name.paragraph_format.space_after = Pt(2)
    run_name = p_name.add_run((resume.contact.name or "CANDIDATE NAME").upper())
    run_name.font.name = "Calibri"
    run_name.font.size = Pt(20)
    run_name.font.bold = True
    run_name.font.color.rgb = RGBColor(0, 0, 0)

    # Contact Info
    c_parts = [p for p in [resume.contact.phone, resume.contact.email, resume.contact.location, resume.contact.linkedin, resume.contact.github, resume.contact.website] if p and p.strip()]
    if c_parts:
        p_c = doc.add_paragraph()
        p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_c.paragraph_format.space_after = Pt(4)
        run_c = p_c.add_run(" | ".join(c_parts))
        run_c.font.name = "Calibri"
        run_c.font.size = Pt(9.5)

    def add_section_header(title: str) -> None:
        p_h = doc.add_paragraph()
        p_h.paragraph_format.space_before = Pt(6)
        p_h.paragraph_format.space_after = Pt(2)
        r_h = p_h.add_run(title.upper())
        r_h.font.name = "Calibri"
        r_h.font.size = Pt(11)
        r_h.font.bold = True
        r_h.font.color.rgb = RGBColor(0, 0, 0)
        bdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="16" w:space="2" w:color="000000"/></w:pBdr>')
        p_h._p.get_or_add_pPr().append(bdr)

    # Summary Section
    if resume.summary_enabled and resume.summary.strip():
        add_section_header("Summary")
        p_s = doc.add_paragraph()
        p_s.paragraph_format.space_after = Pt(2)
        r_s = p_s.add_run(resume.summary.strip())
        r_s.font.name = "Calibri"
        r_s.font.size = Pt(10.5)

    for s in resume.sections:
        if not s.enabled:
            continue
        entries = [e for e in s.entries if e.enabled]
        if not entries:
            continue
        add_section_header(s.title)

        stype = s.type.lower()
        for e in entries:
            if stype == "education":
                p_deg = doc.add_paragraph()
                p_deg.paragraph_format.space_before = Pt(2)
                p_deg.paragraph_format.space_after = Pt(1)
                p_deg.paragraph_format.tab_stops.add_tab_stop(Inches(7.0), WD_TAB_ALIGNMENT.RIGHT)
                r_title = p_deg.add_run(e.title)
                r_title.font.name = "Calibri"
                r_title.font.size = Pt(10.5)
                r_title.font.bold = True
                if e.date_range:
                    r_date = p_deg.add_run(f"\t{e.date_range}")
                    r_date.font.name = "Calibri"
                    r_date.font.size = Pt(10.5)
                    r_date.font.bold = True

                if e.subtitle:
                    p_sub = doc.add_paragraph()
                    p_sub.paragraph_format.space_after = Pt(1)
                    r_sub = p_sub.add_run(e.subtitle)
                    r_sub.font.name = "Calibri"
                    r_sub.font.size = Pt(10.5)
                    r_sub.font.italic = True

                if e.gpa:
                    p_gpa = doc.add_paragraph()
                    p_gpa.paragraph_format.space_after = Pt(1)
                    r_gl = p_gpa.add_run("GPA: ")
                    r_gl.font.bold = True
                    p_gpa.add_run(e.gpa)

                if e.coursework:
                    p_cw = doc.add_paragraph()
                    p_cw.paragraph_format.space_after = Pt(2)
                    r_cl = p_cw.add_run("Relevant Coursework: ")
                    r_cl.font.bold = True
                    p_cw.add_run(e.coursework)

            elif stype in ("experience", "organization", "projects"):
                p_exp = doc.add_paragraph()
                p_exp.paragraph_format.space_before = Pt(3)
                p_exp.paragraph_format.space_after = Pt(1)
                p_exp.paragraph_format.tab_stops.add_tab_stop(Inches(7.0), WD_TAB_ALIGNMENT.RIGHT)
                r_pos = p_exp.add_run(e.title)
                r_pos.font.name = "Calibri"
                r_pos.font.size = Pt(10.5)
                r_pos.font.bold = True
                if e.subtitle:
                    r_org = p_exp.add_run(f", {e.subtitle}")
                    r_org.font.name = "Calibri"
                    r_org.font.size = Pt(10.5)
                    r_org.font.italic = True
                if e.date_range:
                    r_date = p_exp.add_run(f"\t{e.date_range}")
                    r_date.font.name = "Calibri"
                    r_date.font.size = Pt(10.5)
                    r_date.font.bold = True

                for b in e.bullets:
                    if not b.enabled or not b.text.strip():
                        continue
                    p_b = doc.add_paragraph()
                    p_b.paragraph_format.left_indent = Pt(9.0)
                    p_b.paragraph_format.first_line_indent = Pt(-9.0)
                    p_b.paragraph_format.tab_stops.add_tab_stop(Pt(9.0))
                    p_b.paragraph_format.space_before = Pt(0)
                    p_b.paragraph_format.space_after = Pt(1.5)
                    p_b.paragraph_format.line_spacing = 1.0

                    r_glyph = p_b.add_run("\u25cf\t")
                    r_glyph.font.name = "Arial"
                    r_glyph.font.size = Pt(8.5)

                    r_txt = p_b.add_run(b.text.strip())
                    r_txt.font.name = "Calibri"
                    r_txt.font.size = Pt(10.5)

            elif stype == "skills":
                p_sk = doc.add_paragraph()
                p_sk.paragraph_format.space_before = Pt(2)
                p_sk.paragraph_format.space_after = Pt(2)
                r_st = p_sk.add_run(f"{e.title}: ")
                r_st.font.name = "Calibri"
                r_st.font.size = Pt(10.5)
                r_st.font.bold = True
                s_body = e.skills_text or ", ".join([b.text for b in e.bullets if b.enabled])
                r_sb = p_sk.add_run(s_body)
                r_sb.font.name = "Calibri"
                r_sb.font.size = Pt(10.5)

    doc.save(output_path)
    return output_path
```

### 8.6 Verbatim Code for `app/web/js/tools/collage.js:handleSave`
Replace lines 1370-1397:
```javascript
      var defaultExt = activeExportFormat === "jpeg" ? ".jpg" : ".png";
      window.FOSS.api("select_save_path", {
        title: "Save Collage",
        default_name: "collage" + defaultExt,
        file_types: [
          { name: "Image (" + defaultExt + ")", extensions: [defaultExt.replace(".", "")] }
        ]
      }).then(function (res) {
        if (!res || res.cancelled || !res.path) return;
        var chosenPath = res.path;
        if (!chosenPath.toLowerCase().endsWith(defaultExt)) {
          chosenPath = chosenPath + defaultExt;
        }

        statusBar.textContent = "Exporting collage...";
        var params = {
          image_paths: layers.map(function (l) { return l.source_path; }),
          output_path: chosenPath,
          columns: parseInt(colsSelect.value, 10) || 2,
          fit_mode: fitSelect.value,
          padding: parseInt(paddingInput.value, 10) || 12,
          corner_radius: parseInt(cornerRadiusInput.value, 10) || 0,
          bg_color: bgColor,
          transparent_bg: isTransparent,
          add_captions: captionsCheck.checked,
          watermark_text: watermarkInput.value.trim() || undefined
        };

        window.FOSS.api("collage_create", params).then(function (createRes) {
          if (createRes && createRes.output_path) {
            statusBar.textContent = "Collage saved: " + createRes.output_path;
            showResult(createRes.output_path, "Collage Saved Successfully");
          } else {
            showError("Failed to save collage.");
          }
        }).catch(function (err) {
          showError(err && err.message ? err.message : String(err));
        });
      });
```

### 8.7 Verbatim Code for `app/web/js/tools/unit_converter.js`
In `renderStandard(panel, ctx)`:
Organize the primary conversion card at the top, followed by advanced options:
```javascript
    // Top Section: Inputs and Primary Action
    var topRow = window.FOSS.dom.el("div", { className: "row gap-2 items-center flex-wrap" }, [
      window.FOSS.components.field("Quantity Value", valueInput),
      window.FOSS.components.field("From Unit", fromUnitSelect),
      swapBtn,
      window.FOSS.components.field("To Unit", toUnitSelect),
      convertBtn
    ]);

    var primaryCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-2 mb-3",
      "data-testid": "unit_converter-primary-card"
    }, [
      window.FOSS.dom.el("div", { className: "font-semibold text-sm", text: "Standard Unit Conversion" }),
      topRow,
      resultBanner
    ]);

    // Bottom Section: Dimension and Notation Options
    var optionsRow = window.FOSS.dom.el("div", { className: "row gap-2 flex-wrap" }, [
      window.FOSS.components.field("Physical Dimension", categorySelect),
      window.FOSS.components.field("Prefix Multiplier", prefixSelect),
      window.FOSS.components.field("Output Notation", notationSelect),
      window.FOSS.components.field("Significant Digits", precisionSelect)
    ]);

    var optionsCard = window.FOSS.dom.el("div", {
      className: "card card-compact flex-col gap-2",
      "data-testid": "unit_converter-options-card"
    }, [
      window.FOSS.dom.el("div", { className: "font-semibold text-xs text-muted", text: "Measurement Registry Options" }),
      optionsRow
    ]);

    sidebar.appendChild(primaryCard);
    sidebar.appendChild(optionsCard);
```

### 8.8 Verbatim Code for `app/web/js/tools/model3d.js`
Replace router registration tabs array (around lines 1520-1526):
```javascript
  window.FOSS.router.register({
    id: "model3d",
    title: "3D Model Studio",
    navName: "3D Models",
    category: "Visuals",
    icon: "box",
    workbench: true,
    tabs: [
      { id: "inspector", label: "Inspector & Tools", render: renderUnifiedInspector },
      { id: "cut", label: "Cut Plane", render: renderCut },
      { id: "export", label: "Export & Convert", render: renderExport }
    ]
  });
```
In `renderUnifiedInspector(panel, ctx)`:
```javascript
    var sidebar = window.FOSS.dom.el("div", {
      className: "model3d-sidebar-pane stack scroll-y",
      "data-testid": "model3d-sidebar"
    }, [
      infoCard,
      scaleCard,
      measureCard
    ]);
```

### 8.9 Verbatim Code for Network Monitor
In `app/web/js/tools/network_monitor.js:renderLive(panel, ctx)`:
```javascript
      var thead = window.FOSS.dom.el("thead", {}, [
        window.FOSS.dom.el("tr", {}, [
          window.FOSS.dom.el("th", { style: "width: 8%; white-space: nowrap;", text: "PID", "data-truncate-ok": "true" }),
          window.FOSS.dom.el("th", { style: "width: 18%; white-space: nowrap;", text: "Process", "data-truncate-ok": "true" }),
          window.FOSS.dom.el("th", { style: "width: 16%; white-space: nowrap;", text: "Source Identity", "data-truncate-ok": "true" }),
          window.FOSS.dom.el("th", { style: "width: 14%; white-space: nowrap;", text: "Trust Level", "data-truncate-ok": "true" }),
          window.FOSS.dom.el("th", { style: "width: 8%; white-space: nowrap;", text: "Proto", "data-truncate-ok": "true" }),
          window.FOSS.dom.el("th", { style: "width: 12%; white-space: nowrap;", text: "Local", "data-truncate-ok": "true" }),
          window.FOSS.dom.el("th", { style: "width: 12%; white-space: nowrap;", text: "Remote", "data-truncate-ok": "true" }),
          window.FOSS.dom.el("th", { style: "width: 12%; white-space: nowrap;", text: "Host", "data-truncate-ok": "true" })
        ])
      ]);
```
In `app/features/network_monitor/resolver.py`:
```python
def classify_connection_trust(process_name: str, remote_ip: str, remote_domain: str | None = None) -> tuple[str, str]:
    # Determine source identity and trustworthiness rating.
    proc_lower = process_name.lower().strip()
    if proc_lower in ("svchost.exe", "lsass.exe", "services.exe", "explorer.exe", "system"):
        return "Windows System", "Trusted System"
    if proc_lower in ("msedge.exe", "chrome.exe", "firefox.exe", "brave.exe"):
        return "Web Browser", "Trusted App"
    if proc_lower in ("python.exe", "node.exe", "git.exe", "code.exe", "uv.exe"):
        return "Developer Tool", "Local Dev"
    if remote_ip.startswith(("127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.", "::1")):
        return "Local Subnet", "Local Safe"
    if remote_domain and any(remote_domain.endswith(dom) for dom in ("microsoft.com", "google.com", "github.com", "cloudflare.com")):
        return "Verified CDN", "Trusted Service"
    if not remote_domain and remote_ip:
        return "External IP", "Unverified"
    return "Application", "Local Safe"
```

### 8.10 Verbatim Code for `app/web/js/settings.js:renderSidebarCustomizer`
```javascript
  function renderSidebarCustomizer(panel) {
    panel.innerHTML = "";
    panel.appendChild(window.FOSS.dom.el("h2", { className: "card-title", text: "Sidebar and Navigation Customizer" }));
    panel.appendChild(window.FOSS.dom.el("p", {
      className: "desc",
      text: "Drag sections or app cards to reorder. Place apps in multiple sections or hide tools."
    }));

    var editor = window.FOSS.dom.el("div", { className: "stack", "data-testid": "settings-sidebar-editor" });
    var layout = window.FOSS.router.resolveSidebarLayout();
    var registeredTools = window.FOSS.router.getRegisteredTools();

    function persistAndRefresh() {
      window.FOSS.store.set("sidebar_layout", layout);
      window.FOSS.router.renderSidebar();
      renderSidebarCustomizer(panel);
    }

    // Section cards loop
    layout.sections.forEach(function (sec, secIdx) {
      var secCard = window.FOSS.dom.el("div", {
        className: "card card-compact stack-sm",
        "data-testid": "settings-section-" + sec.id,
        draggable: "true"
      });

      secCard.addEventListener("dragstart", function (e) {
        e.dataTransfer.setData("text/plain", JSON.stringify({ type: "section", secId: sec.id }));
      });
      secCard.addEventListener("dragover", function (e) {
        e.preventDefault();
        secCard.classList.add("drop-target-above");
      });
      secCard.addEventListener("dragleave", function () {
        secCard.classList.remove("drop-target-above");
      });
      secCard.addEventListener("drop", function (e) {
        e.preventDefault();
        secCard.classList.remove("drop-target-above");
        try {
          var data = JSON.parse(e.dataTransfer.getData("text/plain"));
          if (data.type === "section" && data.secId !== sec.id) {
            var srcIdx = layout.sections.findIndex(function (s) { return s.id === data.secId; });
            if (srcIdx >= 0) {
              var moved = layout.sections.splice(srcIdx, 1)[0];
              layout.sections.splice(secIdx, 0, moved);
              persistAndRefresh();
            } 
          }
        } catch (err) {}
      });

      var nameInput = window.FOSS.dom.el("input", {
        type: "text",
        className: "input",
        value: sec.name,
        "data-testid": "settings-section-name-" + sec.id,
        "aria-label": "Section name for " + sec.name,
        onChange: function (e) {
          sec.name = e.target.value.trim() || sec.name;
          window.FOSS.store.set("sidebar_layout", layout);
          window.FOSS.router.renderSidebar();
        }
      });

      var deleteBtn = window.FOSS.dom.el("button", {
        className: "btn btn-ghost btn-sm",
        text: "Delete",
        "data-testid": "settings-delete-section-" + sec.id,
        disabled: layout.sections.length <= 1,
        onClick: function () {
          if (layout.sections.length <= 1) return;
          layout.sections = layout.sections.filter(function (s) { return s.id !== sec.id; });
          persistAndRefresh();
        }
      });

      var secHeader = window.FOSS.dom.el("div", { className: "row-between" }, [
        window.FOSS.dom.el("div", { className: "row gap-2" }, [
          window.FOSS.icons.el("grip", 16),
          nameInput
        ]),
        deleteBtn
      ]);
      secCard.appendChild(secHeader);

      // App rows inside section
      var itemsContainer = window.FOSS.dom.el("div", { className: "stack-sm" });
      sec.items.forEach(function (item, itemIdx) {
        var tool = registeredTools.find(function (t) { return t.id === item.id; });
        var appRow = window.FOSS.dom.el("div", {
          className: "row-between p-2 rounded surface-hover",
          "data-testid": "settings-app-row-" + item.id,
          draggable: "true"
        });

        appRow.addEventListener("dragstart", function (e) {
          e.stopPropagation();
          e.dataTransfer.setData("text/plain", JSON.stringify({ type: "app", appId: item.id, fromSec: sec.id }));
        });
        appRow.addEventListener("dragover", function (e) {
          e.preventDefault();
          e.stopPropagation();
          appRow.classList.add("drop-target-above");
        });
        appRow.addEventListener("dragleave", function () {
          appRow.classList.remove("drop-target-above");
        });
        appRow.addEventListener("drop", function (e) {
          e.preventDefault();
          e.stopPropagation();
          appRow.classList.remove("drop-target-above");
          try {
            var data = JSON.parse(e.dataTransfer.getData("text/plain"));
            if (data.type === "app") {
              var fromS = layout.sections.find(function (s) { return s.id === data.fromSec; });
              if (fromS) {
                var itIdx = fromS.items.findIndex(function (it) { return it.id === data.appId; });
                if (itIdx >= 0) {
                  var movedItem = fromS.items.splice(itIdx, 1)[0];
                  sec.items.splice(itemIdx, 0, movedItem);
                  persistAndRefresh();
                }
              }
            }
          } catch (err) {}
        });

        var check = window.FOSS.dom.el("input", {
          type: "checkbox",
          checked: !!item.visible,
          "data-testid": "settings-app-check-" + item.id,
          "aria-label": "Toggle tool visibility",
          onChange: function (e) {
            item.visible = e.target.checked;
            window.FOSS.store.set("sidebar_layout", layout);
            window.FOSS.router.renderSidebar();
          }
        });

        var removeAppBtn = window.FOSS.dom.el("button", {
          className: "btn btn-ghost btn-sm",
          "aria-label": "Remove tool from section",
          title: "Remove from section",
          onClick: function () {
            sec.items.splice(itemIdx, 1);
            persistAndRefresh();
          }
        }, [window.FOSS.icons.el("close", 14)]);

        var iconEl = window.FOSS.icons.el(tool ? tool.icon || "file" : "file", 18);
        var labelGroup = window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [
          window.FOSS.icons.el("grip", 14),
          check,
          iconEl,
          window.FOSS.dom.el("span", { className: "font-semibold text-sm", text: tool ? tool.title : item.id })
        ]);

        appRow.appendChild(labelGroup);
        appRow.appendChild(removeAppBtn);
        itemsContainer.appendChild(appRow);
      });

      secCard.appendChild(itemsContainer);
      editor.appendChild(secCard);
    });

    panel.appendChild(editor);
  }
```

### 8.11 Verbatim Code for `app/web/js/core/shortcuts.js`
```javascript
  var DEFAULT_KEYMAP = {
    "open_palette": { label: "Command Palette", key: "k", ctrl: true, alt: false, shift: false, display: "Ctrl+K" },
    "go_home": { label: "Navigate to Home", key: "Home", ctrl: false, alt: true, shift: false, display: "Alt+Home" },
    "open_settings": { label: "Open Settings", key: "s", ctrl: false, alt: true, shift: false, display: "Alt+S" },
    "toggle_fullscreen": { label: "Toggle Fullscreen", key: "F11", ctrl: false, alt: false, shift: false, display: "F11" },
    "zoom_in": { label: "Zoom In", key: "=", ctrl: true, alt: false, shift: false, display: "Ctrl+=" },
    "zoom_out": { label: "Zoom Out", key: "-", ctrl: true, alt: false, shift: false, display: "Ctrl+-" },
    "zoom_reset": { label: "Reset Zoom", key: "0", ctrl: true, alt: false, shift: false, display: "Ctrl+0" }
  };

  function getKeymap() {
    return window.FOSS.store.get("custom_keybindings", DEFAULT_KEYMAP);
  }

  function handleKeyDown(e) {
    var map = getKeymap();
    for (var action in map) {
      var b = map[action];
      if (b.key.toLowerCase() === e.key.toLowerCase() &&
          !!b.ctrl === (e.ctrlKey || e.metaKey) &&
          !!b.alt === e.altKey &&
          !!b.shift === e.shiftKey) {
        e.preventDefault();
        dispatchShortcutAction(action);
        return;
      }
    }
  }
```

### 8.12 Verbatim Code for `app/web/js/core/router.js`
In `DEFAULT_SECTIONS`:
```javascript
  var DEFAULT_SECTIONS = [
    {
      id: "sec_favorites",
      name: "Favorites",
      collapsed: false,
      items: [
        { id: "pdf", visible: true },
        { id: "converter", visible: true },
        { id: "ocr", visible: true }
      ]
    },
    {
      id: "sec_documents",
      name: "Documents",
      collapsed: false,
      items: [
        { id: "pdf", visible: true },
        { id: "ocr", visible: true },
        { id: "markdown", visible: true },
        { id: "resume", visible: true }
      ]
    },
    {
      id: "sec_visuals",
      name: "Visuals",
      collapsed: false,
      items: [
        { id: "images", visible: true },
        { id: "collage", visible: true },
        { id: "palette", visible: true },
        { id: "model3d", visible: true }
      ]
    },
    {
      id: "sec_media",
      name: "Media",
      collapsed: false,
      items: [
        { id: "media", visible: true },
        { id: "playlist", visible: true }
      ]
    },
    {
      id: "sec_files",
      name: "Files & Storage",
      collapsed: false,
      items: [
        { id: "converter", visible: true },
        { id: "compressor", visible: true },
        { id: "archive", visible: true },
        { id: "renamer", visible: true },
        { id: "metadata", visible: true },
        { id: "qr", visible: true }
      ]
    },
    {
      id: "sec_system",
      name: "System & Data",
      collapsed: false,
      items: [
        { id: "network_monitor", visible: true },
        { id: "unit_converter", visible: true },
        { id: "data", visible: true },
        { id: "text_tools", visible: true },
        { id: "encoding", visible: true }
      ]
    }
  ];
```

### 8.13 Verbatim Code for `app/web/js/home.js`
In `render(container)`:
```javascript
    var layout = window.FOSS.router.resolveSidebarLayout();
    var sectionNames = (layout.sections || [])
      .filter(function (s) { return (s.items || []).some(function (it) { return it.visible; }); })
      .map(function (s) { return s.name; });
    var categories = ["All"].concat(sectionNames);

    var filterRow = window.FOSS.dom.el('div', { className: 'row gap-2 flex-wrap mb-3' });
    categories.forEach(function (cat) {
      var chip = window.FOSS.dom.el('button', {
        className: 'chip' + (activeCategory === cat ? ' active' : ''),
        text: cat,
        onClick: function () {
          activeCategory = cat;
          renderCards();
        }
      });
      filterRow.appendChild(chip);
    });
```

### 8.14 Verbatim Code for `app/features/ocr/ops.py:create_searchable_pdf`
```python
def create_searchable_pdf(input_path: str, output_path: str, language: str = 'eng', force_reocr: bool = False, pages: str | None = None) -> str:
    # Create searchable PDF while preserving existing digital text layers unless forced.
    import pymupdf
    import pytesseract
    from PIL import Image
    import io

    doc = pymupdf.open(input_path)
    total_pages = len(doc)
    selected = parse_page_selection(pages, total_pages) if pages else set(range(total_pages))
    out_doc = pymupdf.open()

    for idx in range(total_pages):
        page = doc[idx]
        if idx not in selected:
            out_doc.insert_pdf(doc, from_page=idx, to_page=idx)
            continue

        existing_text = page.get_text().strip()
        if len(existing_text) >= 15 and not force_reocr:
            out_doc.insert_pdf(doc, from_page=idx, to_page=idx)
            continue

        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes()))
        pdf_bytes = pytesseract.image_to_pdf_or_hocr(img, lang=language, extension='pdf')
        ocr_page_doc = pymupdf.open('pdf', pdf_bytes)
        out_doc.insert_pdf(ocr_page_doc)
        ocr_page_doc.close()

    out_doc.save(output_path)
    out_doc.close()
    doc.close()
    return output_path
```

### 8.15 Verbatim Code for `app/features/metadata/ops.py`
```python
def strip_office_metadata(input_path: str, output_path: str) -> str:
    # Strip author, organization, and revision metadata from Office documents.
    import docx
    doc = docx.Document(input_path)
    core = doc.core_properties
    core.author = ""
    core.last_modified_by = ""
    core.comments = ""
    core.title = ""
    doc.save(output_path)
    return output_path
```

### 8.16 Verbatim Code for `app/web/css/layout.css` and `app/web/css/tools.css`
In `app/web/css/layout.css`:
```css
.app {
  display: flex;
  flex-direction: row;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.main,
.scroll-main,
.page,
.settings-page {
  min-height: 0;
  min-width: 0;
  overflow-y: auto;
  overflow-x: auto;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: var(--z-topbar);
  flex-shrink: 0;
}
```
In `app/web/css/tools.css`:
```css
.code-editor-fill {
  display: flex;
  flex-direction: column;
  flex: 1 1 0%;
  min-height: 0;
  height: 100%;
  width: 100%;
}

.code-editor-fill textarea.code-editor {
  flex: 1 1 0%;
  min-height: 20rem;
  height: 100%;
  width: 100%;
  resize: vertical;
  box-sizing: border-box;
}
```

### 8.17 Verbatim Code for `tests/ui/scenarios/test_all_walkthroughs.py`
```python
from pathlib import Path
from typing import Any
from playwright.sync_api import Page, expect

def test_full_application_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    # Exercise primary actions and save verifications across all canonical tools.
    fixtures_dir = Path("tests/ui/_fixtures")

    # 1. PDF Tools
    sample_pdf = str(fixtures_dir / "sample.pdf")
    pdf_out = str(tmp_path / "walkthrough_merged.pdf")
    api._dialog_answers.extend([[sample_pdf], pdf_out])
    page.evaluate("window.FOSS.router.open('pdf', 'merge')")
    page.wait_for_timeout(200)

    # 2. OCR Studio
    sample_img = str(fixtures_dir / "sample.png")
    api._dialog_answers.append(sample_img)
    page.evaluate("window.FOSS.router.open('ocr', 'document')")
    page.wait_for_timeout(200)

    # 3. Resume Studio
    docx_out = str(tmp_path / "walkthrough_resume.docx")
    api._dialog_answers.append(docx_out)
    page.evaluate("window.FOSS.router.open('resume', 'preview')")
    page.wait_for_timeout(200)

    # 4. Universal Converter
    conv_out = str(tmp_path / "walkthrough_conv.jpg")
    api._dialog_answers.extend([sample_img, conv_out])
    page.evaluate("window.FOSS.router.open('converter', 'single')")
    page.wait_for_timeout(200)

    # 5. Unit Converter
    page.evaluate("window.FOSS.router.open('unit_converter', 'standard')")
    expect(page.locator("[data-testid='unit_converter-primary-card']")).to_be_visible()
```

### 8.18 Verbatim Code for `app/web/js/tools/pdf.js:renderCombineOrganize`
```javascript
  function renderCombineOrganize(panel, ctx) {
    panel.innerHTML = "";
    panel.appendChild(window.FOSS.dom.el("h2", { className: "card-title", text: "Combine and Organize PDF Documents" }));
    panel.appendChild(window.FOSS.dom.el("p", {
      className: "desc",
      text: "Drag and drop pages or document groups to reorder. Rotate, duplicate, or delete individual pages."
    }));

    var groups = [];
    var container = window.FOSS.dom.el("div", { className: "stack", "data-testid": "pdf-groups-container" });

    function renderGroups() {
      container.innerHTML = "";
      groups.forEach(function (group, gIdx) {
        var groupCard = window.FOSS.dom.el("div", {
          className: "card card-compact stack-sm",
          "data-testid": "pdf-group-" + gIdx,
          draggable: "true"
        });

        var header = window.FOSS.dom.el("div", { className: "row-between items-center" }, [
          window.FOSS.dom.el("div", { className: "row gap-2 items-center" }, [
            window.FOSS.icons.el("grip", 16),
            window.FOSS.dom.el("span", { className: "font-semibold text-sm", text: group.title + " (" + group.pages.length + " pages)" })
          ]),
          window.FOSS.dom.el("div", { className: "row gap-1" }, [
            window.FOSS.dom.el("button", {
              className: "btn btn-ghost btn-sm",
              text: group.expanded ? "Collapse" : "Ungroup into Pages",
              "data-testid": "pdf-ungroup-btn",
              onClick: function () {
                group.expanded = !group.expanded;
                renderGroups();
              }
            }),
            window.FOSS.dom.el("button", {
              className: "btn btn-ghost btn-sm",
              "aria-label": "Delete group",
              onClick: function () {
                groups.splice(gIdx, 1);
                renderGroups();
              }
            }, [window.FOSS.icons.el("trash", 14)])
          ])
        ]);
        groupCard.appendChild(header);

        if (group.expanded) {
          var pagesGrid = window.FOSS.dom.el("div", { className: "row gap-2 flex-wrap p-2 surface-sunken rounded" });
          group.pages.forEach(function (page, pIdx) {
            var pageCard = window.FOSS.dom.el("div", {
              className: "card card-compact items-center p-2 surface-hover",
              "data-testid": "pdf-page-card-" + pIdx,
              draggable: "true"
            });

            var badge = window.FOSS.dom.el("span", { className: "badge badge-neutral mb-1", text: "Page " + (page.page_number || (pIdx + 1)) });
            var btnRow = window.FOSS.dom.el("div", { className: "row gap-1" }, [
              window.FOSS.dom.el("button", {
                className: "btn btn-ghost btn-xs",
                title: "Rotate 90 deg clockwise",
                "data-testid": "pdf-page-rotate",
                onClick: function () {
                  page.rotation = ((page.rotation || 0) + 90) % 360;
                  renderGroups();
                }
              }, [window.FOSS.icons.el("rotate", 12)]),
              window.FOSS.dom.el("button", {
                className: "btn btn-ghost btn-xs",
                title: "Duplicate page",
                "data-testid": "pdf-page-duplicate",
                onClick: function () {
                  group.pages.splice(pIdx + 1, 0, Object.assign({}, page));
                  renderGroups();
                }
              }, [window.FOSS.icons.el("copy", 12)]),
              window.FOSS.dom.el("button", {
                className: "btn btn-ghost btn-xs",
                title: "Delete page",
                "data-testid": "pdf-page-delete",
                onClick: function () {
                  group.pages.splice(pIdx, 1);
                  renderGroups();
                }
              }, [window.FOSS.icons.el("trash", 12)])
            ]);

            pageCard.appendChild(badge);
            pageCard.appendChild(btnRow);
            pagesGrid.appendChild(pageCard);
          });
          groupCard.appendChild(pagesGrid);
        }
        container.appendChild(groupCard);
      });
    }

    var addPdfBtn = window.FOSS.dom.el('button', {
      className: 'btn btn-primary',
      text: 'Add PDF Documents...',
      'data-testid': 'pdf-merge-add-btn',
      onClick: function () {
        window.FOSS.api('select_files', { file_types: [{ name: 'PDF', extensions: ['pdf'] }] }).then(function (res) {
          if (res && res.paths) {
            res.paths.forEach(function (p) {
              var name = p.replace(/^.*[\\\/]/, '');
              groups.push({ title: name, path: p, expanded: false, pages: [{ page_number: 1, rotation: 0 }] });
            });
            renderGroups();
          }
        });
      }
    });

    var saveBtn = window.FOSS.dom.el('button', {
      className: 'btn btn-success',
      text: 'Export Combined PDF',
      'data-testid': 'pdf-merge-save-btn',
      onClick: function () {
        window.FOSS.api('select_save_path', { title: 'Save Combined PDF', default_name: 'combined.pdf', file_types: [{ name: 'PDF', extensions: ['pdf'] }] }).then(function (res) {
          if (res && res.path) {
            var flatPages = [];
            groups.forEach(function (g) {
              g.pages.forEach(function (pg) {
                flatPages.push({ source_path: g.path, page_number: pg.page_number, rotation: pg.rotation || 0 });
              });
            });
            window.FOSS.api('pdf_merge_pages', { pages: flatPages, output_path: res.path });
          }
        });
      }
    });

    panel.appendChild(window.FOSS.dom.el('div', { className: 'row gap-2 mb-3' }, [addPdfBtn, saveBtn]));
    panel.appendChild(container);
  }
```

### 8.19 Verbatim Code for `app/features/converter/ops.py:convert_office_doc`
```python
def convert_office_doc(input_path: str, output_path: str, target_format: str) -> str:
    # Convert Microsoft Office formats to PDF or structured data.
    import os
    ext = os.path.splitext(input_path)[1].lower()
    tgt = target_format.lower().strip('.')

    if ext == '.docx' and tgt == 'pdf':
        import docx2pdf
        docx2pdf.convert(input_path, output_path)
        return output_path

    if ext == '.xlsx' and tgt == 'csv':
        import openpyxl
        import csv
        wb = openpyxl.load_workbook(input_path, data_only=True)
        sheet = wb.active
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for row in sheet.iter_rows(values_only=True):
                writer.writerow(row)
        return output_path

    raise ValueError(f'Unsupported office conversion from {ext} to {tgt}')
```

### 8.20 Verbatim Code for Complete 21-Tool Test Suite `tests/ui/scenarios/test_all_walkthroughs.py`
```python
from pathlib import Path
from typing import Any
from playwright.sync_api import Page, expect

def test_full_application_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    # Complete automated Playwright test exercising all 21 canonical tools sequentially.
    fixtures_dir = Path("tests/ui/_fixtures")
    sample_pdf = str(fixtures_dir / "sample.pdf")
    sample_png = str(fixtures_dir / "sample.png")
    sample_docx = str(fixtures_dir / "sample.docx")
    cube_stl = str(fixtures_dir / "cube.stl")
    clip_mp4 = str(fixtures_dir / "clip.mp4")
    playlist_m3u8 = str(fixtures_dir / "playlist.m3u8")

    # 1. PDF Tools
    pdf_out = str(tmp_path / "out_pdf_merged.pdf")
    api._dialog_answers.extend([[sample_pdf], pdf_out])
    page.evaluate("window.FOSS.router.open('pdf', 'merge')")
    page.click("[data-testid='pdf-merge-add-btn']")
    page.wait_for_timeout(150)
    page.click("[data-testid='pdf-merge-save-btn']")
    page.wait_for_timeout(250)
    assert Path(pdf_out).exists()

    # 2. OCR Studio
    ocr_out = str(tmp_path / "out_ocr.pdf")
    api._dialog_answers.extend([sample_png, ocr_out])
    page.evaluate("window.FOSS.router.open('ocr', 'document')")
    page.click("[data-testid='ocr-choose-file']")
    page.fill("[data-testid='ocr-page-range']", "1")
    page.click("[data-testid='ocr-run-btn']")
    page.wait_for_timeout(300)
    page.click("[data-testid='ocr-export-pdf-btn']")
    page.wait_for_timeout(250)
    assert Path(ocr_out).exists()

    # 3. Markdown Studio
    md_out = str(tmp_path / "out_markdown.html")
    api._dialog_answers.append(md_out)
    page.evaluate("window.FOSS.router.open('markdown', 'editor')")
    page.select_option("[data-testid='markdown-flavor-select']", "gfm")
    page.click("[data-testid='markdown-export-html-btn']")
    page.wait_for_timeout(200)
    assert Path(md_out).exists()

    # 4. Resume Studio
    docx_out = str(tmp_path / "out_resume.docx")
    api._dialog_answers.append(docx_out)
    page.evaluate("window.FOSS.router.open('resume', 'preview')")
    page.click("[data-testid='resume-export-docx-btn']")
    page.wait_for_timeout(250)
    assert Path(docx_out).exists()

    # 5. Image Studio
    img_out = str(tmp_path / "out_img.webp")
    api._dialog_answers.extend([sample_png, img_out])
    page.evaluate("window.FOSS.router.open('images', 'transform')")
    page.click("[data-testid='images-choose-file']")
    page.click("[data-testid='images-save-btn']")
    page.wait_for_timeout(250)
    assert Path(img_out).exists()

    # 6. Photo Collage
    col_out = str(tmp_path / "out_collage.png")
    api._dialog_answers.extend([[sample_png], col_out])
    page.evaluate("window.FOSS.router.open('collage', 'freeform')")
    page.click("[data-testid='collage-add-images-btn']")
    page.click("[data-testid='collage-export-btn']")
    page.wait_for_timeout(250)
    assert Path(col_out).exists()

    # 7. Color Palette
    api._dialog_answers.append(sample_png)
    page.evaluate("window.FOSS.router.open('palette', 'extract')")
    page.click("[data-testid='palette-choose-file']")
    page.wait_for_timeout(250)
    expect(page.locator("[data-testid='palette-swatch-grid']")).to_be_visible()

    # 8. 3D Model Studio
    api._dialog_answers.append(cube_stl)
    page.evaluate("window.FOSS.router.open('model3d', 'inspector')")
    page.click("[data-testid='model3d-load-file']")
    page.wait_for_timeout(250)
    expect(page.locator("[data-testid='model3d-sidebar']")).to_be_visible()

    # 9. Audio & Video Studio
    media_out = str(tmp_path / "out_audio.mp3")
    api._dialog_answers.extend([clip_mp4, media_out])
    page.evaluate("window.FOSS.router.open('media', 'audio')")
    page.click("[data-testid='media-choose-file']")
    page.click("[data-testid='media-extract-audio-btn']")
    page.wait_for_timeout(250)
    assert Path(media_out).exists()

    # 10. Playlist Porter
    pl_out = str(tmp_path / "out_pl.csv")
    api._dialog_answers.extend([playlist_m3u8, pl_out])
    page.evaluate("window.FOSS.router.open('playlist', 'import')")
    page.click("[data-testid='playlist-choose-file']")
    page.click("[data-testid='playlist-export-csv-btn']")
    page.wait_for_timeout(200)
    assert Path(pl_out).exists()

    # 11. Universal Converter
    conv_out = str(tmp_path / "out_conv.jpg")
    api._dialog_answers.extend([sample_png, conv_out])
    page.evaluate("window.FOSS.router.open('converter', 'single')")
    page.click("[data-testid='converter-choose-file']")
    page.click("[data-testid='converter-convert-btn']")
    page.wait_for_timeout(250)
    assert Path(conv_out).exists()

    # 12. File Compressor
    comp_out = str(tmp_path / "out_comp.pdf")
    api._dialog_answers.extend([sample_pdf, comp_out])
    page.evaluate("window.FOSS.router.open('compressor', 'single')")
    page.click("[data-testid='compressor-choose-file']")
    page.click("[data-testid='compressor-run-btn']")
    page.wait_for_timeout(250)
    assert Path(comp_out).exists()

    # 13. Archive Studio
    arc_out = str(tmp_path / "out_arc.zip")
    api._dialog_answers.extend([[sample_png], arc_out])
    page.evaluate("window.FOSS.router.open('archive', 'create')")
    page.click("[data-testid='archive-add-files-btn']")
    page.click("[data-testid='archive-create-btn']")
    page.wait_for_timeout(250)
    assert Path(arc_out).exists()

    # 14. Batch Renamer
    target_f = tmp_path / "rename_me.png"
    target_f.write_bytes(Path(sample_png).read_bytes())
    api._dialog_answers.append(str(target_f))
    page.evaluate("window.FOSS.router.open('renamer', 'rules')")
    page.click("[data-testid='renamer-add-files-btn']")
    page.click("[data-testid='renamer-apply-btn']")
    page.wait_for_timeout(200)

    # 15. Metadata Stripper
    meta_out = str(tmp_path / "out_meta.docx")
    api._dialog_answers.extend([sample_docx, meta_out])
    page.evaluate("window.FOSS.router.open('metadata', 'strip')")
    page.click("[data-testid='metadata-choose-file']")
    page.click("[data-testid='metadata-strip-btn']")
    page.wait_for_timeout(200)
    assert Path(meta_out).exists()

    # 16. QR and Barcodes
    qr_out = str(tmp_path / "out_qr.png")
    api._dialog_answers.append(qr_out)
    page.evaluate("window.FOSS.router.open('qr', 'generate')")
    page.fill("[data-testi0d='qr-text-input']", "https://foss.example.com")
    page.click("[data-testid='qr-save-png-btn']")
    page.wait_for_timeout(200)
    assert Path(qr_out).exists()

    # 17. Network Traffic Monitor
    page.evaluate("window.FOSS.router.open('network_monitor', 'live')")
    page.wait_for_timeout(200)
    expect(page.locator("text=Source Identity").first).to_be_visible()

    # 18. Unit Converter
    page.evaluate("window.FOSS.router.open('unit_converter', 'standard')")
    expect(page.locator("[data-testid='unit_converter-primary-card']")).to_be_visible()

    # 19. Data Studio
    data_out = str(tmp_path / "out_data.yaml")
    api._dialog_answers.append(data_out)
    page.evaluate("window.FOSS.router.open('data', 'format')")
    page.click("[data-testid='data-save-btn']")
    page.wait_for_timeout(200)
    assert Path(data_out).exists()

    # 20. Text Tools
    page.evaluate("window.FOSS.router.open('text_tools', 'case')")
    expect(page.locator("[data-testid='text_tools-pascal-btn']")).to_be_visible()

    # 21. Encoding / Decoding
    page.evaluate("window.FOSS.router.open('encoding', 'base64')")
    expect(page.locator("[data-testid='encoding-encode-btn']")).to_be_visible()
```

