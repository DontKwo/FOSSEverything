# fosseverything: product map # noqa: 19

FOSSEverything is a free, local-first desktop workbench: download it once and keep
using it without an account, payment, tracking, ads, or file uploads. The
source is intended for GitHub so people can inspect, improve, and redistribute
the tools they rely on.

This document is the product map. Every tool has a current functionality
section and a future work section so the app never presents planned work as
if it already exists.

## Shared app shell, Home, and search

### Current functionality

- Home is the default workspace, with visible global search and a smart-TV-like
  grid of app tiles.
- `Ctrl+K` opens a compact command palette using the same local search engine.
- Search ranks tool names, categories, button keywords, and descriptions. It
  understands common intent aliases such as combine/merge, shrink/compress,
  and trim/crop, supports small typos, and accepts category filters such as
  `pdf:` and `images:`.
- Search results open the matching workspace and invoke the selected action.
- Home tiles use bundled local artwork for each workspace, with favorites and
  pins persisted locally in application settings.
- Home keeps a local recent-files and recent-outputs list, plus a favorites-only
  filter so frequent files and tools are easy to revisit.
- Home accepts dropped files and routes them to the correct workspace using the
  same file-routing rules as shell/file-association launches, including PDF,
  image, media, data, office, and playlist files.
- The app now uses a lightweight workspace registry to declare supported file
  types and route inputs, replacing one-off hard-coded case checks in the shell.
- The shell now includes local theme controls, accessibility text scaling, and
  keyboard navigation shortcuts for Home, search focus, and tab cycling.
- Every major action and button exposes a centralized, searchable tooltip
  dictionary so users can discover controls by label, description, and keyword
  from the main Home search.
- The app has reusable core modules for feature discovery, search, output
  format names, workers, and format-agnostic navigation.
- **Custom keyboard shortcuts**: Rebind every global shortcut (Home, Settings,
  Find a tool, fullscreen, text-size controls) from Settings > Keybindings,
  with per-shortcut reset-to-default and persistence across restarts.
- **Keyboard-only Home tile navigation**: Home's app-tile grid is fully
  focusable and keyboard-operable - Tab onto a tile, use the arrow keys to
  move between tiles in any direction, and press Enter/Space to open one,
  without touching the mouse.
- **Keyboard-only annotation editing**: PDF Studio's and Image Studio's shared
  annotation canvas supports Tab/Shift+Tab to cycle selection between
  annotations, arrow keys to nudge the selected annotation (Shift for a
  larger step), and Delete/Backspace to remove it, once annotations exist.
  Drawing a brand-new freehand/shape annotation is still inherently a
  pointer-driven action, since there's no meaningful keyboard equivalent to
  "draw a shape at this location."

## PDF Studio

### Current functionality

- Open and view PDFs with page navigation, fit, zoom, mouse-wheel zoom,
  trackpad pinch zoom, and canvas panning.
- Add editable rectangle, highlight, text, freehand, directional arrow,
  redaction, and crop-guide annotations. Text supports font family, size,
  bold, italic, color, and letter spacing; it also has offline spellchecking
  when available.
- Select, move, resize, delete, undo, and redo annotations. Saving bakes them
  into a new PDF; redactions remove underlying marked content.
- Visual Page Organizer: Reorder pages, rotate individual pages (90Â° CW/CCW),
  duplicate pages, and delete pages in a dedicated visual manager.
- PDF Security & Passwords: Encrypt PDFs with user/open passwords and owner
  passwords with granular permissions (printing). Unlock and remove password
  protection from encrypted PDFs with a valid password.
- Merge multiple PDFs with manual ordering and sorting by filename, paths,
  dates, or size. Merge preserves form fields where pikepdf supports them.
- Split PDFs by page ranges.
- Compress PDFs through local Ghostscript presets or advanced DPI/preset
  controls.
- Export each PDF page to numbered PNG, JPEG, WEBP, or TIFF images at a chosen
  DPI.
- **Text Watermarking**: Stamp a customizable diagonal text watermark on all or
  selected PDF pages - configurable text, opacity, font size, color, and rotation
  angle using PyMuPDF's Shape API with morph-based arbitrary rotation.
- **Image Watermarking & Signatures**: Add image-based watermarks and signature
  stamps to document pages while preserving local-only file handling.
- **Page Numbers & Headers/Footers**: Stamp page numbers or header/footer labels
  on PDF pages using format templates (`Page {n} of {total}`, `{n}`, custom text),
  6 alignment positions (top/bottom x left/center/right), configurable font size,
  margins, and per-page range control.
