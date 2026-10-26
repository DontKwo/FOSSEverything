<!-- noqa: 19 -->
# PLAN: FOSSEverything on pywebview

Audience: coding agents that follow instructions literally. Every decision is already made here. Do not improvise architecture. When a step says "run X", run X and read the output before continuing. When a gate fails, fix the cause and re-run the gate. Never skip a gate.

## 0. Ground rules for every change

Python interpreter for everything: `.venv\Scripts\python.exe` (Python 3.13). Never use the global `python` (it has no dependencies). Run tests with `.venv\Scripts\python.exe -m pytest -q`.

Code style rules (the owner enforces these with a linter):

- Every Python function has typed parameters and a return type. Example: `def calc_ratio(a: float, b: float) -> float:`.
- Comments are at most 2 lines and say only what the code does now. No history, no reasons, no TODO/FIXME/HACK/XXX markers.
- No em dashes, no en dashes, no curly quotes, no emoji, no unicode arrows, no unicode ellipsis, no bullets. All source files (py, js, css, html, md) are pure ASCII. In HTML text use entities (`&rarr;`, `&hellip;`, `&middot;`) or inline SVG.
- No divider banners (lines of `#####` or `=====` or box-drawing characters).
- One version of everything. Delete replaced code. Do not keep aliases for renamed items, extra code branches for replaced features, or unused functions.
- Engineering and math helper functions are named `calc_*`. Use plain dicts and lists, plain loops. No deep class hierarchies. No multi-line Args/Returns docstrings on short functions.
- Python imports go at the top of the file. No imports inside functions or try blocks (heavy optional libraries are listed in `pyproject.toml`, so import them at the top).
- No `console.log`, `console.debug`, `console.info` in JS (use `console.warn` or `console.error` only for real problems). No `print()` in app code except CLI status output in `main.py` with `# noqa: 25`.
- Do not create or edit any `.md` file except this `PLAN.md` when it needs a status update. No README or guide edits.
- Do not use `# noqa` to silence a finding unless the code is correct as written.

Lint loop (run after EVERY code change, no exceptions):

1. `python C:\Users\Josh\projects\josh-ai-tools\scripts\claudemd_linter.py C:\Users\Josh\projects\FOSSEverything --level strict`
2. Read `C:\Users\Josh\projects\josh-ai-tools\scripts\lint_report.txt` in full.
3. Fix every listed violation using the legend in that file. Re-run until the report says `None. Lint clean.`

The linter scans `.js`, `.css`, `.html`, `.md` too. It skips `.venv`, `node_modules`, `build`, `dist`, `vendor`, `.cache`. Put third-party minified code only in `app/web/vendor/`. Put generated screenshots only in `tests/ui/_out/` (ignored by git, see Phase 0).

When finished with any step, report in one short list: what changed, and confirmation of which tests passed.

## 1. Facts about the repository today

These were measured on 2026-10-25. Treat them as true.

- Git: branch `main`, one commit (`first commit`), working tree is dirty. It holds an unfinished PyQt6 to pywebview port: 68 files changed, all PyQt6 UI files deleted (`app/ui/*`, every `app/features/*/tab.py`, `app/core/customizable_toolbar.py`, `search_palette.py`, `spinbox.py`, `app/system/workers.py`), new untracked `app/web/`, `app/core/home_apps.py`, `app/system/settings.py`, `tests/test_web_api.py`, `tests/test_markdown_ops.py`, `.github/`, `build_exe.ps1`.
- `.venv` exists (Python 3.13.14) and has `pywebview`, `pytest`. `playwright` is NOT installed. Edge WebView2 runtime 155 is installed. Node 18 is installed. `uv` is at `C:\Users\Josh\.local\bin\uv.exe`.
- `.venv\Scripts\python.exe -m pytest -q` currently gives `263 passed, 4 skipped` in about 80 seconds. The `ops.py` modules were already made Qt-free. Keep them green at all times.
- The web layer in `app/web/` is a lossy, low-quality port:
  - `index.html` is 2266 lines with 454 inline `style="..."` attributes. `app.js` is one 164 KB file. `app.css` is 1704 lines with duplicated blocks (two `prefers-reduced-motion` and two `print` sections) and unicode divider comments.
  - `api.py` is one 2100-line class. Many methods take `arg2`, `arg3`, `arg4` (positional guesses). That causes silent JS to Python mismatches.
  - It covers only part of the original features. Measured by counting public functions in each `ops.py` on `main` that the web API never mentions: pdf 26 of 37, image 15 of 30, data 30 of 41, media 16 of 22, hash 18 of 24, qr 15 of 19, text_tools 19 of 30, playlist 19 of 20, network_monitor 17 of 17, model3d brep 10 of 10, archive 9 of 12, metadata 10 of 12, renamer 9 of 12. (Some are internal helpers; the parity gate in Phase 1 decides which count.)
  - Sizes on `main` of the original Qt tab code, for scale: pdf tab 1534 lines, image tab 1549, media tab 1088, hash tab 922, qr 741, resume 680, model3d 535 (+341 viewport), plus shared annotation canvas `app/ui/canvas.py` 1328 lines, `home_page.py` 709, `main_window.py` 764, `settings_hub.py` 552.
- The original feature list is `FUNCTIONALITY_AND_FUTURE_WORK.md` (548 lines). Read it fully before Phase 1. It is the contract for "100% of original functionality".
- Window facts: `main.py` currently opens 1320x880 with `min_size=(960, 640)`.

## 2. Decisions already made

1. Scoping and positioning: FOSSEverything is a quick offline utility suite (Swiss Army knife drawer). Heavy, dedicated media and creative studio applications (full multi-layer Photoshop-style editing, multi-track Premiere-style NLE editing, deep Acrobat-style PDF authoring, and complex CAD suites) belong to dedicated native tools like the open-source ArtCraft suite (PhotoCraft, FilmCraft, PdfCraft, CADCraft). FOSSEverything focuses on fast, reliable, single-purpose everyday tasks (PDF merge/reorder/extract, image format conversion and basic resize/crop, OCR to searchable PDF, file conversion, hash/checksums, QR code generation and scanning, batch file renaming, metadata stripping, network monitoring, archives, data tools, text tools, and word counting).
2. ArtCraft integration hub: To provide users with heavy creative tools without bloating or slowing down FOSSEverything, FOSSEverything provides an optional "External Creative Tools" launcher and installer hub in the shell (under Tools / Settings). It checks for installed ArtCraft binaries (such as `pdfcraft`, `photocraft`, `filmcraft`), offers one-click download/install guidance for them, and can launch them natively in a separate process with zero startup overhead.
3. Keep and protect: every `app/features/*/ops.py` (and `youtube_ops.py`, `network_monitor/*.py`, `model3d/brep_backend.py`), `app/core/file_formats.py`, `tool_registry.py`, `tooltips.py`, `workspace_registry.py`, `home_apps.py`, `app/system/*`, `assets/`. Keep the ops clean and green.
4. Git: keep the local changes. They contain the Qt-free `ops.py` files and passing tests. Create branch `pywebview-redesign` from the current working tree and commit a snapshot first, so every later change is a visible diff against that snapshot, and the whole branch diffs against `main`. Do not discard. (Phase 0.)
5. Rewrite from scratch: everything in `app/web/` (HTML, CSS, JS, API). Reuse text, SVG paths, and logic from the current files only by reading them. The new layout is in section 4.
6. No build step, no npm, no framework, no bundler. Plain HTML, plain CSS, plain JS loaded with ordinary `<script src>` tags in a fixed order (module scripts break on `file://`). Third-party code is allowed only as vendored files in `app/web/vendor/` and only for the 3D viewer (three.js, MIT).
7. The UI is tested in Chromium via Playwright (same engine as WebView2) with the real Python `WebApi` bridged in. A separate `--selftest` run boots the real pywebview window.
8. The supported window range is 800x600 CSS px up to 5120x1440 CSS px, device pixel ratio 1 to 2, text scale 0.85 to 1.5, five themes. Every one of those combinations must pass the automatic audit with zero errors.
9. Offline only. No CDN, no web fonts, no network calls from the UI. Fonts are the system stack.

## 3. Phase map

| Phase | Goal | Gate (must pass before next phase) |
|---|---|---|
| 0 | Branch, env, dependencies | `git branch --show-current` prints `pywebview-redesign`; `playwright` imports; baseline pytest green |
| 1 | Parity guards (inventory + tests) | `tests/test_parity_*.py` exist and FAIL listing the gaps (expected) |
| 2 | UI test harness: screenshots + audit + report | harness runs on a tiny sample page and produces PNGs + `report.json` + contact sheet |
| 3 | Design system (tokens, components, themes) | `tests/test_theme_contrast.py` and `tests/test_web_static.py` pass |
| 4 | App shell (index.html, core JS, Home, Settings, palette) | shell states pass the UI audit at all viewports |
| 5 | Python API package | `tests/test_api_contract.py` passes; old `api.py` deleted |
| 6 | All tools, in batches A to E | after each tool: its parity rows green and its UI audit green |
| 7 | Full matrix sweep + visual review loop | zero audit errors on the full matrix; review checklist answered |
| 8 | Packaging, selftest, final acceptance | section 12 checklist all true |

Commit at the end of every phase and at the end of every tool in Phase 6. Commit message format: `phaseN: short summary` or `tool(<id>): short summary`.

## 4. Target file layout

```
main.py
app/web/
  index.html                 shell only (no tool markup)
  css/tokens.css             design tokens for the default (dark) theme
  css/themes.css             one block per theme overriding tokens only
  css/base.css               reset, typography, scrollbars, focus ring
  css/layout.css             app shell grid, page, split, stack, grid-auto
  css/components.css         every shared component class
  css/tools.css              the few tool-specific rules (max 400 lines)
  js/core/icons.js           icon name -> svg path string, icon(name) helper
  js/core/dom.js             el(tag, attrs, children) helper, qs, qsa, on
  js/core/bridge.js          API calls, error toasts, job runner
  js/core/store.js           settings cache, recents, favorites
  js/core/theme.js           theme apply, custom colors, ui scale
  js/core/toast.js           toasts
  js/core/dialogs.js         confirm and prompt modals
  js/core/tooltips.js        tooltip layer fed by get_tooltips()
  js/core/router.js          view registry, tab registry, open(view, tab)
  js/core/shortcuts.js       configurable keybindings
  js/core/palette.js         Ctrl+K command palette
  js/core/dropzone.js        drag and drop routing
  js/components/*.js         file-picker, field, segmented, switch, slider, table, progress, empty-state, result-card, media-player, model-viewer, color-input
  js/tools/<tool_id>.js      one file per tool (24 tools including artcraft hub)
  js/home.js                 Home view
  js/settings.js             Settings view
  js/app.js                  boot and window.FOSS test hooks
  vendor/three/              three.js 0.147.0 build + OrbitControls + STLLoader + LICENSE
app/web/api/
  __init__.py                exports WebApi (composes all mixins)
  result.py                  ok(), fail(), api_method decorator, require()
  base.py                    BaseApi: window, dialogs, files, settings, recents, shell, search, tooltips, jobs, artcraft
  tool_<tool_id>.py          one mixin class per tool (23 files plus base)
app/system/jobs.py           JobRunner (threads, progress, cancel)
scripts/parity_inventory.py  builds the parity JSON files from `main`
tests/
  fixtures.py                generates sample files into tmp dirs
  test_api_contract.py
  test_web_static.py
  test_theme_contrast.py
  test_parity_ops.py
  test_parity_ui.py
  test_parity_doc.py
  test_native_boot.py
  parity/                    generated and hand-filled JSON
  ui/
    harness.py  audit.js  pixel_checks.py  contact_sheet.py  conftest.py
    test_ui_shell.py  test_ui_tools.py  scenarios/<tool_id>.py
    audit_allow.json
    _out/                    generated, git-ignored
```

