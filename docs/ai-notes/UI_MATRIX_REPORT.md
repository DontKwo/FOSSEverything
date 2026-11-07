# Automated GUI Test Matrix Report

## 1. Overview
The automated GUI test matrix exercises all controls, modes, and actions across the 21 tools in FOSSEverything against varying fixture types, random walk sequences, and chaos stress actions.

- **Inventory**: `tests/matrix/ui_inventory.json`
- **Runner**: `tests/matrix/ui/run_ui_matrix.py`
- **Test Suite**: `tests/matrix/ui/test_ui_matrix.py` (marked with `ui_matrix`)

## 2. Coverage Summary
- **Total Tools Enumerated**: 21
- **Total Registered Controls**: 1,885
- **Controls Exercised**: >95% reachable via DOM or mock bridge
- **Unautomatable Controls**:
  - WebCam / Hardware Video Capture (requires active system physical camera device).
  - Spotify / YouTube OAuth interactive sign-in flow (requires external cloud network authorization).

## 3. Tool Coverage Grid

| Tool | Controls in Inventory | Sample Fixture Families | Status |
|---|---|---|---|
| archive | 70 | zip, tar, gz, 7z | PASS |
| collage | 94 | png, jpg, webp | PASS |
| compressor | 56 | pdf, mp4, png, mp3 | PASS |
| converter | 58 | docx, pdf, xlsx, pptx, png | PASS |
| data | 116 | json, yaml, xml, csv, toml | PASS |
| encoding | 65 | txt, json, png | PASS |
| images | 112 | png, jpg, webp, bmp, tiff | PASS |
| markdown | 71 | md, txt | PASS |
| media | 83 | mp4, mov, mkv, mp3, wav | PASS |
| metadata | 66 | jpg, png, mp4, pdf, docx | PASS |
| model3d | 130 | stl, obj, ply, gltf | PASS |
| network_monitor | 84 | txt | PASS |
| ocr | 82 | png, jpg, pdf | PASS |
| palette | 80 | png, jpg, webp | PASS |
| pdf | 104 | pdf | PASS |
| playlist | 62 | m3u8, m3u | PASS |
| qr | 83 | qr, png | PASS |
| renamer | 67 | png, jpg, txt, pdf | PASS |
| resume | 145 | json, txt | PASS |
| text_tools | 154 | txt, md | PASS |
| unit_converter | 103 | txt | PASS |

## 4. Discovered Bugs & Fixes
1. **Text Tools Clipboard Permission Exception**:
   - *Problem*: Clicking "Copy Output", "Copy Report", and "Copy Citation" invoked `navigator.clipboard.writeText(...)` directly without fallback, triggering `Page error: Failed to execute 'writeText' on 'Clipboard': Write permission denied`.
   - *Fix*: Routed through `window.FOSS.api("copy_to_clipboard", { text: ... })`.
   - *Regression Test*: Added `scenario_clipboard_regression` in `tests/ui/scenarios/text_tools.py`.

2. **Unit Converter Clipboard Permission Exception**:
   - *Problem*: Clicking "Copy Number", "Copy Equation", and row copy icons invoked `navigator.clipboard.writeText(...)`, raising permission errors.
   - *Fix*: Routed through `window.FOSS.api("copy_to_clipboard", { text: ... })`.
   - *Regression Test*: Added `scenario_clipboard_regression` in `tests/ui/scenarios/unit_converter.py`.

## 5. Execution Commands
To execute the UI test matrix:
```bash
# Smoke test
uv run --no-project --python .venv/bin/python python -m pytest tests/matrix/ui/test_ui_matrix.py -m ui_matrix -v

# Full / Tool run
uv run --no-project --python .venv/bin/python python tests/matrix/ui/run_ui_matrix.py --tool text_tools --seed 42
```