- **PDF Bookmarks & Attachments**: Create, list, and persist bookmarks and embed
  local files as PDF attachments without any cloud workflows.
- **PDF Form Field Inspection & Fill**: List available PDF AcroForm fields and
  populate their values locally without any cloud upload or external form engine.
- **PDF Text Extraction**: Extract selectable text from PDFs to `.txt` or `.md`
  files with optional page separators and Markdown-formatted output.
- **PDF QA, Repair & Structure Inspection**: Compare PDFs for text/page drift,
  repair damaged files locally, and inspect page-level metadata, image counts,
  rotation, and form activity to diagnose document issues before sharing.
- **OCR scanned PDFs locally into searchable PDFs and copyable text**: Generate
  an invisible text layer for scanned documents and export copyable OCR text to
  plain text or Markdown files without leaving the local pipeline.
- **PDF-to-DOCX export**: Convert a PDF into an editable Word document locally,
  recovering text layout, tables, and headings, available both from PDF Studio
  directly and as a File Converter target.
- **OCR-aware PDF-to-DOCX conversion**: Scanned (non-text) PDFs are detected
  automatically and routed through local OCR text recovery before DOCX export,
  so both digital and scanned PDFs produce a real, readable Word document.

## Image Studio

### Current functionality

- Open common PNG, JPG/JPEG, WEBP, BMP, and TIFF images safely in the shared
  canvas via Open dialog or drag-and-drop.
- Add selectable/editable rectangles, text, freehand drawings, and directional
  arrows; bake them into a new image on save.
- 1-click Auto Enhance for color, contrast, and histogram balancing.
- Adjust photo tone, contrast, brightness, saturation, sharpness, warmth (tint),
  blur, grayscale, and apply photographic filter presets (Vivid, Sepia, Warm Tone,
  Cool Tone, High-Contrast B&W, Vintage Fade, Invert).
- Crop with a drawn crop region, standard aspect ratio presets (1:1, 4:5, 16:9,
  9:16, 4:3, 3:2), and 1-click circular avatar cutout.
- Rotate 90 degrees CW/CCW (`Ctrl+R` / `Ctrl+Shift+R`), custom degree angle rotation /
  straighten, and flip horizontally / vertically.
- Privacy & redaction tools: Gaussian blur or mosaic pixelate for marked regions.
- Framing & borders: Add solid color borders or Polaroid-style bottom margins.
- Resize with optional aspect preservation.
- Copy composite image directly to clipboard (`Ctrl+C`).
- Multi-layer image composition: Place, reposition, resize, rotate, and reorder
  multiple image layers.
- Compress and convert images with quick quality presets or an advanced
  quality control.
- Batch resize, convert, and compress image sets in a background worker.
- Save/export PNG, JPG/JPEG, WEBP, TIFF, BMP, and PDF. Transparency is kept
  for formats that support it; JPG/PDF flatten it.
- Remove an image background locally using rembg/ONNX Runtime. The user can
  select exact model IDs: `u2netp`, `u2net`, `isnet-general-use`,
  `birefnet-general`, or `birefnet-portrait`. The selected model can download
  once, then runs locally and is reused.
- **Interactive Screenshot & Screen Capture**: Capture the full desktop screen or
  interactively snip a custom rectangular area (with overlay crosshair, live
  dimension preview, and configurable countdown delay) and load the result directly
  into the canvas for immediate annotation and editing.
- **Perspective Crop & Deskew**: Correct perspective distortion with a four-point
  warp and export the corrected region as a clean image layer.
- **Batch background removal**: Process multiple images locally with model-aware
  cleanup, output naming templates, collision handling, and reusable presets.
- **Curves & Color Balance**: Apply tonal RGB curves and channel balance adjusts
  for subtle white-balance and color correction workflows without leaving the
  local image pipeline.
- **Annotation Presets**: Build reusable annotation presets for callout badges,
  magnifier insets, and numbered-step markers for faster review and markup.
- **Non-destructive layer masks**: Create grayscale or alpha masks for local image
  compositing without flattening or destroying the source pixels.
- **Image OCR and text export**: Run local OCR on images and export readable
  text to plain-text or Markdown files for downstream processing and review.
