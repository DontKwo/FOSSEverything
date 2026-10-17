# Third-Party Notices

FOSSEverything's own source code is licensed under the GNU Affero General Public License
v3.0 or later (AGPL-3.0-or-later) -- see [LICENSE](LICENSE). This document explains why that
license was chosen and lists the license of every direct dependency and externally-invoked
tool the app relies on.

## Why AGPL-3.0-or-later, not a permissive license

FOSSEverything bundles several dependencies that are themselves copyleft-licensed, which
means the *combined, distributed application* cannot legally be offered under a plain
permissive license (like MIT) regardless of what license FOSSEverything's own code would
otherwise use. The two that matter most:

- **PyQt6** (the Qt bindings used for the entire UI) is licensed **GPL-3.0-only** by
  Riverbank Computing, its author -- separately from Qt itself, which Qt Group dual-licenses
  under LGPL-3.0/commercial. Using PyQt6 without purchasing Riverbank's commercial PyQt
  license means the application built with it must be distributed as free software under a
  GPL-3.0-compatible license.
- **PyMuPDF** (used throughout PDF Studio, OCR Studio, and other PDF handling) is dual-licensed
  by Artifex under **AGPL-3.0-or-later, or a commercial Artifex license**. Without the
  commercial license, distributing PyMuPDF requires the combined work to be AGPL-3.0.

AGPL-3.0-or-later is the smallest license that is simultaneously compatible with both of these
requirements (GPLv3 code and AGPLv3 code may be combined and conveyed together per GPLv3
section 13 / AGPLv3 section 13), so it was chosen as FOSSEverything's project license rather
than GPL-3.0 alone or a permissive license paired with a disclosed conflict. FOSSEverything is
a desktop application with no server component, so AGPL-3.0's extra network-source-disclosure
clause (beyond plain GPLv3) has no practical effect for typical use -- it exists here purely to
satisfy PyMuPDF's licensing terms cleanly.

**If you fork this project for closed-source or SaaS use**, you would need to either comply
with AGPL-3.0 (including source availability, even over a network) for the whole combined
work, or independently obtain commercial licenses from Riverbank Computing (for PyQt6) and
Artifex (for PyMuPDF) and relicense your fork accordingly. This is not legal advice --
consult a lawyer for your specific situation.

## Direct dependency licenses

Licenses below were read from each package's own installed metadata (PyPI `License-Expression`
or `License` field), not guessed. Verify against the installed package's own `LICENSE`/`COPYING`
file before relying on this list for a legal decision.

| Package | License | Notes |
|---|---|---|
| PyQt6 | GPL-3.0-only | See rationale above. Riverbank also sells a commercial license. |
| PyQt6-Qt6 (bundled Qt6 libraries) | LGPL-3.0 | Qt Group also offers a commercial Qt license. |
| PyMuPDF | AGPL-3.0-or-later OR Artifex commercial license | See rationale above. |
| pikepdf | MPL-2.0 | Wraps qpdf (Apache-2.0). |
| Pillow | MIT-CMU | Permissive. |
| rembg | MIT | Model *weights* it downloads carry their own separate licenses -- see "Model weight licenses" below. |
| PyYAML | MIT | Permissive. |
| pyspellchecker | MIT | Permissive. |
| qrcode | BSD | Permissive. |
| mutagen | GPL-2.0-or-later | Copyleft; used for reading/writing audio tags. |
| tinytag | MIT | Permissive. |
| imageio-ffmpeg | BSD-2-Clause (wrapper) | Downloads a prebuilt FFmpeg binary; that binary's own license depends on which codecs it was built with -- see FFmpeg note below. |
| opencv-python-headless | Apache-2.0 | Permissive. |
| spotipy | MIT | Permissive. |
| trimesh | MIT | Permissive. |
| shapely | BSD-3-Clause | Permissive. |
| mapbox-earcut | ISC | Permissive. |
| pyvista | MIT | Permissive. |
| pyvistaqt | MIT | Permissive. |
| python-barcode | MIT | Permissive. |
| cryptography | Apache-2.0 OR BSD-3-Clause | Permissive (dual). |
| pillow-heif | BSD-3-Clause (wrapper) | Bundles libheif, which is LGPL-2.1-or-later. |
| rawpy | MIT (wrapper) | Bundles LibRaw, which is dual LGPL-2.1/CDDL-1.0 (or the non-GPL LibRaw Software License for the closed variant -- rawpy's wheels use the open LGPL/CDDL build). |
| psd-tools | MIT | Permissive. |
| cairosvg | LGPL-3.0-or-later | Copyleft (weak/file-level in practice for an unmodified dependency). |
| pdf2docx | MIT | Internally imports PyMuPDF (see above); PyMuPDF's own license terms still apply to that part. |
| fonttools | MIT | Permissive. |
| brotli | MIT | Permissive. |
| language-tool-python | GPL-3.0-only | Copyleft. Wraps a downloaded local LanguageTool server, itself LGPL-2.1-or-later; requires a local Java 17+ runtime the user installs separately. |
| onnxruntime (via rembg) | MIT | Permissive. |
| cadquery-ocp (optional `cad` extra) | Apache-2.0 | Bundles OCCT (OpenCascade), which is LGPL-2.1-with-exception. Only installed if the optional `cad` extra is requested. |
| PyInstaller (dev/build tool only) | GPL-2.0-or-later, with an explicit bootloader exception | The exception means applications *built with* PyInstaller are not required to be GPL-licensed themselves; only PyInstaller's own source is GPL. Not shipped inside the built app. |
| sqlparse | BSD-3-Clause | Permissive. Used for SQL formatting in Data Studio. |
| jsbeautifier | MIT | Permissive. Used for JavaScript formatting in Data Studio. |
| cssbeautifier | MIT | Permissive. Used for CSS formatting in Data Studio. |

## Home screen tile artwork

The Text Tools and Encoding/Decoding tile icons (`assets/home/text_tools.png`, `assets/home/encoding.png`)
are rasterized from CC0-licensed (public domain) SVG icons sourced from SVG Repo
(svgrepo.com/svg/494122/text and svgrepo.com/svg/221308/binary-code-binary). CC0 requires no
attribution, but the source is noted here for traceability.

## Externally-invoked local tools (not bundled, not downloaded by FOSSEverything)

These are separate programs the user installs themselves; FOSSEverything only detects and
shells out to them if present, and every feature that depends on one degrades gracefully
(the capability is simply hidden or disabled) when it's absent:

- **Ghostscript** (optional PDF compression backend) -- AGPL-3.0 or Artifex commercial license.
- **Calibre** (`ebook-convert`, optional e-book conversion backend) -- GPL-3.0.
- **Tesseract OCR** (used via PyMuPDF's OCR integration) -- Apache-2.0.
- **A local Java runtime** (required only for the optional LanguageTool grammar backend) --
  license depends on which JDK/JRE distribution the user installs (e.g. Eclipse Temurin is
  GPL-2.0-with-classpath-exception).

## Model weight licenses

`rembg`'s background-removal feature can download one of several pretrained model files
(`u2net`, `u2netp`, `isnet-general-use`, `birefnet-general`, `birefnet-portrait`) on first use
of that specific model. Each model file has its own license from its original authors/research
group, independent of `rembg`'s own MIT license or FOSSEverything's license. Consult the
model's upstream source (linked from the `rembg` project) before redistributing a model file
itself or using it in a context with different licensing requirements than your own use of
FOSSEverything.