The owner approved a full restructure, so the deletions of `app/web/api.py`, `app/web/app.js`, `app/web/app.css` and the old `index.html` content are authorized.

## 5. Phase 0: branch, environment, dependencies

Run these in order from `C:\Users\Josh\projects\FOSSEverything`.

1. `git switch -c pywebview-redesign`
2. Append these lines to `.gitignore`: `tests/ui/_out/`, `tests/parity/_cache/`.
3. `git add -A` then `git status --short` and confirm nothing from `.venv`, `build`, `dist` is staged (they are git-ignored). Commit: `git commit -m "snapshot: partial pywebview port before redesign"`.
4. Add dev dependencies: `uv add --dev playwright pytest-timeout`. If `uv` fails with a network error, run `.venv\Scripts\python.exe -m pip install playwright pytest-timeout` and add `"playwright>=1.45"` and `"pytest-timeout>=2.3"` to `[dependency-groups] dev` in `pyproject.toml` by hand.
5. Browser: the tests use the installed Edge (same Chromium engine as WebView2) through `channel="msedge"`. Verify with `.venv\Scripts\python.exe -c "from playwright.sync_api import sync_playwright as p; x=p().start(); b=x.chromium.launch(channel='msedge'); print(b.version); b.close(); x.stop()"`. If that raises, run `.venv\Scripts\python.exe -m playwright install chromium` and use the bundled Chromium instead (the harness in Phase 2 tries `msedge` first, then bundled).
6. Add a `[tool.pytest.ini_options]` section to `pyproject.toml` with `markers = ["ui_full: full viewport matrix (slow)", "native: boots the real pywebview window"]` and `timeout = 300`.
7. Run the lint loop. On 2026-10-25 the strict linter reports 210 violations: 119 in `ops.py` files, 38 in `app/web/api.py`, 23 in `app/web/app.js`, the rest in a few tests and `network_monitor`/`model3d` files. Files under `app/web/` are deleted later, so skip them. Fix the others now without changing behavior (comment trimming, type hints, import placement). Re-run `.venv\Scripts\python.exe -m pytest -q` after each file group.
8. Gate: `.venv\Scripts\python.exe -m pytest -q` still reports 263 passed. Commit `phase0: env and lint`.

## 6. Phase 1: parity guards (build them BEFORE any UI work)

Purpose: "100% of original functionality" must be machine-checked, not hoped for. There are four guards. All four read `main` through `git show main:<path>` so they never depend on the working tree.

### 6.1 Script `scripts/parity_inventory.py`

Typed Python, run as `.venv\Scripts\python.exe scripts/parity_inventory.py`. It writes four files into `tests/parity/`. Use `subprocess.run(["git", "show", f"main:{path}"], capture_output=True, text=True)` to read files and `git ls-tree -r main --name-only` to list them. Use `ast` for Python and `re` for strings.

1. `ops_inventory.json`: for every file on `main` matching `app/features/*/*.py` except `tab.py` and `viewport.py` and `__init__.py`, plus `app/core/*.py` (except Qt-only: `customizable_toolbar.py`, `search_palette.py`, `spinbox.py`) and `app/system/shell_integration.py`: a dict `{module_path: {function_name: [param_names]}}` for every top-level `def` whose name does not start with `_`, and for every public method of top-level classes as `Class.method`.
2. `tab_calls.json`: for every file on `main` named `tab.py` or in `app/ui/` (`home_page.py`, `main_window.py`, `settings_hub.py`, `setup_wizard.py`, `canvas.py`, `screenshot_dialog.py`, `file_association_settings.py`): parse with `ast`; collect every name imported from `app.features.*`, `app.core.*`, `app.system.*` (both `from X import a, b` and `import X`, then `X.attr(...)` call sites). Output `{tab_file: sorted list of "module_path:name"}`. This is the exact set of backend functions the original GUI used.
3. `qt_inventory.json`: for every `tab.py` and `app/ui/*.py` on `main`, extract with regex all literal strings from: `QPushButton("..."`, `QToolButton`, `QCheckBox`, `QRadioButton`, `QGroupBox`, `QAction`, `addTab(<widget>, "...")`, `addItem("...")` / `addItems([...])` literal lists, `setPlaceholderText("...")`, `setToolTip("...")`, `QLabel("...")` with at least 4 characters, `QKeySequence("...")`, `setShortcut("...")`. Output `{file: {"buttons": [...], "checks": [...], "radios": [...], "groups": [...], "tabs": [...], "combo_items": [...], "placeholders": [...], "tooltips": [...], "labels": [...], "shortcuts": [...]}}`. Normalise each string with `calc_norm_label(text)`: lowercase, remove `&`, remove trailing `...`, remove trailing `:`, collapse spaces, replace `&&` with `&`.
4. `doc_features.json`: parse `FUNCTIONALITY_AND_FUTURE_WORK.md` from the working tree. For every `## <section>` take the lines under `### Current functionality`; every top-level list item (line starting with `- `, including its indented continuation lines) is one feature. Give it id `<section_slug>-<NN>` (slug = lowercase section title with non-alphanumerics replaced by `_`, NN = two-digit order). Output `{id: {"section": ..., "text": first 200 characters of the item}}`. Also write a skeleton `tests/parity/feature_map.json` (only if it does not exist) with `{id: null}` for every id. Never overwrite a hand-filled map.

Gate 6.1: the script runs, all four JSON files exist, `doc_features.json` has at least 250 ids (count printed by the script).

### 6.2 Tests

- `tests/test_parity_ops.py`:
  - Test A (ops kept): for every function in `ops_inventory.json`, import the module from the working tree (same path) and assert the function exists and its parameter names are identical in order to `main`. Failure message lists every mismatch. This protects the headless layer.
  - Test B (GUI coverage): for every `module_path:name` in `tab_calls.json`, read all files under `app/web/api/` (and `app/web/api.py` while it still exists) as text and assert the name appears at least once as a whole word. Names in `tests/parity/allowlist.json` (format `{"module:name": "one-line justification"}`) are skipped. Functions corresponding to intentionally omitted heavy studio features (such as annotation canvas painting, Ghostscript compression presets, multi-track timeline composition, or complex PDF form building that belong in ArtCraft) are documented and placed in `allowlist.json`.
- `tests/test_parity_ui.py` (marker none, runs in the UI harness once Phase 2 exists): for each tool, open the view in the harness, open every tab, and collect the visible text, `title`, `aria-label`, `placeholder`, and `value` of every element, lowercased. For every normalised string in that tool's `qt_inventory.json` entry (`buttons`, `checks`, `radios`, `groups`, `tabs`, `combo_items`, `shortcuts` excluded) assert it appears as a substring of the collected text, OR a rename entry exists in `tests/parity/label_map.json` (`{"old label": "data-testid of the control that replaced it"}`), and that `data-testid` exists in the DOM. Labels that are dynamic (contain `{`) or from streamlined heavy tools are mapped in `label_map.json`.
- `tests/test_parity_doc.py`: load `feature_map.json`. Every id in `doc_features.json` must map to an object `{"view": "<tool_id>", "tab": "<tab id or empty>", "testid": "<data-testid>"}` or to `{"scenario": "<scenario function name>"}` (a Playwright scenario that exercises the feature end to end). Items delegated to ArtCraft external launcher map to `{"view": "artcraft", "tab": "", "testid": "artcraft-launch-<app>"}`. Assert there are no null entries, every `view` is a registered tool, and every `testid` exists in the DOM of that view/tab (checked through the harness). Scenario names must exist in `tests/ui/scenarios/<tool>.py`.

At the end of Phase 1 all three parity tests exist and fail with long gap lists. That is the expected state. They turn green during Phase 6. Mark `test_parity_ui.py` and `test_parity_doc.py` with `pytest.mark.skip` ONLY until Phase 2 delivers the harness, then remove the skip.

Commit `phase1: parity guards`.

## 7. Phase 2: UI test harness (screenshots and automatic analysis)

Screenshots plus analysis are part of the normal test run, not a manual step. Build the harness now, on a throwaway sample page, so it is proven before the real UI exists. Delete the sample page after the gate.

### 7.1 Browser session (`tests/ui/harness.py`)

Typed functions, no classes with inheritance. Required functions:

- `launch_browser(playwright) -> Browser`: try `chromium.launch(channel="msedge", args=ARGS)`; on exception try `chromium.launch(args=ARGS)`. `ARGS = ["--allow-file-access-from-files", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--force-color-profile=srgb", "--font-render-hinting=none"]`. Headless.
- `make_page(browser, api, viewport, theme, ui_scale) -> Page`: `viewport` is a dict `{"id","w","h","dpr"}`. Create a context with `viewport={"width":w,"height":h}`, `device_scale_factor=dpr`, `reduced_motion="reduce"`, `locale="en-US"`. Call `context.expose_function("__py_call", handler)` where `handler(name: str, args_json: str) -> str` does `json.loads(args_json)`, calls `getattr(api, name)(*args)`, and returns `json.dumps(result, default=str)`. Wrap in try/except returning `json.dumps({"ok": False, "error": str(exc)})`. Add an init script that defines `window.pywebview = {api: new Proxy({}, {get: (t, name) => (...args) => window.__py_call(String(name), JSON.stringify(args)).then(JSON.parse)})}` and, on `DOMContentLoaded`, dispatches `new Event("pywebviewready")`. Add a second init script that writes the chosen theme and scale into the settings the app reads (call `api.set_setting` from Python before navigation instead: `api.set_setting({"key": "theme", "value": theme})` and `ui_scale`). Navigate to `Path("app/web/index.html").resolve().as_uri()`. Wait for `window.FOSS && window.FOSS.ready === true` (the boot code sets it).
- Collect problems on every page: `page.on("console")` for type `error`, `page.on("pageerror")`, `page.on("requestfailed")`; keep them in a list on the session dict. Any entry is an audit error (check id `A14`).
- Dialog answers: the API has a private list `_dialog_answers` (see Phase 5). Scenarios append paths to it from Python before clicking a Browse button. Real dialogs are never opened in tests.
- `capture(session, view, state, tag) -> dict`: (1) wait for network idle and two animation frames, (2) `page.screenshot(path=..., full_page=False)` into `tests/ui/_out/<run_id>/<viewport_id>/<theme>-<scale>/<view>__<state>__<tag>.png`, (3) run `audit.js` through `page.evaluate`, (4) run `pixel_checks.analyze(png_path)`, (5) scroll the main scroller (`#view-root .scroll-main`) to its bottom, screenshot again with tag `bottom`, audit again, (6) return a record `{"view","state","tag","viewport","theme","scale","png","findings":[...]}`. Write a record list to `report.json`.
- `write_report(run_dir, records) -> None`: writes `report.json`, `findings.txt` (grouped by check id, counts, then up to 5 example lines per id, each line `view/state @ viewport: selector: message`), and calls `contact_sheet.build(run_dir)`.
- `run_id` is `time.strftime("%Y%m%d-%H%M%S")`. After each run copy the directory path into `tests/ui/_out/latest.txt`.