- **Broad format support**: Open RAW camera formats (CR2/CR3/NEF/ARW/DNG/RAF/ORF/RW2/PEF/SRW), HEIC/HEIF, AVIF, SVG (rasterized), and PSD (flattened composite) alongside the standard raster formats.
- **GIF support**: Save single-frame GIFs as a standard export format, extract every frame of an animated GIF to individual PNGs, and build a new animated GIF from a chosen sequence of images with a configurable frame duration.
- **ASCII-art export**: Render the current canvas image as ASCII art text at a configurable character width and save it to a `.txt` file, with selectable charset presets (Standard, Detailed, Blocks, Minimal) and a pre-conversion contrast adjustment for legibility.
- **GIF-to-video conversion**: Convert an animated GIF into an MP4 locally via the bundled FFmpeg engine, deriving playback speed from the GIF's own per-frame timing.

## File Converter

### Current functionality

- A dedicated local Converter workspace, accessible from Home and global
  search.
- Choose a source file, a supported target format, an output filename, and an
  output folder. It does not overwrite the input.
- Convert common images to PNG, JPG/JPEG, WEBP, BMP, TIFF, or PDF.
- Convert PDF pages to numbered PNG, JPEG, WEBP, or TIFF images; the chosen
  output filename becomes the page-name prefix.
- Convert JSON, YAML, CSV, TOML, and INI among one another locally. Nested
  data is rejected for CSV output rather than flattened into incorrect columns.
- Shows only source/target pairs backed by installed local code.
- **Batch Conversion Queue**: Add multiple files to a queue, assign a target
  format globally or per-file, choose an output directory, and process the entire
  queue sequentially with per-file status tracking (pending/done/failed), a live
  progress bar, and a completion summary report.
- **FFmpeg-backed audio/video conversion and audio extraction**: Transcode local
  media streams and pull audio tracks out of video files without cloud services.
- **Archive conversion/extraction through local ZIP/TAR/7-Zip/libarchive
  backends**: Convert archive bundles between common formats and extract content
  using verified local backends.
- **Practical office-document import/export via explicitly installed local
  backends**: Extract text and metadata from Office files, export to PDF/TXT/MD,
  and convert spreadsheet data to CSV/JSON using the local conversion stack.
- **All-in-one Compressor**: A single tool that detects whether a chosen file is
  an image, audio, or video and applies the matching local compression backend
  under one Small/Balanced/High Quality preset, without needing to know which
  studio normally handles that format.
- **Extended image format recognition**: The Single File Converter, Batch
  Conversion Queue, and Compressor all recognize and can convert from RAW
  camera formats, HEIC/HEIF, AVIF, SVG, and PSD, not just standard raster
  formats.
- **Font conversion**: Repackage TTF/OTF fonts to compressed WOFF/WOFF2 web
  fonts and back, with an honest rejection when a requested conversion would
  require changing TrueType outlines to CFF outlines (or vice versa) rather
  than silently producing a mislabeled file.
- **E-book conversion**: Convert between EPUB, MOBI, AZW3, and FB2 using a
  locally installed Calibre (`ebook-convert`) when present; the conversion
  targets are hidden entirely if Calibre isn't installed, rather than
  presenting a broken option.
- **Note-app import/export**: Import and export Evernote ENEX files (titles,
  content, tags, timestamps) to/from plain-text or Markdown notes locally,
  the practical interchange path for Apple Notes migrations too, since Apple
  Notes has no first-party programmatic export format of its own.
- **Calendar `.ics` import**: Parse external `.ics` calendar files (not just
  export them) back into structured events locally, including folded-line and
  escaped-text handling.

See [CONVERSION_CAPABILITIES.md](CONVERSION_CAPABILITIES.md) for the honest
format/backend matrix and why some conversion pairs are inherently lossy,
proprietary, DRM-protected, or not meaningful.

## Metadata Tools

### Current functionality

- Dedicated local Metadata workspace, accessible from Home and search.
- Inspect standard metadata in common image files and PDFs before changing or
  sharing them.
- Edit existing image EXIF fields where Pillow supports writing them.
- Edit PDF title, author, subject, keywords, creator, producer, dates, and
  related standard document metadata.
- Save edits to a new output file with a chosen filename.
- Remove standard image EXIF/container metadata by rebuilding image pixels in
  a clean output copy.
- Remove standard PDF Info and XMP metadata in a clean output copy.
- Clearly warns that metadata removal does not remove PDF page content,
  annotations, or attachments.
- **Metadata support for audio, video, office documents, archives, e-books, and
  more image formats through dedicated local parsers**: inspect, edit, strip, and
  compare metadata across local file types without cloud services.
