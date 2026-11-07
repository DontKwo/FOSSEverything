# Privacy Statement

FOSSEverything is a local-first desktop application. This statement describes what the application does with files and data.

## Processing and Data Handling

- **Local Execution**: PDF editing, image processing, media transcoding, OCR, metadata inspection, data formatting, QR decoding, hashing, 3D modeling, and archive operations run on your local hardware. Files remain on your machine.
- **No Accounts**: The application requires no registration, logins, subscriptions, or network authentication checks.
- **Zero Telemetry**: No usage metrics, error reporting services, tracking pixels, cookies, or background telemetry calls are implemented.
- **No Cloud Uploads**: The application never sends files, filenames, content, or metadata to external servers.
- **Local Configuration**: Preferences, recent paths, favorites, custom keybindings, and presets are saved in a local JSON configuration file inside your user profile directory (`app/system/settings.py`).
- **Non-Destructive Defaults**: Modifying operations (watermarking, format conversion, metadata stripping) write output to a new destination path to preserve input originals. The UI outlines all modifications before processing.

## Optional Downloads and System Integrations

A few optional capabilities use pretrained models or external tools:

- Downloads occur only when explicitly requested in the corresponding tool interface (such as selecting a background-removal neural model or initializing an optional grammar server).
- Files download directly from official upstream project distribution repositories. FOSSEverything does not maintain an intermediary server.
- Downloaded models are cached locally for offline reuse. Subsequent tasks run without network access.
- Tools that use optional system software (such as Ghostscript, Calibre, or a Java runtime) detect existing local installations on your system PATH. They never install external software automatically or redirect processing to external web services.

## Auditing and Inspection

All processing logic is inspectable in the `app/features/<feature>/ops.py` modules. See [CONTRIBUTING.md](CONTRIBUTING.md) for testing guidelines and development setup.
