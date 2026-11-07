# Third-Party Notices

FOSSEverything is licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later). See [LICENSE](LICENSE). This document outlines the rationale for this license and lists third-party components utilized by the project.

## License Rationale

FOSSEverything integrates several dependencies with copyleft licenses. As a result, the distributed application must be provided under terms compatible with these requirements:

- **PyMuPDF**: Dual-licensed by Artifex under AGPL-3.0-or-later or commercial terms. Using PyMuPDF without a commercial license requires the combined distributed application to be released under AGPL-3.0.
- **mutagen**: Licensed under GPL-2.0-or-later for reading and writing audio metadata tags.
- **language-tool-python**: Licensed under GPL-3.0-only for local offline grammar and style analysis.

AGPL-3.0-or-later satisfies all dependency obligations simultaneously per section 13 of the GNU General Public License v3 and GNU Affero General Public License v3. FOSSEverything executes as an offline desktop utility with no server infrastructure; the network source disclosure clause exists to satisfy PyMuPDF terms cleanly.

## Direct Dependencies

| Package | License | Notes |
|---|---|---|
| pywebview | BSD-3-Clause | Native desktop webview application window container. |
| PyMuPDF | AGPL-3.0-or-later | Core PDF manipulation and embedded Tesseract OCR integration. |
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

## External Tools

The following tools are optional external utilities installed by the user on the operating system PATH. FOSSEverything detects their presence and provides graceful degradation when absent:

- **Ghostscript**: Optional PDF compression backend (AGPL-3.0 or commercial).
- **Calibre (`ebook-convert`)**: Optional e-book document conversion (GPL-3.0).
- **Tesseract OCR**: Optional engine for optical character recognition (Apache-2.0).
- **Java Runtime Environment (JRE 17+)**: Optional requirement for LanguageTool execution (GPL-2.0 with Classpath Exception).

## Pretrained Model Weights

The background removal tool (`rembg`) downloads model weights upon user request (`u2net`, `u2netp`, `isnet-general-use`, `birefnet-general`, `birefnet-portrait`). Each model file carries an independent license governed by its respective research institution. Consult upstream research repositories for specific model distribution terms.