- **Editable GPS map preview, bulk metadata changes, timestamp shifts,
  camera-field presets, and per-field remove toggles**: update metadata in
  batches, preview coordinate locations, and safely adjust local document/photo
  fields before export.
- **Before/after metadata diff and backend safety reporting**: compare metadata
  snapshots and surface a clear list of fields a given local backend cannot
  safely remove.
- **Recursive batch metadata cleanup**: Process entire directory trees recursively
  with preview mode to inspect metadata before cleanup, collision handling, and
  non-destructive output to a separate directory.

## Data Studio

### Current functionality

- Dedicated local Data Studio workspace, accessible from Home and search.
- Format and pretty-print JSON, YAML, XML, TOML, and INI with customizable
  indentation.
- Minify JSON and XML by stripping redundant whitespace.
- Real-time syntax validation with line-number error reporting for JSON, YAML,
  XML, CSV, TOML, and INI.
- Direct format conversion among JSON, YAML, CSV, TOML, and INI with validation.
- File open, save as, and direct clipboard copying.
- **JSONPath Query Evaluator**: Evaluate JSONPath expressions on JSON/YAML data
  directly in the editor. Supports dot-notation, array indexing, wildcards (`*`),
  array slices (`[0:3]`), recursive descent (`$..key`), and filter expressions
  (`[(@.field op val)]` with `==`, `!=`, `<`, `>`, `<=`, `>=`). Results replace
  the editor content for easy inspection and chaining.
- **JSON Schema Inference**: Infer a standard JSON Schema (Draft-07) from any
  JSON or YAML data structure with a single click. Produces `type`, `properties`,
  `required` arrays, and handles nested objects and arrays automatically.
- **Markdown Table Editing**: Parse and render pipe-delimited Markdown tables,
  convert them into structured rows, and round-trip them without losing column
  names or values.
- **Schema Diffing & Overrides**: Compare a live schema against a target schema,
  report added/removed/changed fields, and apply field-level type overrides for
  validation and cleanup workflow follow-up.
- **CSV-to-Markdown conversion presets**: Turn spreadsheet exports into reviewable
  Markdown tables with headers, alignment, and reusable conversion settings.
- **Schema-validation preview**: Validate JSON, YAML, or CSV-backed payloads
  against a user-provided schema before cleanup or import.
- **Notebook-style table tooling**: Clean, normalize, and round-trip Markdown
  tables with empty-column filtering, whitespace trimming, and review-friendly
  formatting for docs and research notes.
- **Unit converter**: Convert focused value pairs across length, weight,
  temperature, time, area, volume, speed, pressure, angle, and data units with
  quick local calculations.
- **Random generator**: Produce strings, passwords, numbers, UUIDs, names, and
  email-like tokens with configurable rules and output formatting.
- **Markdown live preview**: Convert Markdown text to an HTML preview locally for
  notes, research docs, and content drafting.
- **Calendar export**: Generate valid `.ics` calendar payloads for local event
  scheduling and transfer to calendars or scheduling tools.
- **Document diffing**: Compare two text sources side-by-side and summarize
  additions, removals, and changed lines in a local unified-diff view.
- **Local grammar and style checking**: Flag double spaces, repeated words,
  sentence-spacing issues, and stray all-caps text with a readability score,
  entirely offline.
- **Citation and bibliography generation**: Generate single citations or full
  bibliographies in APA, MLA, Chicago, or BibTeX format from author/title/year/
  publisher fields.
- **Stronger local grammar backend**: Full sentence-structure and style
  analysis via a local LanguageTool instance (requires a local Java 17+
  runtime) when available, automatically falling back to the built-in
  heuristic check with no crash or interruption when it isn't.
- **SQL, JavaScript, and CSS formatting**: Beautify SQL (via `sqlparse`),
  JavaScript (via `jsbeautifier`), and CSS (via `cssbeautifier`) alongside the
  existing JSON/YAML/XML formatters, plus a conservative heuristic minifier
  for JavaScript and CSS and comment/whitespace-stripping SQL minification.
- **Cron Expression Generator**: Parse a standard 5-field cron expression into
  a human-readable description and preview its next 5 run times, entirely
  locally with no external scheduling service.

## Text Tools

### Current functionality

- Dedicated local Text Tools workspace, accessible from Home and search.
- **Case conversion**: UPPERCASE, lowercase, Title Case, Sentence case,
  camelCase, snake_case, kebab-case, and CONSTANT_CASE.
