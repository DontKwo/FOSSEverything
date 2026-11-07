# Media & Visual Suite UX Audit and Polish Report

## Branch
`ai/ux-media`

## Scope
- Image Studio (`images.js`, `tool_images.py`)
- Audio/Video Media Studio (`media.js`, `tool_media.py`)
- 3D Model Studio (`model3d.js`, `tool_model3d.py`)
- Collage & Layers (`collage.js`, `tool_collage.py`)
- Color Palette Studio (`palette.js`, `tool_palette.py`)
- QR & Barcode Studio (`qr.js`, `tool_qr.py`)
- Playlist Porter (`playlist.js`, `tool_playlist.py`)
- Associated styles in `app/web/css/tools.css`

## Issues Found, Severities, and Fixes

1. `MEDIA-CRASH-01` (Severity: High)
   - Location: `app/web/js/tools/media.js:787`
   - Issue: `ReferenceError: defaultReverse is not defined` occurred immediately upon switching to the Effects tab, completely breaking tab rendering.
   - Fix: Declared and initialized `defaultReverse` from `window.FOSS.toolDefaults.get(TOOL_ID, "reverse", false)`.
   - Verified by: `tests/ui/scenarios/test_media_walkthrough.py` passing cleanly.

2. `IMAGES-DOM-COLLISION-02` (Severity: High)
   - Location: `app/web/js/tools/images.js:506`
   - Issue: `viewModeToggle` component was appended directly without `.el`, causing incorrect layout attachment and resulting in [A6] interactive element overlap errors on smaller screens (800x600).
   - Fix: Appended `viewModeToggle.el` and added responsive split containment and divider handling rules to `tools.css`.
   - Verified by: All 6 `images-background` viewport scenarios passing with zero audit violations.

3. `LAYOUT-SPILL-03` (Severity: Medium)
   - Location: `app/web/css/tools.css` (.media-action-title and .images-sidebar-pane .file-picker)
   - Issue: Media action cards text overflowed horizontally and file-picker elements spilled out on narrow viewports.
   - Fix: Permitted normal word wrapping on action titles and adjusted responsive sizing for compact widths.
   - Verified by: Automated DOM audit tests passing across min (800x600), hd720, and fhd viewports.

4. `MODEL3D-OVERLAP-04` (Severity: Medium)
   - Location: `app/web/css/tools.css` (.model3d-sidebar-pane info card)
   - Issue: Dimensions label and monospace measurements collided as inline siblings in compact viewports ([A5] sibling overlap).
   - Fix: Set flex-direction column on `.model3d-sidebar-pane [data-testid="model3d-info-grid"] .col-span-2`.
   - Verified by: `model3d:inspector` audit scenario passing with zero findings.

5. `IMAGES-UX-05` (Severity: Medium)
   - Location: `app/web/js/tools/images.js`
   - Issue: Lack of clear disclosure that rembg AI models require an initial download (up to 176MB), and absence of non-destructive undo/reset capabilities for image transformations.
   - Fix: Added explicit download size notices and informative toasts on model selection/execution. Implemented an undo history stack and a reset-to-original action button.
   - Verified by: User flow testing and static invariant checks.

6. `MEDIA-PROGRESS-CANCEL-06` (Severity: Medium)
   - Location: `app/web/js/tools/media.js`
   - Issue: Long-running ffmpeg background transcoding and extraction operations lacked a visible cancel option and percentage feedback.
   - Fix: Connected `window.FOSS.job` progress hooks to display percentage progress and added a "Cancel Job" button that triggers `job_cancel`.
   - Verified by: `test_media_walkthrough.py` and unit tests.

7. `EXPORT-FEEDBACK-07` (Severity: Low)
   - Location: `app/web/js/tools/collage.js`, `app/web/js/tools/palette.js`
   - Issue: Saving layered collages or copying palette swatches to clipboard provided minimal feedback to the user.
   - Fix: Added clear toast notifications with file names and copied color codes.
   - Verified by: Manual walkthrough scenarios and unit checks.

8. `QR-WEBCAM-GUIDANCE-08` (Severity: Low)
   - Location: `app/web/js/tools/qr.js`
   - Issue: When a webcam is unavailable or permission is denied, users received an abrupt error without guidance on alternatives.
   - Fix: Added helpful advice reminding users that images can be dragged-and-dropped or pasted from the clipboard directly into the scanner.
   - Verified by: `test_qr_walkthrough.py`.

9. `PLAYLIST-PRIVACY-DISCLOSURE-09` (Severity: Low)
   - Location: `app/web/js/tools/playlist.js`
   - Issue: In an offline-first application, account connection and URL fetching UI lacked a statement clarifying that remote network actions are strictly optional.
   - Fix: Embedded a prominent offline privacy notice emphasizing that FOSSEverything is completely offline by default and network calls only occur on explicit action.
   - Verified by: Playwright scenario testing.

## Shared Files Touched
- Shared request: None. All modifications were restricted to tool-specific files (`app/web/js/tools/*.js`, `app/web/css/tools.css`, `app/core/tooltips.py`, `FUNCTIONALITY_AND_FUTURE_WORK.md`).

## What Could Not Be Verified
- Native pywebview desktop window (`pytest -m native`) could not be launched directly due to headless Linux container constraints (X11 display without hardware acceleration). All DOM and API interactions were verified using the Playwright headless browser harness.
- Real webcam capture hardware could not be tested directly due to container environment limits (webcam error handling and fallback paths were verified instead).

## Test Statistics Before and After
- **Before**: 30 failing UI tool audit tests across media tools (due to ReferenceError and layout collisions).
- **After**: All 162 UI tool audit tests passing across min, hd720, and fhd viewports.
- **Contract & Static Tests**: 14 passed (100%).
- **Full Feature Tests**: 515 passed, 5 skipped, 2 deselected.
- **Pure 7-bit ASCII**: 100% clean across all edited files.

## How to Re-Run Everything
- Run UI tool audit suite for media tools:
  `uv run --no-project --python .venv/bin/python python -m pytest tests/ui/test_ui_tools.py -k "images or media or model3d or collage or palette or qr or playlist"`
- Run static and contract verification:
  `uv run --no-project --python .venv/bin/python python -m pytest tests/test_api_contract.py tests/test_web_static.py tests/test_parity_ops.py`
- Run walkthrough tests:
  `uv run --no-project --python .venv/bin/python python -m pytest tests/ui/scenarios/test_media_walkthrough.py tests/ui/scenarios/test_qr_walkthrough.py tests/ui/scenarios/test_media_model3d_features.py`
