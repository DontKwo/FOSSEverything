# FOSSEverything User Guide

Welcome to FOSSEverything, the offline desktop power tool. This guide will walk you through the basics of operating the application, utilizing search filters, and contributing new application modules to the ecosystem.

## Running the Web Portal

Because FOSSEverything is designed as a standalone offline desktop application, the primary way to launch the interface is via the standard Python bootstrapper:

```bash
uv run python main.py
```

This commands spins up a headless Python backend that coordinates local hardware operations while simultaneously launching a native OS window using `pywebview`. There is no cloud backend, no telemetry, and no accounts required.

If you are developing or testing UI changes purely on the frontend, you can bypass the backend and run a static HTTP server on the `app/web/` directory:
```bash
uv run python -m http.server 3000 --directory app/web
```
Navigate to `http://localhost:3000` in any web browser to view the interface structure.

## Using Search Filters

The search portal is the fastest way to navigate FOSSEverything.

1. **Invoke the Search**: Press `Ctrl+K` (or `Cmd+K` on macOS) anywhere in the application to open the global command palette.
2. **Intent-Based Keywords**: You do not need to know the exact name of a tool. The search engine normalizes words and maps intent aliases. For example, typing `shrink`, `reduce`, or `compress` will immediately suggest tools like the "File Compressor" and "Archive & Compression".
3. **Combination Filters**: The search supports basic AND matching. For instance, searching for `convert image` will instantly filter down the toolkit to the exact conversion utilities matching both concepts.

## Submitting New FOSS Applications

FOSSEverything uses an extensible plugin-style registry. Adding a new workspace or application requires modifications in three distinct layers to maintain separation of concerns:

1. **Domain Operations (`app/features/<feature_name>/ops.py`)**:
   Implement pure Python functions capable of processing files completely offline. Ensure you import no GUI code or webview context.
2. **Web API Mixin (`app/web/api/tool_<feature_name>.py`)**:
   Create a mixin class containing endpoints decorated with `@api_method`. Ensure validation on inputs and structured returns via `ok()` or `fail()`. Expose your methods lazily in `app/web/api/__init__.py`.
3. **Frontend Integration (`app/web/js/tools/<feature_name>.js`)**:
   Create the workspace UI using standard HTML/CSS/JS. Avoid using any external frontend frameworks.
4. **Registration (`app/core/tool_registry.py`)**:
   Add a `HomeApp` definition mapped to your tool ID with plain-language keywords and aliases so the search engine can discover your utility offline.

Once implemented, run all standard checks (`uv run pytest`) and submit a pull request!