- **Reversal**: reverse text by character, by word order, or by line order.
- **Whitespace and line cleanup**: trim trailing/leading whitespace, collapse
  repeated spaces, remove blank lines, convert between tabs and spaces
  (configurable width), and normalize line endings (LF/CRLF/CR).
- **Line operations**: sort lines alphabetically (ascending or descending),
  deduplicate lines, number lines sequentially, add a prefix/suffix to every
  line, and join/split lines with a chosen delimiter.
- **Text/code-point and text/binary conversion**: convert text to and from a
  space-separated list of decimal Unicode code points, and to and from
  space-separated 8-bit binary octets (UTF-8 byte-wise).
- **Regex find & replace**: apply a regular expression across the current
  text with case-insensitive, multiline, and dot-matches-all flags, with
  clear error messages instead of raw tracebacks for invalid patterns.
- **Diff checker**: compare the current text against a second block in a
  two-pane dialog and show a unified diff with added/removed line counts.

## Encoding / Decoding

### Current functionality

- Dedicated local Encoding/Decoding workspace, accessible from Home and search.
- **Base64 encode/decode**: standard and URL-safe alphabets, for pasted text
  and for arbitrary local files (encode a file's bytes to Base64, or decode a
  Base64 payload back to a file).
- **URL/percent-encoding**: component-safe encoding and a full-URL variant
  that preserves reserved characters, plus decoding.
- **HTML entity encode/decode**: standard named entities and a numeric
  character-reference variant.
- **Hexadecimal encode/decode**: text and file bytes, with a toggle between
  continuous and space-separated byte pairs.
- **Binary (byte-level) encode/decode**: arbitrary local files to and from a
  space-separated binary representation, distinct from Text Tools' plain-text
  binary conversion.
- Clear, non-crashing error messages for invalid input (bad Base64 padding or
  characters, malformed hex, non-UTF-8 bytes) instead of raw tracebacks.

## Batch File Renamer

### Current functionality

- Dedicated local Batch Renamer workspace, accessible from Home and search.
- Find and replace in filenames with plain text or full Regular Expressions
  (Regex with `$1` capture group substitution).
- Sequential numbering with customizable start number, step, and zero-padding
  (e.g., `001`, `002`).
- Add custom prefixes and suffixes.
- Change letter casing: lowercase, UPPERCASE, Title Case, or Sentence case,
  with optional extension casing rules.
- Change or normalize file extensions.
- Real-time collision-safe preview table warning of duplicates, existing disk
  collisions, and unchanged files.
- Safe two-pass execution supporting swap/case-only renames on Windows.
- Saved renaming presets for reusable rulesets and undo session history to roll
  back prior rename batches.
- **Metadata-aware rename templates**: Use EXIF dates, camera models, and ID3
  audio tags directly in filename patterns for batch naming and organization.
- **Cross-folder rename planning**: Add files from multiple source folders into one batch, then optionally consolidate every renamed file into a single output folder (moving across drives when needed) without disturbing the original folders.
- **Timeline mode**: Reorder files gathered from any number of folders into one true chronological sequence (EXIF/ID3 capture date, falling back to file modified time) before applying sequential numbering, for merging multiple cameras/sources into one timeline.
- **Saved cross-folder rename plans**: Save a cross-folder batch (source folders + rule/mode) as a named, reusable plan, then re-run it later against only the files added to those folders since the plan was last run.

## Archive & Packaging

### Current functionality

- Create ZIP and TAR/GZ archives directly from files or folders without relying on a cloud service.
- Extract archives to a chosen destination and inspect their member list locally.
- Compare directory snapshots and generate incremental backup sets that only include changed files.
- Use the same archive helpers in file-processing workflows and batch operations.
- **Password-Protected Local Bundles**: Create encrypted archive bundles with a
  password-derived key and decrypt them back locally without any external cloud
  service or online vault.
- **Key rotation and integrity verification**: Rotate bundle passwords without
  rewriting source data and verify archive member hashes for local integrity
  checks.
- **Local bundle manifests**: Produce hash manifests for source trees so backup
  and archive diffing follow a consistent integrity policy.
- **Archive policy presets**: Use predefined backup policies for common use cases (Personal Photos, Source Code, Sensitive Documents, Media Backup, Quick Share, Long-term Archive) with preconfigured compression and encryption settings.

## QR Codes & Barcodes

### Current functionality

