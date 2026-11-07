# Shared Component Requests (from ai/matrix-ui)

## 1. Native Clipboard Bridge Integration
- **Issue**: Standard DOM calls to `navigator.clipboard.writeText(...)` fail in headless browser automation and restricted pywebview sandbox contexts with:
  `Write permission denied`
- **Request**: Components that trigger clipboard operations should use `window.FOSS.api("copy_to_clipboard", { text: ... })` or wrap `navigator.clipboard.writeText` in a defensive fallback to `window.FOSS.api("copy_to_clipboard")`.
- **Status in Tools**: Addressed locally in `text_tools.js` and `unit_converter.js`.

## 2. File Dialog Mock Queue State
- **Note**: Ensure `api._dialog_answers` in test environments is drained gracefully when file pickers cancel or multiple files are chosen in sequence.