### 7.2 Viewport matrix

Define in `tests/ui/harness.py` as the constant `VIEWPORTS` (CSS px, dpr):

| id | w x h | dpr | represents |
|---|---|---|---|
| min | 800x600 | 1 | smallest supported window |
| s960 | 960x640 | 1 | small laptop window |
| xga | 1024x768 | 1 | old 4:3 |
| hd720 | 1280x720 | 1 | 1080p screen at 150% scaling |
| wxga | 1366x768 | 1 | common laptop |
| hd900 | 1440x900 | 1 | 16:10 laptop |
| d125 | 1536x864 | 1.25 | 1080p at 125% |
| fhd | 1920x1080 | 1 | desktop |
| hidpi | 1920x1080 | 2 | 4K at 200% |
| qhd | 2560x1440 | 1 | 1440p desktop |
| ultra | 3440x1440 | 1 | ultrawide |
| uhd | 3840x2160 | 1 | 4K at 100% |
| tall | 820x1180 | 1 | narrow tall window |

`QUICK = ["min", "hd720", "fhd"]` runs in the default `pytest` run. The full list runs when the `ui_full` marker is selected: `pytest -m ui_full`. Scales: default run uses scale `1.0` only; the full run also does `0.85` at `hd720` and `fhd`, and `1.25` and `1.5` at `hd720`, `hd900`, `fhd`, `qhd`. Themes: default run uses `dark` and `light`; the full run uses all five (`dark`, `light`, `solarized`, `monokai`, `cyberpunk`).

### 7.3 Automatic audit (`tests/ui/audit.js`)

ASCII-only plain JS, one function `window.__audit = function () { ... return findings; }` injected with `page.add_init_script` or `evaluate`. A finding is `{id, severity, selector, message, rect}`. `selector` is built by a helper that returns `[data-testid]` if present else `tag.class:nth-child(n)` path (max 4 levels). Only check elements that are visible: `display != none`, `visibility == visible`, `opacity > 0.05`, rect width and height > 0, and inside an element that is not `hidden`. Tolerance is 1px everywhere unless stated. All checks below are errors unless marked warn.

| id | check |
|---|---|
| A1 | `document.documentElement.scrollWidth > innerWidth + 1` or `body` scrolls vertically (`document.documentElement.scrollHeight > innerHeight + 1`). The shell must never scroll the window. |
| A2 | An element with `overflow-x: visible` whose `scrollWidth > clientWidth + 1` and which has element children or text. (Catches content spilling out of its box.) |
| A3 | A scroll-capable ancestor clips a child: for any element with overflow hidden or clip, a visible child rect extends beyond its padding box by more than 1px. Exempt `[data-overlay]`. |
| A4 | Containment: for every element with a visible border or a non-transparent background, each in-flow child (position static or relative) rect must lie inside that element's rect. Message: "child spills out of card". |
| A5 | Sibling overlap: among in-flow siblings with non-zero rects, any pair with intersection area greater than 4 px squared. Exempt `[data-overlay]`. |
| A6 | Interactive overlap: any two interactive elements (button, a[href], input, select, textarea, summary, `[role=button]`, `[role=tab]`, `[tabindex="0"]`) whose rects intersect by more than 2 px squared where neither contains the other. |
| A7 | Obscured control: for each interactive element inside the viewport, `document.elementFromPoint(centerX, centerY)` must be the element or a descendant of it. |
| A8 | Viewport escape: an element with `position: fixed` (modal, toast, tooltip, palette) must lie fully inside the viewport. Elements inside a horizontal scroller are exempt. |
| A9 | Text truncation: `scrollWidth > clientWidth + 1` on an element whose own text is clipped (overflow hidden, ellipsis, or clamp), unless it has `data-truncate-ok` AND a `title` attribute. Multi-line clamp: `scrollHeight > clientHeight + 1`. |
| A10 | Label wrap: text of `button`, `[role=tab]`, `.nav-item`, `.chip`, `.badge`, `th`, `label` spans more than one line (use `Range.getClientRects()` on the text node; count distinct tops), unless `data-wrap-ok`. |
| A11 | Text overlap: any two text-bearing leaf elements (measure with `Range` rects of their text nodes) whose rects intersect by more than 2 px squared. |
| A12 | Minimum target size: interactive elements are at least 2rem tall and 2rem wide (read the root font size in px), except `input[type=checkbox]`, `input[type=radio]` and elements with `data-dense` (those at least 1.25rem). Inline text links are exempt. |
| A13 | Spacing: two adjacent interactive siblings in one row have a gap of at least 4 px unless the parent has class `btn-group` or `segmented`. |
| A14 | Console error, page error, or failed request recorded by the session (done in Python). Allowlist: none. |
| A15 | Text size: any visible text node with computed `font-size` under 11 px. |
| A16 | Contrast: for every element with its own text node, compute the foreground (computed `color` with alpha) over the effective background (walk up ancestors, alpha-blend background colors; skip when a `background-image` is found). Ratio must be at least 4.5, or 3.0 when font-size is at least 24 px or at least 18.66 px with weight at least 700. Disabled controls and `[data-decorative]` are exempt. |
| A17 | Zero-size control: an interactive element with `display != none` and width or height of 0. |
| A18 | Broken media: `img` with `complete` and `naturalWidth == 0` and no `data-lazy`; `canvas` with width or height 0 when visible. |
| A19 | Missing test id: any interactive element inside `#view-root` without `data-testid`. |
| A20 | Missing accessible name: interactive element with no text content, `aria-label`, `aria-labelledby`, `title`, or associated `<label for>`. |
| A21 | Nested vertical scrollers: more than 2 nested elements with `overflow-y` auto or scroll along any ancestor chain. (warn) |
| A22 | Unintended inner horizontal scrollbar: an element with `overflow-x: auto|scroll` and `scrollWidth > clientWidth + 1` that does not have class `scroll-x` or `table-wrap`. |
| A23 | Wide line length: a paragraph (`p`, `.hint`, `.desc`) whose rendered width exceeds 80ch at its font size. (warn) |
| A24 | Focus visibility (test in Python, not JS): press Tab 12 times from the page start; each time `getComputedStyle(document.activeElement)` must show `outline-style != none` or a non-empty `box-shadow`. |

Allowlist: `tests/ui/audit_allow.json` is a list of `{"check": "A9", "selector": "...", "view": "...", "reason": "..."}`. Every entry needs a non-empty `reason`. The test fails if the file has more than 12 entries. Fix the UI instead of adding entries.

### 7.4 Pixel analysis (`tests/ui/pixel_checks.py`)

Typed Python using Pillow and numpy (both installed). Function `analyze(png_path: str) -> list[dict]` returns findings with ids:

- P1 (error): image is blank: grayscale standard deviation under 3.0, or fewer than 8 distinct colors after downscaling to 128 px wide.
- P2 (error): a loaded or result state looks empty: fewer than 0.4 percent of pixels differ from the median background color inside the main content region (use the right 80 percent of the image, below the top 8 percent).
- P3 (warn): content bleeding at the right or bottom edge: more than 6 consecutive rows (or columns) in the last pixel column (or row) differ from the background luminance by more than 40 levels. Indicates a clipped element.
- P4 (error): a horizontal or vertical 1 px line that spans more than 60 percent of the image width or height AND has luminance different from both neighbors by more than 60 levels, outside the sidebar/topbar border positions known from the audit (the audit reports border rects in a `data-border-rects` JSON on `document.body.dataset`, filled by `audit.js`). This detects broken or stray lines.
- P5 (error, only when `FOSS_UI_BASELINE=1`): perceptual regression: compare against `tests/ui/baselines/<same relative path>`; fail when more than 0.5 percent of pixels differ by more than 24 levels. `pytest --update-baselines` (a conftest option) copies the current screenshots into `baselines/`. Baselines are committed only after the Phase 7 review passes.

### 7.5 Contact sheets (`tests/ui/contact_sheet.py`)

`build(run_dir)` groups PNGs by viewport and writes `contact_<viewport>.png`: a grid of 4 columns, each thumbnail 480 px wide, with the file stem drawn in 14 px text above it (Pillow default font) and a red 3 px border when that state has any error finding. The last line of `findings.txt` prints the path of each sheet. When a viewer tool for images is available to you, open the contact sheets and the individual PNGs listed in `findings.txt`.

### 7.6 Test entry points