- Dedicated local QR Codes & Barcodes workspace, accessible from Home and search (`Ctrl+K`).
- Generate custom QR codes 100% offline with zero cloud calls or data leakage.
- Payload generators: Website URLs, Wi-Fi network configuration (SSID, Password, WPA/WEP/Open), Plain Text, Contact cards (vCard 3.0), Email, Phone numbers, SMS messages, Geo coordinates, and Calendar events.
- Customization: Custom foreground and background colors, Error Correction level selection (L, M, Q, H), and module resolution scaling.
- **Center Logo / Icon Embedding**: Embed a center logo image with white contrast badge and automatic error correction compensation.
- **Vector SVG Export**: Export QR codes as pure-vector SVG files for print, laser cutting, or engraving.
- **Code 39 Barcode Generation**: Generate local Code 39 barcodes for IDs, asset tags, and labels with configurable width, height, colors, and optional value labels.
- **QR Code & Barcode Scanner / Decoder**:
  - Offline decoding of QR codes and standard linear barcodes (EAN-13, Code 128, etc.) from images, PDFs, or clipboard screenshots via OpenCV.
  - Multi-code detection per page/image.
  - Structured payload actions: 1-click open URLs in default browser, 1-click extract & copy Wi-Fi passwords, copy text.
- **Direct Webcam QR / Barcode Scanning**: Use a local camera feed to capture and decode a QR or barcode in a few frames without cloud services.
- **Expanded payload templates**: MeCard business cards, WhatsApp deep links, and structured asset/inventory tracking tags alongside the existing vCard, Wi-Fi, and calendar templates.
- **Additional barcode symbologies**: Code 128, EAN-13, EAN-8, UPC-A, and ITF generation alongside Code 39, with a symbology selector and shared color/label controls.
- **Calendar event export**: Save the Calendar Event payload directly as a standalone `.ics` file, not just as a QR payload.
- **Print-ready label sheets**: Export any generated QR/barcode onto a physically accurate, print-ready multi-label PDF sheet using standard layout presets (e.g. Avery 5160/5163), auto-paginating for large batches.

## Hash & Verify

### Current functionality

- Dedicated local Hash & Verify workspace, accessible from Home and search (`Ctrl+K`).
- Hash any file using SHA-256, SHA-512, SHA-1, MD5, SHA-224, SHA-384, BLAKE2b, and BLAKE2s locally.
- Hash arbitrary text strings with real-time live digest computation, including optional keyed HMAC generation.
- Compare two files directly for identical checksums and verify keyed digests against expected values.
- Multi-hash panel: compute all common algorithms simultaneously in a single pass.
- Verify file integrity: compare computed file hash against an expected hash with clear pass/fail status.
- **Recursive Directory Tree Hashing**:
  - Recursively hash entire folder hierarchies with real-time progress and byte throughput tracking.
  - Generate and export standard GNU/BSD checksum manifest files (`.sha256`, `.md5`, `checksums.txt`).
- **Checksum Manifest Verification**:
  - Open and verify any `.sha256` or `checksums.txt` manifest against local directories.
  - Detailed verification table highlighting `PASS`, `FAILED`, and `MISSING` files.
- **Manifest Diffing**: Compare two checksum manifests to report added, removed, and changed files with old/new hash values.
- **Content Signing**: Generate a local Ed25519 signing keypair, sign any file (including a checksum manifest), and verify a signature against a file and public key.
- **Policy-Based Verification Presets**: Verify a manifest against named policies (Quick Check, Standard Release, Signed Release, Compliance Archive) that combine an algorithm requirement with an optional mandatory signature check.
- **Signature Timestamping & Trusted-Key Management**: Bind a local UTC timestamp and signer name into a signature (a local attestation, distinct from a third-party-notarized timestamp), verify both signature validity and whether the file has changed since signing, and maintain a local named keyring of trusted public keys for multi-party release workflows.

## Palette Extractor & Eyedropper

### Current functionality

