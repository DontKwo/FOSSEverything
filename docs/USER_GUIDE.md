# FOSSEverything User Guide

Welcome to FOSSEverything, the offline desktop power tool. This guide will walk you through the basics of operating the application, utilizing search filters, and contributing new application modules to the ecosystem.

## Installing

Download the package for your platform from the [latest release](https://github.com/DontKwo/FOSSEverything/releases/latest).

### Windows setup wizard

The installer asks for:
- **Install folder** and **Start Menu folder** (or none).
- **Installation type**: Full, Compact (app only), or Custom components: Explorer right-click menu "Open in FOSSEverything", and Open with entries per file family (PDF, images, audio and video, Office, data, playlists, 3D models, Markdown).
- **Shortcuts**: desktop icon.
- **First-run preferences**: theme and interface size. Existing preferences are kept by default.
- **Per-user or all-users** install (no administrator rights needed for per-user).

Uninstalling removes shortcuts and registry entries and offers to delete your preferences.

Silent install flags:

```text
FOSSEverything-Setup.exe /VERYSILENT /CURRENTUSER /DIR="<install folder>" /TYPE=compact /COMPONENTS="ctx,assoc\pdf" /TASKS=desktopicon /Theme=dark /Scale=1.25
```

Themes: `ut_austin_dark`, `dark`, `light`, `solarized`, `monokai`, `cyberpunk`, `ut_austin`. Scale: `0.9`, `1.0`, `1.1`, `1.25`, `1.5`, `2.0`.

### macOS

Open `FOSSEverything-macos.dmg` and drag the app to Applications. Builds are not notarized yet, so the first launch needs right-click, **Open**. If macOS still blocks it, run `xattr -dr com.apple.quarantine /Applications/FOSSEverything.app`.

### Linux

Extract the tarball and run `./install.sh`. It prompts for install folder, command link, theme, and scale when run in a terminal. Scripted use:

```bash
./install.sh --prefix ~/apps/FOSSEverything --theme dark --ui-scale 1.25 --no-cli-link --yes
./install.sh --uninstall --prefix ~/apps/FOSSEverything --yes
```

Use `./install.sh --help` for every option.

### Windows SmartScreen

Builds are not code signed yet. If SmartScreen warns, choose **More info**, then **Run anyway**. Compare the file against `SHA256SUMS.txt` on the release page.
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