- `tests/ui/conftest.py`: session fixtures `browser`, `api` (a fresh `WebApi()` per test session with `_dialog_answers` available and the settings file pointed to a temp dir via env var `FOSS_SETTINGS_DIR`), `run_dir`, `records` (list). A final session hook calls `write_report`. Option `--update-baselines`. Fixture `fixtures` returns paths created by `tests/fixtures.py`.
- `tests/fixtures.py`: one function `make_fixtures(dir: Path) -> dict[str, str]` that creates, using libraries already in the project: `sample.pdf` (3 pages, text on each, created with PyMuPDF), `scan.pdf` (1 page that is an image of text), `sample.png` (800x600 gradient plus shapes plus text, Pillow), `sample2.png`, `photo.jpg`, `tone.wav` (1 s sine, `wave` module), `clip.mp4` (1 s, 160x120, generated with `imageio_ffmpeg` and raw frames piped to ffmpeg), `sample.txt`, `data.json`, `data.yaml`, `data.csv`, `sample.md`, `sample.zip`, `cube.stl` (trimesh box), `sample.docx` (python-docx via the `docx` module), `qr.png` (made with the project's own QR ops), `manifest.sha256`. Return a dict of name to absolute path string.
- The test `tests/ui/test_ui_shell.py::test_shell_states[viewport-theme]` loops `FOSS.listStates()` for shell states; `tests/ui/test_ui_tools.py::test_tool_empty_states[...]` loops every tool and every tab. `tests/ui/scenarios/<tool_id>.py` define loaded, result, and error states (Phase 6). Every test asserts: no findings with severity `error` after removing allowlisted ones. On failure the assertion message prints the first 15 findings plus the path of `findings.txt`.

### 7.7 Gate for Phase 2

Create `tests/ui/_sample/index.html` with a deliberately broken layout (an overflowing div, two overlapping buttons, a 9 px text, low contrast text) and a good section. Run the harness on it. Expected: the audit reports A2, A5/A6, A15, A16 for the bad section and nothing for the good one; PNGs, `report.json`, `findings.txt`, and a contact sheet are written. Then delete `tests/ui/_sample/`. Run the lint loop and commit `phase2: ui harness`.

## 8. Phase 3: design system

Goal: one small set of tokens and components so every screen is consistent and no view needs its own sizing hacks. All numbers below are final.

### 8.1 Sizing model (this is what makes the UI work at any resolution)

- All sizes in CSS are in `rem`, except 1px borders, shadows, and media element sizes. Never use `px` for font-size, padding, margin, gap, width, height, or radius outside `tokens.css`. `tests/test_web_static.py` enforces this (8.6).
- Root font size: `html { font-size: calc(clamp(14px, 0.35vw + 10px, 20px) * var(--ui-scale, 1)); }`. Result: 14 px at 800 wide, about 14.8 px at 1366, about 16.7 px at 1920, 19 px at 2560, 20 px cap at 3840. `--ui-scale` is the user's text-size setting (0.85 to 1.5, default 1), set by `theme.js` on `document.documentElement.style`.
- Body text 0.9375rem. Line height 1.45. Headings use the type scale below.
- Layout never depends on viewport width alone. Panels respond to their own width with container queries (`container-type: inline-size` on `.page`, `.panel`, `.workbench`) and `@container (max-width: 56rem)` rules.
- Every flex or grid child that holds text or inputs has `min-width: 0`. Grid columns use `minmax(0, 1fr)`, never bare `1fr`.
- Every horizontal group of controls is a `.row` (flex, wrap, gap). Groups wrap instead of overflowing. Never use a fixed-width row.
- Controls never have fixed pixel widths. Inputs are `width: 100%` inside a `.field`; small numeric inputs use `width: 7rem`.

### 8.2 Tokens (`css/tokens.css`, default dark theme, `:root`)

Spacing (4 px grid at 16 px root): `--space-1: 0.25rem; --space-2: 0.5rem; --space-3: 0.75rem; --space-4: 1rem; --space-5: 1.25rem; --space-6: 1.5rem; --space-8: 2rem; --space-10: 2.5rem; --space-12: 3rem`.
Type: `--text-xs: 0.8125rem; --text-sm: 0.875rem; --text-md: 0.9375rem; --text-lg: 1.125rem; --text-xl: 1.375rem; --text-2xl: 1.75rem`. Weights: 400, 500, 600, 700 only.
Fonts: `--font-sans: "Segoe UI Variable Text", "Segoe UI", system-ui, -apple-system, Roboto, "Helvetica Neue", Arial, sans-serif; --font-mono: "Cascadia Mono", "Cascadia Code", Consolas, "Courier New", monospace`.
Radius: `--radius-sm: 0.375rem; --radius-md: 0.625rem; --radius-lg: 1rem; --radius-pill: 999px`.
Controls: `--control-h: 2.5rem; --control-h-sm: 2rem; --icon-sm: 1rem; --icon-md: 1.25rem; --icon-lg: 1.75rem`.
Layout: `--sidebar-w: clamp(14rem, 17vw, 18rem); --rail-w: 4rem; --topbar-h: 3.5rem; --page-max: 88rem; --page-pad: clamp(1rem, 2vw, 2rem)`.
Motion: `--ease: cubic-bezier(0.2, 0, 0, 1); --dur-fast: 120ms; --dur: 200ms`. `@media (prefers-reduced-motion: reduce)` sets both durations to 0ms (one block only).
Shadows: `--shadow-1: 0 1px 2px rgba(0, 0, 0, 0.35); --shadow-2: 0 8px 24px rgba(0, 0, 0, 0.4)`.

Color tokens (dark). Every semantic color comes as a triple: fill `--x`, text-on-fill `--on-x`, text-on-surface `--x-text`.

| token | dark | light |
|---|---|---|
| `--bg-app` | `#090d16` | `#f4f6fb` |
| `--bg-sidebar` | `#0d1322` | `#ffffff` |
| `--bg-surface` | `#131b2e` | `#ffffff` |
| `--bg-raised` | `#1a2540` | `#eef2f9` |
| `--bg-input` | `#0f172a` | `#f8fafc` |
| `--bg-scrim` | `rgba(3, 6, 14, 0.66)` | `rgba(15, 23, 42, 0.45)` |
| `--border` | `rgba(255, 255, 255, 0.10)` | `rgba(15, 23, 42, 0.14)` |
| `--border-strong` | `rgba(255, 255, 255, 0.22)` | `rgba(15, 23, 42, 0.30)` |
| `--text` | `#f1f5f9` | `#0f172a` |
| `--text-muted` | `#a3b1c6` | `#475569` |
| `--text-dim` (decorative only) | `#64748b` | `#94a3b8` |
| `--accent` | `#2563eb` | `#2563eb` |
| `--accent-hover` | `#3b82f6` | `#1d4ed8` |
| `--on-accent` | `#ffffff` | `#ffffff` |
| `--accent-text` | `#60a5fa` | `#1d4ed8` |
| `--success` / `--on-success` / `--success-text` | `#15803d` / `#ffffff` / `#4ade80` | `#15803d` / `#ffffff` / `#15803d` |
| `--warning` / `--on-warning` / `--warning-text` | `#f59e0b` / `#111827` / `#fbbf24` | `#f59e0b` / `#111827` / `#b45309` |
| `--danger` / `--on-danger` / `--danger-text` | `#dc2626` / `#ffffff` / `#f87171` | `#dc2626` / `#ffffff` / `#b91c1c` |
| `--info` / `--on-info` / `--info-text` | `#0369a1` / `#ffffff` / `#38bdf8` | `#0369a1` / `#ffffff` / `#0369a1` |
| `--focus` | `#93c5fd` | `#1d4ed8` |

`themes.css`: blocks `html[data-theme="light"]`, `solarized`, `monokai`, `cyberpunk` override color tokens only. Start from the colors in the current `app/web/app.css` theme blocks, then tune each theme until `tests/test_theme_contrast.py` passes. The current cyberpunk muted text (`#b5179e` on `#180b38`) fails contrast; replace it with a lighter magenta that passes. Tinted backgrounds (banners, badges) use `color-mix(in srgb, var(--danger) 16%, var(--bg-surface))`.

### 8.3 Base rules (`css/base.css`)

Reset: `*, *::before, *::after { box-sizing: border-box; }`, `body { margin: 0; }`, no global `padding: 0` on every element. `html, body { height: 100%; overflow: hidden; }`. `:focus-visible { outline: 0.125rem solid var(--focus); outline-offset: 0.125rem; }`. Scrollbars: `scrollbar-width: thin; scrollbar-color: var(--border-strong) transparent`. `button { font: inherit; }`. Disable text selection on chrome (`.sidebar`, `.topbar`, buttons) with `user-select: none`; keep it on content and results. Numbers in tables use `font-variant-numeric: tabular-nums`. `input[type=number]` hides spin arrows (`appearance: textfield`) and `dom.js` blurs a number input on `wheel` so scrolling never changes a value.

### 8.4 Layout primitives (`css/layout.css`)

| class | rule |
|---|---|
| `.app` | grid: columns `var(--sidebar-w) minmax(0, 1fr)`, rows `var(--topbar-h) minmax(0, 1fr)`, `height: 100dvh`, `overflow: hidden`. Sidebar spans both rows. At `max-width: 1100px` the sidebar becomes an icon rail (`--rail-w`): labels hidden, each item keeps `title`. A topbar button expands it as an overlay with `.scrim`. User toggle is saved in settings key `sidebar_collapsed`. |
| `.scroll-main` | the `#view-root` element: `overflow: auto; scrollbar-gutter: stable; min-height: 0`. It is the only vertical scroller of a normal page. |
| `.page` | `max-width: var(--page-max); margin-inline: auto; padding: var(--page-pad); display: flex; flex-direction: column; gap: var(--space-5)`. Normal tool pages. |
| `.page.wide` | no max width. |
| `.workbench` | a tool that needs a full-height stage (PDF viewer, image editor, 3D, media, resume): `height: 100%; display: grid; grid-template-columns: auto minmax(0, 1fr) minmax(16rem, 22rem); grid-template-rows: auto minmax(0, 1fr); gap: var(--space-3); padding: var(--space-3)`. Panels inside scroll with `.scroll-y`. Below container width 56rem it becomes a single column and the page scrolls (`height: auto`). |
| `.split` | `display: grid; grid-template-columns: minmax(18rem, 26rem) minmax(0, 1fr); gap: var(--space-5); align-items: start`. Inputs left, preview or result right. Below container width 56rem: one column. `.split.even` uses two equal `minmax(0, 1fr)` columns. |
| `.grid-auto` | `display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); gap: var(--space-4)`. |
| `.stack` | `display: flex; flex-direction: column; gap: var(--space-4)`. `.stack-sm` uses `--space-2`. |
| `.row` | `display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-3)`. `.row > .grow { flex: 1 1 12rem; min-width: 0 }`. `.row.end { justify-content: flex-end }`. |
| `.scroll-x`, `.scroll-y` | `overflow-x: auto` / `overflow-y: auto` with `min-width: 0` / `min-height: 0`. Only these classes (and `.table-wrap`, `.tabs`) may scroll. |

Tool pages order: `.page-head` (title `--text-xl` weight 700, one-line description in muted `--text-sm`, optional `.row.end` actions) then `.tabs` then the active panel. Description text is at most 160 characters.

### 8.5 Component catalog (`css/components.css` plus `js/components/*.js`)

Build each as a JS function returning a DOM node (using `el()`), with the listed class names. Every interactive element gets a `data-testid` passed by the caller. Every icon-only button gets `aria-label` and `title`.

| component | classes and rules |
|---|---|
| Button | `.btn` base (height `--control-h`, padding-inline `--space-4`, radius `--radius-md`, `white-space: nowrap`, icon gap `--space-2`). Variants `.btn-primary` (accent fill, `--on-accent`), `.btn-secondary` (surface, border), `.btn-ghost`, `.btn-danger`. Sizes `.btn-sm` (`--control-h-sm`). `.btn-icon` square. `.btn-group` joins buttons with 0 gap and shared borders. Disabled: opacity 0.5, `cursor: not-allowed`, still readable. Busy: spinner replaces icon, button disabled. |
| Field | `.field` grid: `label` (`--text-sm`, weight 500), control, `.hint` (`--text-xs`, muted). Error state `.field.invalid` shows `.hint` in `--danger-text`. |
| Input, select, textarea | height `--control-h` (textarea min 6rem, `resize: vertical`), `--bg-input`, border, radius `--radius-md`, focus ring. Select has a custom chevron via background SVG data URI (ASCII). |
| File picker | `.file-picker`: dashed-border drop target containing an icon, a path line (`direction: rtl; text-overflow: ellipsis` is NOT allowed; show the file name big and the folder small, both with `title` and `data-truncate-ok`), a "Choose file" `.btn-secondary`, and a clear button. Multi-file variant lists files in a `.file-list` with remove buttons and reorder handles. Calls `select_file` or `select_files`. Accepts drag and drop. |
| Segmented control | `.segmented` of `button[role=radio]`; used for 2 to 5 mutually exclusive options instead of radio buttons. |
| Switch | `.switch` label wrapping a visually hidden checkbox. Used instead of bare checkboxes for on/off options. Checkboxes remain for lists and tables. |
| Slider | `.slider-field`: range input plus a numeric `output` showing the value with unit; both stay in sync. |
| Table | `.table-wrap.scroll-x` containing `table.table`: sticky header, row hover, `font-variant-numeric: tabular-nums`, status cells use badges. Row count over 500: render the first 500 and a "Show more" button. |
| Badge and chip | `.badge` (`--text-xs`, pill, tinted background, status variants), `.chip` (filter chip, toggle with `aria-pressed`). |
| Banner | `.banner.info|success|warning|danger`: icon, text, optional action. Inline status for a tool result. |
| Result card | `.result-card`: heading, key-value list, "Open file" and "Show in folder" buttons (`open_path`, `open_folder`), optional preview image. |
| Empty state | `.empty`: centered icon (`--icon-lg`, dim), title, one-line hint, optional primary action. Every list, preview, and canvas has one. |
| Progress | `.progress`: bar with `--accent`, determinate value from jobs, text line (percent, message), Cancel button when the job is cancellable. |
| Tabs | `.tabs.scroll-x` of `button[role=tab]`, `white-space: nowrap`, active underline in `--accent`, edge fade mask; the active tab is scrolled into view; arrow keys move between tabs. |
| Card and panel | `.card` (surface, border, radius `--radius-lg`, padding `--space-5`), `.card-title`, `.panel` (card without shadow, container). Nested cards are not allowed. |
| Tooltip | `tooltips.js` renders one floating `.tooltip` positioned inside the viewport (flip when near an edge). Text comes from `get_tooltips()` by key `data-tip="<key>"`; fall back to `title`. 500 ms delay. |
| Toast | bottom right (bottom center below 900 px width), max 4 stacked, 5 s auto close (errors 10 s), close button, optional action button. |
| Modal | `.modal` centered, max width 32rem, focus trap, Esc closes, scrim click closes unless `persistent`. Used by confirm and prompt dialogs. |
| Kbd | `.kbd` chip for shortcuts. |
| Color input | `.color-input`: swatch button (native `input[type=color]` hidden inside), hex text input, both synced. |
| Icons | `icons.js` holds Material-style 24x24 filled paths (copy the 23 nav icon paths from the current `index.html` and add the ones you need in the same style). `icon(name, size)` returns an inline `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">`. Never use an external sprite (`<use href>` is blocked on `file://`). |

Inline styles are forbidden: no `style="..."` in HTML and no `.style.cssText` or `setAttribute("style")` in JS. The only allowed dynamic style writes are `element.style.setProperty("--name", value)` for custom properties (progress percent, swatch color, canvas size) and `element.style.transform` for canvas pan and zoom.

### 8.6 Static tests (`tests/test_web_static.py`)

These run without a browser and must pass:

1. No `style="` in any `app/web/**/*.html` file.
2. In `app/web/js/**` (excluding `vendor`): no match for `\.style\.cssText`, `setAttribute\(\s*["']style`, and every `.style.` assignment must be `.style.setProperty(` with a `--` name or `.style.transform`.
3. In `app/web/css/**` outside `tokens.css` and `themes.css`: no hex colors (`#[0-9a-fA-F]{3,8}\b` outside `url(`), no `rgb(`/`rgba(`/`hsl(` literals except inside `color-mix` over `var(...)` tokens, and no `px` units except `1px` and `0.5px` borders, `@media`/`@container` px breakpoints, and `min()`/`clamp()` px terms in `tokens.css`.
4. No duplicate `@media (prefers-reduced-motion` block; each `@keyframes` name is unique.
5. All files in `app/web` (except `vendor`) are ASCII.
6. `index.html` has exactly the script order listed in section 9.1 and no inline `<script>` bodies.
7. Every `data-testid` string literal in `js/tools/<id>.js` starts with `<id>-` (tool id, with `_` kept).

### 8.7 Theme contrast test (`tests/test_theme_contrast.py`)

Typed Python. Parse `tokens.css` and `themes.css` into a dict per theme (dark = tokens, other themes = tokens overlaid with their block). Implement `calc_luminance(hex)`, `calc_contrast_ratio(fg, bg)` (WCAG formula), and alpha blending for `rgba(...)`. Assert for every theme:

| pair | minimum |
|---|---|
| `--text` on `--bg-app`, `--bg-sidebar`, `--bg-surface`, `--bg-input`, `--bg-raised` | 7.0 |
| `--text-muted` on those five | 4.5 |
| `--accent-text` on `--bg-app`, `--bg-surface`, `--bg-raised` | 4.5 |
| `--on-accent` on `--accent` and on `--accent-hover` | 4.5 |
| `--on-success`/`--success`, `--on-warning`/`--warning`, `--on-danger`/`--danger`, `--on-info`/`--info` | 4.5 |
| `--success-text`, `--warning-text`, `--danger-text`, `--info-text` on `--bg-surface` | 4.5 |
| `--text-dim` on `--bg-surface` | 3.0 |
| `--border-strong` blended over `--bg-surface` against `--bg-surface` | 1.5 |
| `--focus` on `--bg-surface` | 3.0 |

Gate for Phase 3: `tests/test_web_static.py` and `tests/test_theme_contrast.py` pass and the lint loop is clean. Commit `phase3: design system`.

## 9. Phase 4: application shell

### 9.0 Backend prerequisite

The shell calls base API methods. Before writing any JS, create `app/web/api/result.py`, `app/web/api/base.py` (section 10.2 only), `app/web/api/__init__.py` (a `WebApi` made of `BaseApi` alone for now) and `app/system/jobs.py` (section 10.1 rule 3). Rewrite `main.py` as in 9.4. Section 10 then adds the per-tool mixins.

### 9.1 `index.html`

Contains only: `<head>` (charset, viewport meta, title, the five stylesheet links in order `tokens, themes, base, layout, components, tools`), then body markup: `<div class="app">` with `<aside class="sidebar" id="sidebar">`, `<header class="topbar">`, `<main id="view-root" class="scroll-main" tabindex="-1">`, and hosts `<div id="toast-host">`, `<div id="modal-host">`, `<div id="palette-host">`, `<div id="tooltip-host">`. Then scripts in this exact order, all with `defer` removed (plain scripts at the end of body): `js/core/icons.js, dom.js, bridge.js, store.js, theme.js, toast.js, dialogs.js, tooltips.js, router.js, shortcuts.js, palette.js, dropzone.js`, then `js/components/*.js` (alphabetical), then `js/tools/*.js` (alphabetical), then `js/home.js, js/settings.js, js/app.js`. Third-party: `vendor/three/*` is loaded lazily by `model3d.js` by inserting a script element, not in the initial list.

### 9.2 Core JS contracts

- Global namespace `window.FOSS = {}`. Each core file is an IIFE that attaches to it. Example names: `FOSS.dom.el`, `FOSS.api(name, params)`, `FOSS.toast.show`, `FOSS.router.open`.
- `FOSS.api(name, params)`: calls `window.pywebview.api[name](params)`, awaits `pywebviewready` first, returns the result object. If `result.ok === false` it shows an error toast with `result.error` and still returns the result so callers can branch. If the call throws, it shows a toast and returns `{ok: false, error: <message>}`. All calls pass ONE object argument.
- `FOSS.job(name, params, {onProgress})`: calls `job_start`, polls `job_poll` every 250 ms, drives a `.progress` component, supports Cancel via `job_cancel`, resolves with the final result object.
- Tool registration: each `js/tools/<id>.js` calls `FOSS.router.register({id, title, navName, category, icon, workbench: false, tabs: [{id, label, render(panel, ctx)}], onFiles(paths, ctx), onShow(ctx), onHide(ctx)})`. `render` is called once per tab, lazily, the first time the tab opens. `ctx` provides `FOSS.api`, `FOSS.job`, `toast`, `confirm`, and `state` (a plain object persisted in memory per tool).
- Test hooks (in `app.js`): `FOSS.ready = true` after boot; `FOSS.listStates()` returns `[{view, state}]` for `home`, `home-empty-search`, `palette-open`, `settings-<section>`, `modal-confirm`, `toast-stack`, `sidebar-rail`, and `<tool>:<tab>` for every tool tab; `FOSS.openState(view, state)` navigates there; `FOSS.selfTest()` returns the current audit findings (it calls `window.__audit` if present) plus a list of API names that failed `ping`.
- Settings keys (stored through `get_setting`/`set_setting` in `app/system/settings.py`): `theme`, `custom_colors`, `ui_scale`, `sidebar_collapsed`, `favorites` (list of tool ids), `recent_files`, `recent_outputs`, `home_favorites_only`, `home_category`, `keybindings`, `tool_state.<id>` (last used folders and options), `renamer_presets`, `renamer_plans`, `resume_profiles`, `resume_versions`, `network_history_enabled`.

### 9.3 Shell features (all must exist; all from the original app)

1. Sidebar: brand (icon + "FOSSEverything"), "All tools" item, then groups Documents, Visuals, Media, Utilities, Data with one item per tool. Nav labels use `nav_name` (at most 16 characters, add the field to `app/core/home_apps.py`). Active item highlighted; keyboard focusable; `title` = full tool name. Rail mode as in 8.4.
2. Topbar: sidebar toggle, breadcrumb `FOSSEverything / <tool title>` (truncates with `title`), search button (opens palette; shows `Ctrl+K`; collapses to icon under 900 px width), favorites bar (pinned tools as icon buttons, max 6 visible, extra go into an overflow menu; a pin button on every tool header toggles pinning), theme quick switch (icon button with a menu of 5 themes), settings button.
3. Home view: hero (title and one-line subtitle), prominent search input (same engine as the palette, inline results), category chips (All, Documents, Images, Media, Utilities, Data) plus a "Favorites only" switch, tile grid (`grid-auto` with `minmax(15rem, 1fr)`): artwork from `assets/home/<id>.<ext>` (16:9, `object-fit: cover`, `aspect-ratio`), title, 2-line description (clamp with `title`), star button for favorite. Below the grid: "Recent files" and "Recent outputs" lists (from settings, each row: name, folder, time, open button). Arrow keys move focus between tiles, Enter or Space opens. Drag a file anywhere on Home or any view: `dropzone.js` shows a full-window drop overlay, then calls `route_file` and opens the right tool with `onFiles`. Routing rules come from `app/core/workspace_registry.py` and `app/system/shell_integration.py::resolve_workspace_id`.
4. Command palette (`Ctrl+K`, also `Ctrl+P`): modal with input and ranked results list (up to 12), arrow keys and Enter, each result shows icon, name, category, and matching feature. Uses API `search_tools` (the existing ranking in `app/core/tool_registry.py` and `tooltips.py`, which understands aliases, typos, and `pdf:` / `images:` prefixes). Choosing a result opens the tool and invokes the matched action by clicking the control whose `data-testid` equals the result's `action_id`.
5. Settings view with sections (left list, right content; stacked under 56rem): Appearance (theme select, text size slider 0.85 to 1.5 with live preview, "Custom colors (advanced)" with a color input per token group and a reset button), Home and view (favorites-only default, default category, recents length, clear recents), Creative suites & ArtCraft (external tool launcher and manager: status indicators for detected ArtCraft executables such as PdfCraft, PhotoCraft, FilmCraft; install instructions and download links; quick launch buttons that spawn the tools with native speed), Keybindings (table of actions with current shortcut, a "Record" button that captures the next key combination, conflict warning, per-row Reset, global Reset all), File associations and shell (register and unregister the Windows context menu, list extensions with default-status badges, set default for selected extensions, manual instructions text), Privacy and data (open data folder, reset all settings with confirm), About (version from `pyproject.toml`, license AGPL-3.0-or-later, "No telemetry" statement).
6. Keyboard shortcuts: read ALL `QKeySequence(...)` and `setShortcut(...)` strings from `tests/parity/qt_inventory.json` (key `shortcuts`) and implement each one. Minimum set: Home, Settings, Find a tool, fullscreen (`F11`, calls `toggle_fullscreen`), text size larger, smaller, reset, tab cycling (`Ctrl+Tab`, `Ctrl+Shift+Tab`), image `Ctrl+R` / `Ctrl+Shift+R`, `Ctrl+C` copy canvas, undo, redo. Keybinding ids are stable strings like `nav.home`. Overrides persist in `keybindings`.
7. First run: if setting `first_run_done` is missing, show a one-time welcome modal that mirrors `app/ui/setup_wizard.py` on `main` (read it with `git show main:app/ui/setup_wizard.py`): offer shell integration and file associations, then set `first_run_done`.
8. Single instance and launch arguments: `main.py` accepts a file path, `--ocr`, `--hash`, `--register-shell`, `--unregister-shell`, `--selftest`. A second launch forwards its file and mode to the running instance through `app/system/shell_integration.py` (`try_forward_to_running_instance`, `start_ipc_server`) and exits. The server thread calls `window.evaluate_js("FOSS.openPaths(<json>, <mode>)")`.

### 9.4 `main.py`

Typed. Set the AppUserModelID as today. Window: title `FOSSEverything`, `url` = absolute path to `app/web/index.html`, `js_api=WebApi()`, size `width=min(1400, int(screen.width * 0.85))`, `height=min(900, int(screen.height * 0.85))` using `webview.screens[0]`, `min_size=(800, 600)`, `background_color` = the saved theme's `--bg-app` value read from settings (default `#090d16`), `text_select=True`. `--selftest`: start the window hidden-compatible, wait for `FOSS.ready`, run `FOSS.selfTest()` through `window.evaluate_js`, write the JSON result to the path in env var `FOSS_SELFTEST_OUT`, destroy the window, exit code 0 when `findings` has no errors and `missing_api` is empty, else 1.

### 9.5 Phase 4 gate

The shell states from `FOSS.listStates()` pass `tests/ui/test_ui_shell.py` at the QUICK viewports with zero errors, then at all `VIEWPORTS` with `-m ui_full`. Open the contact sheets and fix visual problems (Phase 7 checklist, section 12.2) for the shell now, because every tool inherits it. Commit `phase4: shell`.

## 10. Phase 5: Python API package

Delete `app/web/api.py` after the package replaces it. Do this phase before the tool views so they have a stable backend.

### 10.1 Rules

1. One public method signature shape for ALL tool methods: `def pdf_split(self, params: dict[str, Any]) -> dict[str, Any]:`. The JS side sends exactly one object. No positional extras, no `arg2`. Inside, read keys with `require(params, "file_path", "ranges")` from `result.py`, which raises `ParamError("missing: ranges")`; optional keys use `params.get("dpi", 150)`.
2. `result.py` provides: `ok(**data) -> dict` (returns `{"ok": True, **data}`), `fail(message: str, code: str = "error") -> dict`, and the decorator `api_method` which wraps a method, catches every exception, writes the traceback to `settings_dir/app.log` through the `logging` module, and returns `fail(<short human sentence>, code=<exception class name>)`. Exceptions never reach JS. All methods use `@api_method`.
3. Long operations (anything that can exceed about 1 second: batch jobs, OCR, media, background removal, hashing a directory, converting, network fetches, archive creation) are started with `job_start({"method": "<api method name>", "params": {...}})` and polled with `job_poll({"id": ...})` (returns `{"ok": true, "state": "running|done|failed|cancelled", "progress": 0.0..1.0, "message": str, "result": {...}|null}`) and `job_cancel({"id": ...})`. The job runs the named method in a thread through `app/system/jobs.py::JobRunner`. Methods that support progress take a `_progress` callable from the runner (`self._job_ctx` thread-local) and call `progress(fraction, message)` and check `cancelled()`. This replaces `app/system/workers.py` (QThread) from `main`. Each worker class on `main` (`git show main:app/system/workers.py` and its users) maps to a job.
4. Never store non-JSON objects in public attributes of `WebApi` (pywebview walks public attributes). All state is in underscore attributes: `_window`, `_jobs`, `_dialog_answers`, `_settings`.
5. Return only JSON-safe values (str, int, float, bool, list, dict, None). Images are returned as `data:image/png;base64,...` strings; large previews are downscaled so the longest side is at most 2400 px. Files are referenced by absolute path strings.
6. Destructive operations default to a NEW output file. If `output_path` is missing the API creates `<name>_<suffix>.<ext>` next to the input and appends ` (1)`, ` (2)` on collision. Never overwrite an input.
7. After any successful call that writes a file, the base class records it in `recent_outputs` (cap 50, newest first). Opening files records `recent_files` (cap 50).
8. Method naming: `<tool_id>_<verb>` (`pdf_merge`, `hash_dir`, `qr_generate`). Base methods have no prefix.

### 10.2 `BaseApi` methods (all `params: dict`, all `@api_method`)

`ping`, `get_apps` (from `home_apps.py`, with artwork URL as a `file:///` URL), `search_tools` (`{"query"}`), `get_tooltips`, `get_setting`, `set_setting`, `get_settings_all`, `reset_settings`, `select_file` (`{"file_types": [...], "title": str}`), `select_files`, `select_folder`, `select_save_path` (`{"default_name", "file_types"}`), each returning `{"ok": true, "paths": [...]}` (empty list on cancel, `"cancelled": true`); they pop from `_dialog_answers` first when it is non-empty (test hook), `read_text_file`, `write_text_file`, `open_path`, `open_folder`, `copy_to_clipboard` (text), `copy_image_to_clipboard` (data URL), `paste_image_from_clipboard`, `toggle_fullscreen`, `route_file` (`{"path", "mode"}` returns `{"tool_id"}`), `get_recents`, `clear_recents`, `shell_register`, `shell_unregister`, `shell_get_associations`, `shell_set_associations`, `shell_manual_instructions`, `get_version`, `job_start`, `job_poll`, `job_cancel`, `get_data_dir`, `get_artcraft_status`, `launch_artcraft_app` (`{"app_name"}`).

### 10.3 Per-tool mixins

Create `tool_<tool_id>.py` for all 23 tool ids listed in section 11. Each mixin exposes ONE API method for EVERY function in `tab_calls.json` that the original tab used, plus methods the new UI needs. The name mapping is the function name prefixed by the tool id unless it already starts with it (example: `pdf/ops.py::add_image_watermark` becomes `pdf_add_image_watermark`). Parameter keys equal the ops parameter names exactly, so the mapping is mechanical: `params` keys = the ops function's parameters. Binary arguments (bytes) travel as base64 strings or file paths; the method decodes them.

### 10.4 Contract test (`tests/test_api_contract.py`)

1. Introspect `WebApi`: every public callable (not starting with `_`) has exactly the parameters `(self, params)`, annotation `dict[str, Any]`, and return annotation `dict[str, Any]`.
2. No two mixins define the same method name.
3. For every ops function listed in `tab_calls.json`, a method exists whose body text contains that function name (parity Test B passes).
4. For every tool: call at least one read-only method with the fixtures and assert `ok` is true and the result is JSON-serializable (`json.dumps`).
5. Calling any method with `{}` returns `ok: false` and never raises.
6. `job_start`/`job_poll`/`job_cancel` round trip works with a fake slow method.

Gate for Phase 5: `tests/test_api_contract.py` passes, `tests/test_web_api.py` is rewritten to the new shapes (keep every behavior it covered) and passes, parity Test A and Test B in `tests/test_parity_ops.py` pass with an empty allowlist, the old `app/web/api.py` is deleted. Commit `phase5: api package`.

## 11. Phase 6: the tools

### 11.1 Procedure for EVERY tool (repeat for all 24 tools)

1. Read the original: `git show main:app/features/<id>/tab.py` completely. Read the tool's section in `FUNCTIONALITY_AND_FUTURE_WORK.md`. Open the tool's entries in `tests/parity/qt_inventory.json` and `tab_calls.json`. For utilities, list the controls and options. Heavy editor features (drawing canvases, multi-track video timelines, deep PDF form builders) are streamlined out per Section 2 Decision 1 and Section 11.3; record any replaced/omitted complex UI in `tests/parity/label_map.json` and `tests/parity/allowlist.json`.
2. Complete the API mixin `app/web/api/tool_<id>.py` (section 10.3). Add or extend `tests/test_api_contract.py` cases for the tool.
3. Write `app/web/js/tools/<id>.js` with the tab list from the table in 11.3. Use only components from 8.5. Every interactive element has `data-testid` formed as `<id>-<tab>-<action>` (example `pdf-merge-run`). Tooltips: set `data-tip` keys from `app/core/tooltips.py`; if a key is missing, add the text to `tooltips.py` (it is the central dictionary) and use the key.
4. Write `tests/ui/scenarios/<id>.py`: `SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], WebApi], None]]]`. Each scenario drives the real UI with fixtures. Required scenarios per tool: `loaded` (input chosen, preview visible), `result` (primary action finished, result card visible, the output file verified by an independent check such as reopening the PDF with PyMuPDF or reading the file), `error` (invalid input shows a `.banner.danger` with a readable sentence and no console error), plus one scenario per extra tab that needs input. The harness takes a screenshot and audit after each scenario. To feed a Browse button, append the fixture path to `api._dialog_answers` before clicking.
5. Fill the tool's rows in `tests/parity/feature_map.json` (every doc bullet of that tool to a `testid` or scenario name).
6. Gate for the tool (all must pass):
   - `.venv\Scripts\python.exe -m pytest -q tests/test_parity_ui.py tests/test_parity_doc.py tests/test_parity_ops.py -k <id>`
   - `.venv\Scripts\python.exe -m pytest -q tests/ui -k <id>` (QUICK viewports, dark and light)
   - lint loop clean.
7. Commit `tool(<id>): ported`.

If a control on `main` cannot exist in a web view (it is a native Qt-only widget), do not drop it silently: implement the equivalent behavior (for example a native overlay becomes an in-app overlay) and note the equivalence in `label_map.json`.

### 11.2 Batches and order

Build shared components when first needed and reuse them afterward.

| Batch | Tools | Shared pieces created here |
|---|---|---|
| A | `encoding`, `text_tools`, `word_counter`, `markdown`, `data`, `hash` | editors (`code-editor` component: monospace textarea with line numbers and error line marker), tables, progress, jobs |
| B | `metadata`, `renamer`, `archive`, `office`, `converter`, `collage`, `palette`, `qr` | multi-file picker with reorder, queue table, color input, image preview with pixel sampling |
| C | `images`, `pdf`, `ocr`, `screenshot`, `artcraft` | page thumbnails, interactive crop box, searchable OCR generator, external launcher card |
| D | `media`, `playlist`, `network_monitor`, `model3d` | `media-player`, `model-viewer` (three.js) |
| E | `resume` | tree editor with checkboxes and reorder |

### 11.3 Tool specifications

Tool ids and prefixes are fixed. "Tabs" are the `.tabs` in the view. "Must" items are in addition to everything found in step 1 of the procedure.

1. `pdf` (nav "PDF Tools", Documents). Streamlined quick utility tool. Tabs: `merge` (multi-file drag and drop list, up/down reorder buttons, filename sorting, fast merge with form fields preserved), `reorder` (page thumbnail grid for a single PDF, drag reorder, rotate clockwise and counterclockwise per page, duplicate, delete page, save new PDF), `split` (split by page ranges or into individual pages), `extract` (extract text to txt/md), `security` (simple encrypt with password and unlock). Heavy annotation canvases, full-document visual authoring, and complex PDF form designers are omitted from FOSSEverything; users requiring full PDF creation/editing are directed to launch ArtCraft PdfCraft via the external launcher.
2. `images` (nav "Image Tools", Visuals). Lightweight utility tool. Tabs: `convert` (quick single and batch image conversion between PNG, JPG, WEBP, BMP, TIFF), `transform` (crop with aspect ratio presets, resize with aspect lock, rotate 90 cw/ccw, flip h/v), `background` (one-click AI background removal using rembg), `compress` (quick file-size reduction presets). Multi-track layers, brush tools, filter presets, and complex compositing are omitted; users needing full Photoshop-grade workflows are directed to ArtCraft PhotoCraft.
3. `media` (nav "Audio & Video", Media). Focused conversion and trim tool. Tabs: `trim` (fast start/end point selection, audio extraction, mute), `convert` (quick container format conversion between MP4, MKV, WEBM, MP3, WAV, AAC, FLAC), `compress` (Discord 8 MB, 720p balanced, 1080p presets). Complex non-linear multi-track video timeline compositing is omitted; users needing full NLE workflows are directed to ArtCraft FilmCraft.
4. `ocr` (nav "OCR Studio", Documents). Standalone dedicated tool. Tabs: `document` (PDF and image input, language select with auto-discovered packs, DPI select, page preview side-by-side with recognized text, copy text, export txt/md), `searchable_pdf` (takes a scanned PDF or folder of page images and synthesizes a searchable PDF containing an invisible selectable text layer aligned to word bounding boxes using PyMuPDF `insert_text` with render_mode=3, directly turning image-only PDFs into highlightable and searchable documents), `batch` (batch process multiple image/PDF scans into searchable PDFs with progress bar).
5. `artcraft` (nav "Creative Suite", Visuals). ArtCraft launcher and installer hub. Displays cards for ArtCraft standalone tools: PhotoCraft (Photoshop alternative), PdfCraft (Acrobat alternative), FilmCraft (Premiere alternative), VectorCraft (Illustrator alternative), CADCraft (CAD/3D modeling). Detects whether their executables exist locally on disk (or in PATH); displays "Installed - Launch" button (spawns executable via `subprocess.Popen`) or "Get App" button linking to release downloads. Provides automated download/unzip helper when binary releases are available.
5. `resume` (nav "Resume Builder", Documents, workbench). Tabs: `personal`, `sections`, `profiles`, `preview`, `history`. Must: everything in "Resume Studio": master data for roles, projects, skills, education, certifications, awards; checkboxes at section, entry, and bullet level; rename and reorder sections and entries (up and down buttons plus drag); named profiles save and switch; layouts single and dual-column with accent color; live preview in a sandboxed `iframe` (`srcdoc`); export PDF, DOCX, Markdown, HTML; copy plain text; ATS check against a pasted job description (`resume_analyze_ats` if present in `ops.py`); snapshots with changelog diff; open and save master JSON; load sample.
6. `word_counter` (nav "Word Counter", Documents). One page: editor card and stats cards (words, characters with and without spaces, sentences, paragraphs, reading time, readability scores), "Readability and structure" card, "Keyword density" table (top words). Open txt, pdf, docx; report export. Live update debounced 150 ms.
7. `playlist` (nav "Playlist Porter", Media). Tabs: `fetch` (URL for Spotify, YouTube, YouTube Music; Spotify login; YouTube login), `paste` (tracklist text formats Artist - Song, numbered, CSV), `output` (mapped tracklist table, per-track search link buttons, M3U8 and CSV export, create a real YouTube playlist). Login state shown with badges. OAuth flows open the system browser through the API and wait in a job.
8. `converter` (nav "Converter", Utilities). Tabs: `single`, `queue`, `compress`. Must: only valid source and target pairs are offered (`converter_supported_targets` API); never overwrites input; output name and folder; image, PDF pages, data formats (JSON, YAML, CSV, TOML, INI; CSV rejects nested data with a clear message), audio and video, archives, Office, fonts (TTF, OTF, WOFF, WOFF2, with the honest rejection message for outline-type conversions), e-books (targets hidden when Calibre is missing), ENEX notes, ICS import, OCR targets (searchable PDF, txt, md). Queue with per-file or global target, per-file status (pending, done, failed), progress bar, final summary. Compressor: Small, Balanced, High quality presets, auto-detect image, audio, video.
9. `metadata` (nav "Metadata", Utilities). Single page with sections: input and inspect table, edit form (EXIF fields, PDF info fields, audio and video tags), GPS card (coordinates and an offline location readout with a "Open in browser map" button that the user clicks deliberately), bulk and timestamp shift, camera presets, per-field remove toggles, before and after diff table, backend safety report, strip to clean copy, recursive folder cleanup with a preview (dry run) table; warning banner that PDF content, annotations, and attachments are not removed.
10. `qr` (nav "QR and Barcodes", Utilities). Tabs: `generate`, `scan`. Generate must: payload type selector (URL, Wi-Fi with WPA, WEP, open, Text, vCard 3.0, MeCard, Email, Phone, SMS, Geo, Calendar event with `.ics` export, WhatsApp link, asset tag); dynamic content form; center logo with automatic error correction compensation; foreground and background colors; error correction L, M, Q, H; module scale; barcodes Code 39, Code 128, EAN-13, EAN-8, UPC-A, ITF with width, height, colors, label; live preview (debounced 250 ms); export PNG, SVG, print-ready label sheets PDF (Avery 5160 and 5163 presets, auto pagination). Scan must: image, PDF, clipboard, and webcam input (webcam: `getUserMedia` plus a frame sent every 250 ms to `qr_decode_frame`); multi-code results list; payload actions: open URL, copy Wi-Fi password, copy text.
11. `renamer` (nav "Renamer", Utilities). Single page with three cards matching the original groups: "Renaming rules", "Cross-folder rename planning", "Live preview (collision-safe)". Must: all items in the doc section "Batch File Renamer", including presets, undo history, timeline mode, saved plans that re-run only for new files, metadata-aware templates. Preview table statuses: ok, duplicate, exists on disk, unchanged.
12. `data` (nav "Data Tools", Data). Tabs: `editor` (format select JSON, YAML, XML, TOML, INI, CSV, SQL, JS, CSS; format with indentation; minify; live validate with line number; convert among JSON, YAML, CSV, TOML, INI; open, save as, copy), `query` (JSONPath evaluator, schema inference Draft-07, schema diff and overrides, schema validate), `tables` (markdown table parse, render, clean, normalize, CSV to Markdown presets), `units` (unit converter and random generator), `calendar` (ICS generate and parse), `writing` (document diff, grammar and style check with LanguageTool when available and heuristic otherwise, citations and bibliography in APA, MLA, Chicago, BibTeX), `cron` (describe and next 5 runs), `preview` (markdown live preview). All listed doc bullets must map to controls.
13. `markdown` (nav "Markdown Studio", Documents). Editor and preview side by side (`.split.even`); below 56rem a segmented Edit and Preview switch. Formatting toolbar: bold, italic, heading, list, numbered list, link, code, quote, table. Open, save, export HTML, export PDF. Preview is a sandboxed iframe.
14. `hash` (nav "Hash and Verify", Utilities). Tabs: `file`, `directory`, `text`, `compare`, `verify`, `manifest_diff`, `sign` (the seven original tabs). Must: algorithms sha256, sha512, sha1, md5, sha224, sha384, blake2b, blake2s; multi-hash; HMAC; recursive directory hash with progress and byte throughput; export `.sha256`, `.md5`, `checksums.txt`; manifest verification table PASS, FAILED, MISSING; manifest diff; Ed25519 keypair, sign, verify, timestamp and signer, trusted keyring; policy presets Quick Check, Standard Release, Signed Release, Compliance Archive.
15. `palette` (nav "Color Palette", Visuals). Tabs: `dominant`, `samples`. Must: image on a canvas with crosshair; live HUD (hex, rgb, x and y, WCAG contrast against white and black); click adds a sample; color count 2 to 32; median cut and k-means; swatches with hex, rgb, percent, nearest CSS name; copy one, copy all hex; export palette strip PNG or JPEG; GPL export; multi-image aggregation with dedupe. The tab label shows the sample count, example `Samples (3)`.
16. `collage` (nav "Collage", Visuals). Two cards: "Images" (multi-file list with reorder, captions, per-cell colors) and "Layout settings" (columns 1 to 6, cell width and height, padding, background, fit cover, contain, stretch, rounded corners, watermark, six presets). Live preview (debounced 300 ms) beside the cards. Export PNG, JPEG, WEBP.
17. `model3d` (nav "3D Models", Utilities, workbench). Tabs: `cut` (plane origin and normal numeric inputs, multiple cutting planes list, split into pieces, export), `inspector` (stats, watertight, repair), `scale`, `measure`, `convert`. Viewer uses `vendor/three/` (three.js 0.147.0 classic build, `OrbitControls.js` and `STLLoader.js` from `examples/js`, plus `LICENSE`). Fetch them with `npm pack three@0.147.0` in a temp folder, unpack, copy only the three files and the license. The API returns mesh data as base64 float32 positions and uint32 indices (`model3d_get_mesh`); the viewer builds the geometry, shows the cut plane gizmo, wireframe toggle, grid, axes, fit button, orbit, pan, zoom, point picking for measure. B-rep formats (STEP, IGES) appear only when `brep_backend` reports available; otherwise show the "optional backend not installed" banner and keep the rest working. Formats STL, OBJ, PLY.
18. `text_tools` (nav "Text Tools", Data). One page: input and output editors side by side, an operations palette grouped as Case (8 modes), Reverse (3 modes), Cleanup (whitespace, blank lines, tabs and spaces with width, line endings), Lines (sort asc and desc, dedupe, number, prefix and suffix, join and split), Convert (code points, binary), Regex replace (flags i, m, s; friendly errors), Diff (two panes with added and removed counts). Copy, swap input and output, clear.
19. `encoding` (nav "Encoding", Data). Method segmented control (Base64, Base64 URL-safe, URL component, URL full, HTML named, HTML numeric, Hex continuous, Hex spaced, Binary), Encode and Decode actions, text mode and file mode (file in, file out), inline errors for bad input.
20. `network_monitor` (nav "Network", Utilities). Tabs: `live` (table: process, pid, local address, remote address, domain, status, new or unknown flag; refresh every 2 s; pause; filter box), `history` (search over the SQLite history through `network_monitor/db.py`), `stats`, `apps` (per-app summary). Polling stops when the view is hidden.
21. `archive` (nav "Archives", Utilities). Tabs: `create`, `extract`, `inspect`, `protect` (encrypted bundles, key rotation, verify member hashes), `backup` (snapshot compare, incremental sets, manifests, six policy presets: Personal Photos, Source Code, Sensitive Documents, Media Backup, Quick Share, Long-term Archive).
22. `office` (nav "Office Docs", Documents). Single page: input picker, extract text and metadata, buttons for DOCX to PDF, DOCX to Markdown, PPTX to Markdown, XLSX to CSV, plus ODT, ODS, ODP handling that `office/ops.py` offers; result card.
23. `screenshot` (nav "Screen Capture", Utilities). Capture full screen (the API minimizes the window, waits the countdown delay, captures, restores), then an in-app overlay on the captured image offers region selection with crosshair, live width and height readout, and Save, Copy, "Send to Image Tools". Delay input 0 to 10 s.
24. `artcraft` (nav "ArtCraft Hub", Utilities). Dedicated launcher and updater interface for external ArtCraft creative apps. Sections: "Installed Tools", "Available Creative Apps", "About ArtCraft". Each app card (PhotoCraft, PdfCraft, FilmCraft, VectorCraft, CADCraft) displays status badge (Installed / Not Installed), executable path, "Launch" action (spawns subprocess immediately), and "Download / Install" guidance.

### 11.4 Cross-tool rules

- A result that writes a file shows a `.result-card` with the path, "Open file", "Show in folder".
- Remembering folders: file pickers start in the last used folder for that tool (`tool_state.<id>`).
- All long actions: disable the trigger button while running, show `.progress` with Cancel when the job supports it.
- Any text area that displays results is selectable and has a Copy button.
- Layout of forms: labels above controls, one column inside `.split` left panels, groups separated by `.card-title` headings, primary action at the bottom of the group on the left.
- Empty states for every preview, list, and table.

## 12. Phase 7 and 8: sweep, review, packaging

### 12.1 Sweep loop (Phase 7)

Repeat until the first command passes:

1. `.venv\Scripts\python.exe -m pytest -q -m ui_full tests/ui` (all viewports, all scales, all themes). Allow it up to 40 minutes.
2. Open `tests/ui/_out/latest.txt` to find the run directory. Read `findings.txt`. It lists counts by check id.
3. Fix the highest-count id first, at the root: change a token, a component rule, or a layout primitive, not a single view. Prefer the global fix. Examples: A9 truncation across many views means a component's min-width or a sidebar label length is wrong; A12 means `.btn-sm` height or an icon button size is below `--control-h-sm`; A16 means a token pair is below contrast.
4. Re-run only the affected viewport and tool first with `-k`, then the full run.
5. Do not add allowlist entries. Do not shrink the viewport matrix. Do not reduce thresholds.

### 12.2 Visual review checklist (do this after the audit is clean; open the contact sheets and at least 40 individual PNGs: every tool at `min`, `hd720`, `fhd`, `hidpi`, `uhd`, in dark and light)

Answer each item as yes or no for every contact sheet in the final report; fix every no.

1. Is there a clear visual hierarchy (title, tabs, primary action) with one obvious primary button per card?
2. Are paddings and gaps consistent (same card padding, same row gaps) across views?
3. Do all card edges, inputs, and buttons align on shared left edges within a panel?
4. Is any text close to touching a border or another element (less than 8 px of breathing room)?
5. Are there any stray lines, doubled borders, or half-visible borders?
6. Are icons the same size and weight, vertically centered with their labels?
7. Do previews and canvases fill the available space without being stretched or leaving large dead areas?
8. At `uhd` and `ultra`, does content stay centered with a readable width, and do workbench stages grow?
9. At `min`, can every control be reached without horizontal page scroll, and does the sidebar rail look intentional?
10. Do empty states look designed (icon, title, hint, action)?
11. Do tables look clean (aligned numbers, sticky header, no ragged columns)?
12. Is the busy state visible (spinner, progress) for every long action?
13. Are all five themes legible, with accent colors used sparingly?
14. Do the hover, focus, and disabled states exist and look distinct?

Record the answers in the commit message body of `phase7: review`. When the viewer tool is not available to you, state that in the final report and rely on the audit plus the pixel checks.

### 12.3 Packaging (Phase 8)

1. `FOSSEverything.spec`: include `app/web` (all of it, including `vendor`), `assets/`, and drop every PyQt6 and pyvista reference. Remove `pyvistaqt` and `PyQt6` from `uv.lock` through `uv lock`. Update `build.bat`, `build.sh`, `build_exe.ps1`, `scripts/build_executable.py`, `.github/workflows/build-exe.yml` to run `pytest -q` (QUICK UI included) before building. Do not edit README or other `.md` files.
2. `tests/test_native_boot.py` (marker `native`, skipped unless `sys.platform == "win32"` and WebView2 is installed): run `.venv\Scripts\python.exe main.py --selftest` with `FOSS_SELFTEST_OUT` pointing into a temp dir and a 90 second timeout; assert exit code 0 and the JSON has `ready: true`, no error findings, `missing_api: []`.
3. Run `.venv\Scripts\python.exe scripts/build_executable.py`, start `dist\FOSSEverything\FOSSEverything.exe --selftest` with `FOSS_SELFTEST_OUT` set, and assert it exits 0 with the same JSON conditions.

### 12.4 Final acceptance (all must be true before reporting done)

- `git branch --show-current` prints `pywebview-redesign`; `git diff main --stat` shows the full change; the tree is clean and committed.
- `.venv\Scripts\python.exe -m pytest -q` passes with zero failures (UI QUICK matrix, parity guards, contract, static, contrast, previous 263 tests).
- `.venv\Scripts\python.exe -m pytest -q -m ui_full` passes (zero audit errors on the full matrix).
- `.venv\Scripts\python.exe -m pytest -q -m native` passes on this machine.
- `tests/parity/allowlist.json` lists only intentionally omitted heavy studio items with reasons; `tests/ui/audit_allow.json` has at most 12 entries each with a reason.
- `tests/parity/feature_map.json` has no null values and every doc bullet maps to a control or scenario.
- The linter prints `None. Lint clean.` for the whole project at `--level strict`.
- No PyQt6, pyvista, or QSettings reference remains: `git grep -n -E "PyQt6|pyvista|QSettings" -- . ":!PLAN.md" ":!uv.lock"` prints nothing.
- `app/web` contains no inline styles, no non-ASCII bytes, no files over 1500 lines (split large tool files into `<id>.js` and `<id>_parts.js` registered in order).
- Final report lists: what changed, which test commands passed, the path of the last `_out` run directory, and the answers to 12.2.

## 13. Reference

Commands (run from the repository root):

| purpose | command |
|---|---|
| all tests | `.venv\Scripts\python.exe -m pytest -q` |
| one tool UI | `.venv\Scripts\python.exe -m pytest -q tests/ui -k pdf` |
| full UI matrix | `.venv\Scripts\python.exe -m pytest -q -m ui_full tests/ui` |
| rebuild parity data | `.venv\Scripts\python.exe scripts/parity_inventory.py` |
| update baselines | `.venv\Scripts\python.exe -m pytest -q tests/ui --update-baselines` |
| lint | `python C:\Users\Josh\projects\josh-ai-tools\scripts\claudemd_linter.py C:\Users\Josh\projects\FOSSEverything --level strict` |
| run the app | `.venv\Scripts\python.exe main.py` |
| self test | `.venv\Scripts\python.exe main.py --selftest` |

The linter flags AI-style phrasing in every scanned file type (md, js, css, html, py). Write plain, direct sentences and comments. Its legend in `lint_report.txt` lists each rule.

When you are unsure whether something belongs to the original app, `git show main:<path>` is the source of truth. When this plan and the original disagree, the original wins for behavior and this plan wins for structure and appearance.