- Dedicated local Palette Extractor & Eyedropper workspace, accessible from Home and search (`Ctrl+K`).
- Open any image and extract its dominant color palette using Pillow's median-cut quantizer - fully offline, no network calls.
- **Interactive Eyedropper Tool**: Hover or click directly on any pixel of the loaded image with the crosshair cursor.
- Live pixel coordinate HUD showing Hex `#RRGGBB`, RGB `rgb(r, g, b)`, and position `(X, Y)`.
- Dedicated **Eyedropper Samples** tab: Every clicked color is automatically added to a sampled palette with 1-click clipboard copy.
- Choose the number of dominant colors to extract (2-32).
- Displays color swatches with hex codes (`#RRGGBB`), RGB tuples, percentage share, and nearest named CSS color labels.
- Includes a live WCAG contrast-ratio readout for pixel sampling so text/background balance is visible while picking colors.
- Supports both median-cut extraction and K-means clustering for more perceptually balanced dominant-color selection.
- Copy individual hex/RGB codes or all hex codes at once for use in CSS/design tools.
- Export a visual palette strip image (PNG/JPEG) as a reusable color reference.
- **Multi-image palette aggregation**: Extract and merge dominant colors from multiple images for brand consistency, with automatic deduplication of similar colors.

## Collage Maker

### Current functionality

- Dedicated local Collage Maker workspace, accessible from Home and search.
- Add multiple images and arrange them into a configurable grid layout.
- Choose columns (1-6), cell width/height, padding, background color, and
  fit mode: Cover (crop to fill), Contain (letterbox), or Stretch.
- Optional per-photo text captions rendered below each cell.
- Custom per-cell background colors and rounded-corner masks for cleaner product,
  social, or board-style layouts.
- Export the final collage to PNG, JPEG, or WEBP via a save-as dialog.
- All compositing runs locally with Pillow - no file uploads.
- **Preset layouts**: Side-by-side 2-up, triptych, Instagram grid (3×3), product grid (2×2), story strip (1×4), and wide panel (2×1) framing presets are available for faster composition choices with predefined aspect ratios and spacing.
- **Reordering and watermarking**: Drag/drop image order is preserved for grid
  composition, and exported collages can include a subtle watermark stamp.

## Media Studio

### Current functionality

- Dedicated local Media Studio workspace with an embedded video/audio player and transport controls (Play, Pause, Stop, Seek Slider, Volume).
- 100% offline, local FFmpeg engine via `imageio-ffmpeg` with zero external setup or network requests.
- **Universal Format Support**: MP4, MKV, MOV, AVI, WEBM, MP3, WAV, AAC, FLAC, M4A, OGG, WMA.
- **Interactive Range & Trimming Timeline**: Live start/end playhead markers for marking start/end points with precise sub-second step controls and selection duration tracking.
- **Trim & Cut**: Fast stream-copy mode (instant, lossless keyframe cutting) and frame-accurate re-encoding mode.
- **Audio Extractor**: 1-click audio track extraction from video to MP3, WAV, AAC, FLAC, M4A, or OGG with selectable bitrates (128 kbps to 320 kbps).
- **Convert & Transcode**: Transcode across video containers (MP4, MKV, MOV, WEBM, AVI) and audio formats with custom CRF quality controls.
- **Compress & Resize**: One-click sharing presets (Discord/Email 8MB limit, 720p Balanced Web, 1080p High Quality) and custom scaling.
- **Mute Video**: Strip audio streams locally with zero quality loss.
- **Frame Snapshot**: Capture the active video frame at full native resolution to PNG or JPG.
- **Metadata Tools Integration**: Full audio/video tag inspection (duration, bitrate, resolution, codecs, channels, title, artist, album, genre), tag editing, and privacy metadata stripping.
- **File Converter Integration**: Convert audio and video files in both single-file and batch queue modes.
- **Subtitle Extraction & Burn-In**: Pull embedded subtitle tracks into `.srt` files and burn captions back onto a video output with FFmpeg locally.
- **Audio Waveform Visualization**: Generate a local waveform PNG preview from audio files to quickly assess energy, rhythm, and cut points before editing.
- **Local Speech Transcription**: Attempt on-device transcription from audio/video files using a lightweight local Whisper backend when available, while keeping the feature local-first and gracefully reporting when no Whisper runtime is installed. Transcription now preserves real per-segment timing.
- **Subtitle generation from real transcription timing**: Export the timed segments from a local transcription directly to SRT/VTT, in addition to manually typed timecoded cues; existing burn-in and extraction remain available.
- **Timeline Composer**: Concatenate an ordered sequence of trimmed/cropped clips into one MP4 or GIF export, with per-clip fade in/out, a shared target resolution and frame rate, an optional crossfade transition between clips, and multiple mixed-in audio overlay tracks (each with its own volume, fade, and start offset).

## OCR Studio and Text Extraction

### Current functionality

