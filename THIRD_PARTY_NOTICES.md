# Third-Party Notices

FOSSEverything is licensed under the [MIT License](LICENSE) (`Copyright (c) 2026 DontKwo`). This document lists external open-source packages, optional command-line backends, pretrained models, icons, fonts, and test datasets used or supported by the application. Upstream components remain subject to their own respective license terms when redistributed or combined with external backends.

## Direct Dependencies

| Package | License | Notes |
| :--- | :--- | :--- |
| pywebview | BSD-3-Clause | Native desktop webview application window container. |
| PyMuPDF | AGPL-3.0-or-later / Commercial | Core PDF manipulation and embedded Tesseract OCR integration. |
| pikepdf | MPL-2.0 | PDF structure manipulation wrapping qpdf (Apache-2.0). |
| Pillow | MIT-CMU | Image loading, processing, and filtering. |
| rembg | MIT | Local background removal wrapper. Model weights carry individual licenses. |
| PyYAML | MIT | YAML parsing and formatting. |
| pyspellchecker | MIT | Offline spell checking. |
| qrcode | BSD | QR code generation. |
| mutagen | GPL-2.0-or-later | Audio tag parsing and editing. |
| tinytag | MIT | Lightweight audio metadata extraction. |
| imageio-ffmpeg | BSD-2-Clause | FFmpeg binary wrapper for audio and video processing. |
| opencv-python-headless | Apache-2.0 | Computer vision operations and barcode decoding. |
| spotipy | MIT | Spotify client integration. |
| trimesh | MIT | 3D mesh operations and slicing. |
| shapely | BSD-3-Clause | Geometric calculations. |
| mapbox-earcut | ISC | Fast polygon triangulation. |
| python-barcode | MIT | 1D barcode generation. |
| cryptography | Apache-2.0 OR BSD-3-Clause | Cryptographic hash and signing operations. |
| pillow-heif | BSD-3-Clause | HEIF and HEIC support wrapping libheif (LGPL-2.1-or-later). |
| rawpy | MIT | Camera RAW processing wrapping LibRaw (LGPL-2.1 or CDDL-1.0). |
| psd-tools | MIT | Adobe Photoshop file decoding. |
| cairosvg | LGPL-3.0-or-later | Vector SVG rasterization. |
| pdf2docx | MIT | PDF to Word document conversion. |
| fonttools | MIT | Font manipulation and WOFF packaging. |
| brotli | MIT | WOFF2 font compression and decompression. |
| language-tool-python | GPL-3.0-only | Local grammar analysis wrapper. |
| sqlparse | BSD-3-Clause | SQL query formatting and tokenization. |
| jsbeautifier | MIT | JavaScript code formatting. |
| cssbeautifier | MIT | CSS stylesheet formatting. |
| google-api-python-client | Apache-2.0 | Google client library. |
| psutil | BSD-3-Clause | System metrics and socket connection inspection. |
| matplotlib | PSF | Color palette visualization and plotting. |
| Feather Icons | MIT | UI iconography used in the web portal. |

## Optional External Tools

The following tools are optional system binaries detected automatically on PATH:

- **Ghostscript**: Optional PDF compression backend (AGPL-3.0 or commercial).
- **Calibre (`ebook-convert`)**: Optional e-book document conversion (GPL-3.0).
- **Tesseract OCR**: Optional engine for optical character recognition (Apache-2.0).
- **Java Runtime Environment (JRE 17+)**: Optional requirement for local grammar checks.

## Pretrained Model Weights & Assets

- Background removal models (`u2net`, `u2netp`, `isnet-general-use`, `birefnet-general`, `birefnet-portrait`) are downloaded only when requested by the user and follow their upstream repository licenses.
- Web portal fonts and demonstration test datasets are subject to their respective open font and public-domain licenses.

## Related Documentation

- [Project Overview](README.md)
- [MIT License](LICENSE)
- [Security Policy](SECURITY.md)
- [Privacy Statement](PRIVACY.md)
- [User Guide](docs/USER_GUIDE.md)
