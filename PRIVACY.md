# Privacy Statement

FOSSEverything is a local-first desktop application. This statement describes exactly what
the app does and does not do with your files and data.

## What FOSSEverything does

- **All processing happens on your own device.** PDF rendering and editing, image editing,
  audio/video transcoding, OCR, metadata inspection, data formatting, QR/barcode decoding,
  hashing, and every other feature run entirely on your CPU/GPU, using files stored locally
  on your machine.
- **No account, no login, no payment wall.** There is nothing to sign up for and nothing
  gating any feature behind a network check.
- **No analytics or tracking of any kind.** No usage analytics, crash reporters that phone
  home, tracking pixels, cookies, fingerprinting, or background telemetry pings.
- **No hidden network calls.** The app does not upload your files, file contents, filenames,
  or metadata anywhere. It never silently sends anything to a server.
- **Local settings only.** Preferences, recent files, favorites, presets, saved rename plans,
  keybindings, and similar state are stored locally via `QSettings` (the OS's standard local
  app-config mechanism) or local JSON files under your user profile. None of it leaves your
  machine.
- **Safe-by-default outputs.** Destructive operations (metadata stripping, watermarking,
  format conversion, etc.) write to a new output file rather than silently overwriting your
  input, and the UI explains what will be changed, flattened, removed, or lost before you
  confirm.

## The only network activity that exists, and how it's disclosed

A small number of optional features use models or engines that must be downloaded once
before they work offline afterward. In every case:

- The download is disclosed in the feature's own UI before it happens (for example, Image
  Studio's background-removal model picker, or Data Studio's LanguageTool grammar backend).
- The download source is the model/tool's own official distribution channel (e.g. the
  `rembg`/ONNX Runtime model cache, or the LanguageTool project's own server jar), not a
  FOSSEverything-operated server -- FOSSEverything does not operate any server at all.
- Once downloaded, the model/engine is cached locally and reused; no further network access
  is needed to use that feature again.
- If you never open a feature that needs an optional download, no such request ever happens.

Some features also invoke separately-installed local programs on your system (Ghostscript
for PDF compression fallback, Calibre for e-book conversion, a local Java runtime for the
LanguageTool grammar backend). These are your own local installations that FOSSEverything
detects and shells out to -- it never installs, downloads, or bundles these programs itself,
and never uses their absence as a reason to send your files elsewhere instead.

## Your files, your control

Nothing about how FOSSEverything works requires trusting a remote service with your data,
because there isn't one. If you have questions about a specific feature's network behavior,
the corresponding `ops.py` module under `app/features/<name>/` is plain, readable Python with
no hidden network calls to find -- see [CONTRIBUTING.md](CONTRIBUTING.md) if you'd like to
verify this yourself or contribute improvements.