- Dedicated local OCR Studio workspace, accessible from Home and search (`Ctrl+K`).
- 100% offline, local Tesseract OCR engine bundled via PyMuPDF with zero external binary or cloud requirements.
- Supported input formats: PDF documents (single and multi-page, scanned or digital) and all common image formats (PNG, JPG, WEBP, TIFF, BMP, GIF, etc.).
- Multi-language recognition: English, Spanish, French, German, Italian, Portuguese, Chinese (Simplified/Traditional), Japanese, Korean, Russian, Arabic, Hindi, Dutch, Polish, Turkish, Ukrainian, Vietnamese.
- Configurable scan resolutions: Standard (150 DPI), High Quality (200 DPI), and Ultra (300 DPI) for fine print and receipts.
- Live side-by-side view with visual page navigation/preview and integrated text editor.
- Multi-format text export: 1-click clipboard copy, plain text (`.txt`), and Markdown (`.md`) with page dividers.
- **Searchable PDF Generation**: Embeds an invisible OCR text layer over scanned documents or images, making them fully selectable, searchable, and copy-pasteable while preserving original visuals.
- **Batch OCR Queue**: Process multiple image and PDF files in bulk to Searchable PDFs, Markdown, or Plain Text.
- **Integrated into PDF Studio**: Extract text directly with optional OCR recognition, or convert any scanned PDF to a searchable PDF.
- **Integrated into Image Studio**: Extract text from full images or drawn crop regions with 1-click clipboard copy.
- **Integrated into File Converter**: Convert images or scanned PDFs directly to Searchable PDF, `.txt`, or `.md` via OCR.
- **HOCR & ALTO XML Export**: Save OCR output as hOCR or ALTO XML with per-word bounding boxes so downstream indexing, document processing, or archiving tools can reuse the extracted text precisely.
- **Multi-column layout reconstruction**: Detect multi-column OCR flows and structure extracted text into separate left/right columns for easier reading and downstream export.
- **Language-pack auto-discovery**: Inspect installed local Tesseract data folders and automatically expose supported regional packs without manual configuration.


## Resume Studio

### Current functionality

- Dedicated local Resume Studio workspace, accessible from Home and search (`Ctrl+K`).
- 100% Offline & Private: Master resume data, tailoring configurations, and exported documents remain completely local with zero network calls.
- Master Resume Management: Maintain an all-inclusive master repository of roles, projects, technical skills, education, certifications, and awards.
- Granular 1-Click Tailoring: Checkboxes at the Section, Role/Entry, and Individual Bullet Point levels to toggle inclusion per job application.
- Section Retitling & Reordering: Move sections or entries up/down with single clicks and rename headers inline (e.g. "Work Experience" to "Relevant Experience").
- Job Tailoring Presets / Profiles: Save tailored configurations as named profiles (e.g., "Full-Stack Lead", "Data Engineer", "Frontend Specialist") and switch between them instantly.
- Multi-Theme Exporters:
  - Export ATS-friendly, clean PDF documents generated via local PyMuPDF layout engine.
  - Export to Markdown (`.md`) and responsive HTML.
  - Export as a valid DOCX / Word document with a minimal, local-first template package for downstream editing and ATS-friendly distribution.
  - 1-click copy tailored plain text to clipboard.
- Dual-column resume templates: Export tailored resumes in a two-column layout with configurable accent colors for more magazine-style or ATS-friendly presentations.
- Version history and changelog diffing: Save job-tailoring snapshots, compare prior versions, and summarize which sections, entries, or bullets changed between profile revisions.


## Product and engineering guardrails

- No account, payment wall, ads, analytics, tracking, or hidden file uploads.
- Processing happens on-device by default. Optional model or backend downloads
  are disclosed, reusable, removable, and never silently send a file away.
- Every destructive operation defaults to a new output file and must explain
  what will be changed, flattened, removed, or lost.
- Domain operations stay usable without Qt (`pdf_ops`, `image_ops`,
  `converter_ops`, `metadata_ops`, and future modules) so they can be tested
  and reused headlessly.
- A missing optional backend should disable only the corresponding capability,
  never the whole app.
- Test headless operations and search behavior before expanding into higher
  risk document rewriting.
- A privacy statement ([PRIVACY.md](PRIVACY.md)), an open-source license
  ([LICENSE](LICENSE), AGPL-3.0-or-later), a contributor guide
  ([CONTRIBUTING.md](CONTRIBUTING.md)), reproducible build instructions
  (`uv.lock`-pinned, documented in README's "building standalone executables"
  section), and dependency/model license notices ([NOTICES.md](NOTICES.md))
  are all published ahead of public GitHub release.
