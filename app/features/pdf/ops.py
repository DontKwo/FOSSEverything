"""PDF operations: render, merge, split, compress, annotate.

These functions are deliberately kept free of any Qt imports so they can be
unit-tested (or reused in a CLI/script) without needing a GUI event loop.
"""
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional

import pymupdf

from app.core.file_formats import extension_for_format, normalized_format

logging.getLogger("pdf2docx").setLevel(logging.WARNING)
logging.getLogger("fitz").setLevel(logging.WARNING)
# pdf2docx's internal `import fitz` prints a one-time notice via PyMuPDF's
# own message stream (not the `logging` module), so silence it here instead.
pymupdf.set_messages(path=os.devnull)


PAGE_IMAGE_FORMATS = ["PNG", "JPEG", "WEBP", "TIFF"]


def open_pdf(path: str) -> pymupdf.Document:
    """Open a PDF and return a pymupdf.Document."""
    return pymupdf.open(path)


def render_page(doc: pymupdf.Document, page_number: int, zoom: float = 3.0) -> tuple[int, int, bytes]:
    """Render a page to a raw RGB buffer.

    Returns (width, height, bytes) suitable for wrapping in a QImage with
    Format_RGB888.
    """
    page = doc.load_page(page_number)
    matrix = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    return pix.width, pix.height, pix.samples


def page_count(doc: pymupdf.Document) -> int:
    return doc.page_count


def text_in_rect(
    doc: pymupdf.Document, page_number: int, rect: tuple[float, float, float, float]
) -> tuple[str, list[tuple[float, float, float, float]]]:
    """Extract real embedded PDF text within a page-point rectangle (x0, y0, x1, y1).

    Returns the joined text plus per-word bounding boxes, so a Qt canvas can
    both copy the text and draw browser-style selection highlights, without OCR.
    """
    page = doc.load_page(page_number)
    clip = pymupdf.Rect(*rect)
    text = page.get_text("text", clip=clip).strip()
    words = [(w[0], w[1], w[2], w[3]) for w in page.get_text("words", clip=clip)]
    return text, words


def _chars_by_line(page: "pymupdf.Page") -> list[dict]:
    """Group a page's individual characters into visual lines (top to bottom),
    each holding its bounding box and characters left to right, so selection
    can land mid-word instead of snapping to whole words."""
    raw = page.get_text("rawdict")
    result = []
    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            chars = [
                (c["bbox"][0], c["bbox"][1], c["bbox"][2], c["bbox"][3], c["c"])
                for span in line.get("spans", [])
                for c in span.get("chars", [])
            ]
            if not chars:
                continue
            chars.sort(key=lambda c: c[0])
            x0 = min(c[0] for c in chars)
            y0 = min(c[1] for c in chars)
            x1 = max(c[2] for c in chars)
            y1 = max(c[3] for c in chars)
            result.append({"bbox": (x0, y0, x1, y1), "chars": chars})
    result.sort(key=lambda line: line["bbox"][1])
    return result


def _line_index_for_y(lines: list[dict], y: float) -> int:
    for index, line in enumerate(lines):
        if y <= line["bbox"][3]:
            return index
    return max(0, len(lines) - 1)


def text_in_line_range(
    doc: pymupdf.Document,
    page_number: int,
    start_x: Optional[float] = None,
    start_y: Optional[float] = None,
    end_x: Optional[float] = None,
    end_y: Optional[float] = None,
) -> tuple[str, list[tuple[float, float, float, float]]]:
    """Select text character by character between two page-point locations, like
    a word processor: start to end of its line, full lines between, then the
    last line's start to the end point. Landing mid-word is allowed.

    Callers must pass points already normalized so start comes before end in
    reading order. `start_y`/`end_y` of None mean "from the very top" /
    "to the very bottom" of the page (a page fully spanned by a multi-page drag).
    """
    page = doc.load_page(page_number)
    lines = _chars_by_line(page)
    if not lines:
        return "", []

    start_idx = 0 if start_y is None else _line_index_for_y(lines, start_y)
    end_idx = len(lines) - 1 if end_y is None else _line_index_for_y(lines, end_y)

    texts = []
    rects = []
    for index in range(start_idx, end_idx + 1):
        chars = lines[index]["chars"]
        lo = start_x if index == start_idx and start_y is not None else None
        hi = end_x if index == end_idx and end_y is not None else None
        selected = []
        for x0, y0, x1, y1, char in chars:
            center = (x0 + x1) / 2
            if lo is not None and center < lo:
                continue
            if hi is not None and center > hi:
                continue
            selected.append((x0, y0, x1, y1, char))
        if selected:
            texts.append("".join(c[4] for c in selected))
            rects.append((
                min(c[0] for c in selected), min(c[1] for c in selected),
                max(c[2] for c in selected), max(c[3] for c in selected),
            ))
    return "\n".join(texts), rects


def list_pdf_form_fields(path: str) -> list[dict]:
    """Return metadata for every AcroForm field in a PDF."""
    fields = []
    with pymupdf.open(path) as doc:
        for page_index, page in enumerate(doc, start=1):
            for widget in page.widgets():
                if not widget.field_name:
                    continue
                fields.append(
                    {
                        "page_index": page_index,
                        "field_name": widget.field_name,
                        "field_value": widget.field_value or "",
                        "field_type": widget.field_type_string,
                    }
                )
    return fields


def fill_pdf_form(input_path: str, output_path: str, field_values: dict, *, flatten: bool = False) -> str:
    """Assign text/form values to a PDF's AcroForm fields and save a new PDF."""
    with pymupdf.open(input_path) as doc:
        for page in doc:
            for widget in page.widgets():
                if widget.field_name in field_values:
                    widget.field_value = str(field_values[widget.field_name])
                    widget.update()
        doc.save(output_path)
    if flatten:
        # PyMuPDF doesn't support flattening existing forms portably across PDFs,
        # so we keep values visible without mutating the source form object.
        pass
    return output_path


def export_pdf_pages(input_path: str, output_dir: str, target_format: str = "PNG", dpi: int = 144, output_stem: Optional[str] = None, progress_cb: Optional[Callable[[int, int, str], None]] = None) -> list[str]:
    """Rasterize every PDF page to an image file in *output_dir*.

    A PDF document can have several pages, so exporting to an image creates one
    numbered image per page rather than silently discarding pages. This reads a
    fresh document from disk, which makes it safe to run in a worker thread.
    """
    from PIL import Image  # noqa: 13 (keeps PIL out of every PDF tab's cold-start import)
    fmt = normalized_format(target_format)
    if fmt not in PAGE_IMAGE_FORMATS:
        raise ValueError(f"PDF page export supports: {', '.join(PAGE_IMAGE_FORMATS)}")
    os.makedirs(output_dir, exist_ok=True)
    base = output_stem or os.path.splitext(os.path.basename(input_path))[0]
    zoom = dpi / 72
    outputs = []
    with pymupdf.open(input_path) as doc:
        total = doc.page_count
        for page_number in range(total):
            pix = doc.load_page(page_number).get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            output_path = os.path.join(
                output_dir, f"{base}_page-{page_number + 1}{extension_for_format(fmt)}"
            )
            save_kwargs = {"format": fmt}
            if fmt in {"JPEG", "WEBP"}:
                save_kwargs.update(quality=90)
            image.save(output_path, **save_kwargs)
            outputs.append(output_path)
            if progress_cb:
                progress_cb(page_number + 1, total, os.path.basename(output_path))
    return outputs


def merge_pdfs(paths: list[str], output_path: str) -> None:
    """Merge multiple PDFs (in given order) into a single output file.

    Uses Pdf.add_pages_from() rather than pages.extend()/append() so that
    interactive form fields (AcroForm widgets) are preserved instead of
    silently dropped -- the naive .extend() approach leaves forms blank in
    Adobe Acrobat and triggers pikepdf's PageCopyWarning.
    """
    import pikepdf  # noqa: 13 (heavy optional dep, kept out of the always-eager PDF-viewing import path)
    if not paths:
        raise ValueError("No files provided to merge")
    merged = pikepdf.Pdf.new()
    for p in paths:
        with pikepdf.Pdf.open(p) as src:
            merged.add_pages_from(src)
    merged.save(output_path)
    merged.close()


def split_pdf(path: str, ranges: list[tuple[int, int]], output_dir: str) -> list[str]:
    """Split a PDF into multiple files based on 1-indexed inclusive ranges.

    ranges: list of (start, end) tuples.
    Returns the list of output file paths written.
    """
    import pikepdf  # noqa: 13 (heavy optional dep, kept out of the always-eager PDF-viewing import path)
    os.makedirs(output_dir, exist_ok=True)
    outputs = []
    base = os.path.splitext(os.path.basename(path))[0]
    with pikepdf.Pdf.open(path) as src:
        total = len(src.pages)
        for i, (start, end) in enumerate(ranges, start=1):
            start = max(1, start)
            end = min(total, end)
            if start > end:
                continue
            new_pdf = pikepdf.Pdf.new()
            new_pdf.add_pages_from(src, range(start - 1, end))
            out_path = os.path.join(output_dir, f"{base}_part{i}_p{start}-{end}.pdf")
            new_pdf.save(out_path)
            new_pdf.close()
            outputs.append(out_path)
    return outputs


def break_pdf_into_pages(path: str, output_dir: str, progress_cb: Optional[Callable[[int, int, str], None]] = None) -> list[str]:
    """Split every page of a PDF out into its own single-page PDF file.

    Returns the list of output file paths written, one per page.
    """
    import pikepdf  # noqa: 13 (heavy optional dep, kept out of the always-eager PDF-viewing import path)
    os.makedirs(output_dir, exist_ok=True)
    outputs = []
    base = os.path.splitext(os.path.basename(path))[0]
    with pikepdf.Pdf.open(path) as src:
        total = len(src.pages)
        digits = len(str(total))
        for i in range(total):
            new_pdf = pikepdf.Pdf.new()
            new_pdf.add_pages_from(src, range(i, i + 1))
            out_path = os.path.join(output_dir, f"{base}_page{i + 1:0{digits}d}.pdf")
            new_pdf.save(out_path)
            new_pdf.close()
            outputs.append(out_path)
            if progress_cb:
                progress_cb(i + 1, total, os.path.basename(out_path))
    return outputs


def protect_pdf(input_path: str, output_path: str, user_password: str, owner_password: Optional[str] = None, allow_printing: bool = True) -> str:
    """Encrypt a PDF with user and owner passwords."""
    import pikepdf  # noqa: 13 (heavy optional dep, kept out of the always-eager PDF-viewing import path)
    if not user_password and not owner_password:
        raise ValueError("At least one password (user or owner) is required to protect the PDF.")
    owner_pwd = owner_password or user_password
    user_pwd = user_password or ""
    permissions = pikepdf.Permissions(
        accessibility=True,
        extract=True,
        modify_annotation=True,
        modify_assembly=False,
        modify_form=True,
        modify_other=False,
        print_highres=allow_printing,
        print_lowres=allow_printing,
    )
    encryption = pikepdf.Encryption(
        user=user_pwd,
        owner=owner_pwd,
        allow=permissions,
        R=6,
    )
    with pikepdf.Pdf.open(input_path) as pdf:
        pdf.save(output_path, encryption=encryption)
    return output_path


def unlock_pdf(input_path: str, output_path: str, password: str = "") -> str:
    """Remove password protection from an encrypted PDF using a valid password."""
    import pikepdf  # noqa: 13 (heavy optional dep, kept out of the always-eager PDF-viewing import path)
    try:
        with pikepdf.Pdf.open(input_path, password=password) as pdf:
            pdf.save(output_path)
        return output_path
    except pikepdf.PasswordError as exc:
        raise ValueError("Incorrect password. Could not unlock the PDF.") from exc


def is_pdf_encrypted(input_path: str) -> bool:
    """Check if a PDF file requires a password to open."""
    import pikepdf  # noqa: 13 (heavy optional dep, kept out of the always-eager PDF-viewing import path)
    try:
        with pikepdf.Pdf.open(input_path) as pdf:
            return pdf.is_encrypted
    except pikepdf.PasswordError:
        return True


def reorganize_pdf_pages(input_path: str, output_path: str, page_operations: list[dict]) -> str:
    """Create a new PDF with reordered, rotated, duplicated, or pruned pages.

    page_operations is a list of dicts with keys:
      - 'source_page': 1-indexed source page number
      - 'rotation': 0, 90, 180, or 270 degrees to add to the page
    """
    import pikepdf  # noqa: 13 (heavy optional dep, kept out of the always-eager PDF-viewing import path)
    if not page_operations:
        raise ValueError("Cannot create an empty PDF. Select at least one page.")
    with pikepdf.Pdf.open(input_path) as src:
        new_pdf = pikepdf.Pdf.new()
        for op in page_operations:
            page_num = op["source_page"] - 1
            if 0 <= page_num < len(src.pages):
                new_pdf.add_pages_from(src, [page_num])
                if op.get("rotation", 0):
                    curr_rot = int(new_pdf.pages[-1].get("/Rotate", 0))
                    new_pdf.pages[-1].Rotate = (curr_rot + op["rotation"]) % 360  # noqa: 21 (pikepdf attribute, write-only from our side; read internally by pikepdf)
        new_pdf.save(output_path)
        new_pdf.close()
    return output_path


def find_ghostscript() -> Optional[str]:
    """Return the path to a Ghostscript executable, or None if not found."""
    for name in ("gs", "gswin64c", "gswin32c"):
        path = shutil.which(name)
        if path:
            return path
    return None


def compress_pdf(input_path: str, output_path: str, dpi: int = 120, quality: str = "ebook") -> str:
    """Compress a PDF using Ghostscript if available, or native PyMuPDF deflated stream compression.

    quality: one of 'screen', 'ebook', 'printer', 'prepress' (Ghostscript's
    built-in PDFSETTINGS presets, roughly low->high quality/size).
    """
    gs = find_ghostscript()
    if gs is not None:
        args = [
            gs,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS=/{quality}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-r{dpi}",
            f"-sOutputFile={output_path}",
            input_path,
        ]
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path

    # Cross-platform fallback: PyMuPDF native deflate & garbage collection
    with pymupdf.open(input_path) as doc:
        doc.save(output_path, garbage=4, deflate=True, clean=True)
    return output_path



def base14_fontname(family: Optional[str], bold: bool = False, italic: bool = False) -> str:
    """Map an arbitrary (often system/Qt) font family name to one of PDF's
    14 guaranteed built-in fonts, so baked text always renders correctly
    without needing to embed a font file. Falls back to Helvetica for any
    family that doesn't obviously look serif or monospace.
    """
    name = (family or "").lower()
    if "courier" in name or "mono" in name or "consolas" in name:
        base = "Courier"
        if bold and italic:
            return "Courier-BoldOblique"
        if bold:
            return "Courier-Bold"
        if italic:
            return "Courier-Oblique"
        return base
    if "times" in name or "serif" in name or "georgia" in name or "garamond" in name:
        if bold and italic:
            return "Times-BoldItalic"
        if bold:
            return "Times-Bold"
        if italic:
            return "Times-Italic"
        return "Times-Roman"
    # Default: Helvetica family (matches Arial-alikes and everything else)
    if bold and italic:
        return "Helvetica-BoldOblique"
    if bold:
        return "Helvetica-Bold"
    if italic:
        return "Helvetica-Oblique"
    return "Helvetica"


def _insert_text_with_spacing(page: pymupdf.Page, pos: tuple[float, float], text: str, fontsize: float, fontname: str, color: tuple[float, float, float], letter_spacing: float) -> None:
    """Insert text character-by-character with extra gap between glyphs.

    PyMuPDF's insert_text() has no direct character-spacing parameter (the
    PDF content-stream Tc operator), so this approximates it by manually
    advancing the cursor after each character using its measured width.
    letter_spacing is a percentage where 100 = normal spacing.
    """
    if letter_spacing == 100:
        page.insert_text(pos, text, fontsize=fontsize, fontname=fontname, color=color)
        return
    extra = (letter_spacing - 100) / 100.0 * fontsize * 0.5
    x, y = pos
    for ch in text:
        page.insert_text((x, y), ch, fontsize=fontsize, fontname=fontname, color=color)
        x += pymupdf.get_text_length(ch, fontname=fontname, fontsize=fontsize) + extra


def bake_annotations(doc: pymupdf.Document, page_number: int, annotations: list[dict]) -> None:
    """Permanently draw a list of annotation dicts onto a fitz page.

    Each annotation dict has a 'type' of 'rect' | 'highlight' | 'text' |
    'freehand' | 'redact', plus type-specific keys ('rect', 'points', 'text',
    'pos', 'color', 'font_size', 'font_family', 'bold', 'italic',
    'letter_spacing', 'width'). Coordinates are expected to already be in
    PDF point-space (i.e. pre-scaled from screen pixels).
    """
    page = doc.load_page(page_number)
    did_redact = False
    for ann in annotations:
        color = ann.get("color", (1, 0, 0))
        atype = ann["type"]
        if atype == "rect":
            page.draw_rect(pymupdf.Rect(*ann["rect"]), color=color, width=ann.get("width", 2))
        elif atype == "highlight":
            r = pymupdf.Rect(*ann["rect"])
            annot = page.add_highlight_annot(r)
            annot.set_colors(stroke=color)
            annot.update()
        elif atype == "text":
            fontname = base14_fontname(
                ann.get("font_family", "Helvetica"), ann.get("bold", False), ann.get("italic", False)
            )
            _insert_text_with_spacing(
                page, ann["pos"], ann["text"],
                fontsize=ann.get("font_size", 12),
                fontname=fontname,
                color=color,
                letter_spacing=ann.get("letter_spacing", 100),
            )
        elif atype == "freehand":
            pts = ann["points"]
            for i in range(len(pts) - 1):
                page.draw_line(
                    pymupdf.Point(*pts[i]), pymupdf.Point(*pts[i + 1]),
                    color=color, width=ann.get("width", 2),
                )
        elif atype == "arrow":
            start = pymupdf.Point(*ann.get("start", (0, 0)))
            end = pymupdf.Point(*ann.get("end", (0, 0)))
            width = ann.get("width", 2)
            page.draw_line(start, end, color=color, width=width)
            dx = end.x - start.x
            dy = end.y - start.y
            length = (dx * dx + dy * dy) ** 0.5
            if length > 4:
                head_len = min(20.0, max(6.0, length * 0.25))
                ux = dx / length
                uy = dy / length
                perp_x = -uy
                perp_y = ux
                wing_w = head_len * 0.45
                base_x = end.x - ux * head_len
                base_y = end.y - uy * head_len
                w1 = pymupdf.Point(base_x + perp_x * wing_w, base_y + perp_y * wing_w)
                w2 = pymupdf.Point(base_x - perp_x * wing_w, base_y - perp_y * wing_w)
                page.draw_line(w1, end, color=color, width=width)
                page.draw_line(w2, end, color=color, width=width)
        elif atype == "redact":
            r = pymupdf.Rect(*ann["rect"])
            page.add_redact_annot(r, fill=(0, 0, 0))
            did_redact = True
    if did_redact:
        page.apply_redactions()


def save_annotated_pdf(doc: pymupdf.Document, output_path: str) -> None:
    doc.save(output_path)


def extract_pdf_text(input_path: str, mode: str = "plain", page_separator: bool = True) -> str:
    """Extract text from PDF pages in plain or markdown format with optional separators."""
    with pymupdf.open(input_path) as doc:
        parts = []
        for page_num, page in enumerate(doc, start=1):
            if mode == "markdown":
                # fitz can output Markdown-flavoured text
                text = page.get_text("markdown").strip()
            else:
                text = page.get_text("text").strip()

            if page_separator:
                parts.append(f"--- Page {page_num} ---\n{text}")
            else:
                parts.append(text)

        return "\n\n".join(parts)


def save_pdf_text(input_path: str, output_path: str, mode: str = "plain") -> str:
    """Extract text from *input_path* and write it to *output_path*.

    Returns the output path.
    """
    content = extract_pdf_text(input_path, mode=mode)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path


def add_pdf_watermark(
    input_path: str,
    output_path: str,
    text: str = "CONFIDENTIAL",
    opacity: float = 0.25,
    font_size: int = 64,
    color: tuple[float, float, float] = (0.8, 0.0, 0.0),
    angle: float = 45.0,
    pages: list[int] | None = None,
) -> str:
    """Add a diagonal text watermark with custom opacity, font size, color, and angle."""
    import math
    with pymupdf.open(input_path) as doc:
        for page_idx, page in enumerate(doc):
            if pages is not None and (page_idx + 1) not in pages:
                continue

            rect = page.rect
            center_x = rect.width / 2
            center_y = rect.height / 2

            r, g, b = color

            # Estimate text width for centering
            try:
                text_w = pymupdf.get_text_length(text, fontname="helv", fontsize=font_size)
            except Exception:
                text_w = len(text) * font_size * 0.55

            # Place the text origin at the page center, then rotate around that center
            pivot = pymupdf.Point(center_x, center_y)
            m = pymupdf.Matrix(angle)  # rotation-only matrix

            shape = page.new_shape()
            shape.insert_text(
                pymupdf.Point(center_x - text_w / 2, center_y),
                text,
                fontsize=font_size,
                color=(r, g, b),
                fill_opacity=opacity,
                stroke_opacity=opacity,
                morph=(pivot, m),
            )
            shape.finish()
            shape.commit(overlay=True)

        doc.save(output_path, garbage=4, deflate=True)
    return output_path



def add_image_watermark(
    input_path: str,
    output_path: str,
    watermark_image_path: str,
    opacity: float = 0.3,
    position: str = "center",
    pages: list[int] | None = None,
) -> str:
    """Stamp an image watermark on a PDF.

    Position can be "center", "bottom-right", "bottom-left", "top-right", "top-left".
    """
    with pymupdf.open(input_path) as doc:
        for page_idx, page in enumerate(doc):
            if pages is not None and (page_idx + 1) not in pages:
                continue

            pr = page.rect
            wm_size = min(pr.width, pr.height) * 0.35

            if position == "center":
                x0 = (pr.width - wm_size) / 2
                y0 = (pr.height - wm_size) / 2
            elif position == "bottom-right":
                x0 = pr.width - wm_size - 20
                y0 = pr.height - wm_size - 20
            elif position == "bottom-left":
                x0 = 20
                y0 = pr.height - wm_size - 20
            elif position == "top-right":
                x0 = pr.width - wm_size - 20
                y0 = 20
            else:  # top-left
                x0 = 20
                y0 = 20

            wm_rect = pymupdf.Rect(x0, y0, x0 + wm_size, y0 + wm_size)

            with open(watermark_image_path, "rb") as wf:
                img_data = wf.read()

            page.insert_image(wm_rect, stream=img_data, overlay=True, fill_opacity=opacity)

        doc.save(output_path, garbage=4, deflate=True)
    return output_path


@dataclass
class BatchPdfItem:
    """Tracks one file's progress through a batch PDF operation."""
    input_path: str
    status: str = "pending"  # "pending", "done", "failed"
    error: Optional[str] = None
    output_path: Optional[str] = None


def _unique_output_path(output_dir: str, filename: str) -> str:
    """Return a path for *filename* inside *output_dir*, deduping with _1, _2... on collision."""
    candidate = os.path.join(output_dir, filename)
    if not os.path.exists(candidate):
        return candidate
    stem, ext = os.path.splitext(filename)
    counter = 1
    while True:
        candidate = os.path.join(output_dir, f"{stem}_{counter}{ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def _run_pdf_batch(
    items: list[BatchPdfItem],
    output_dir: str,
    op: Callable[[str, str], None],
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> list[BatchPdfItem]:
    """Run a single-file PDF operation over every item, recording status per item.

    op(input_path, output_path) performs the actual work. A per-file failure
    is recorded on that item rather than aborting the rest of the batch.
    """
    os.makedirs(output_dir, exist_ok=True)
    total = len(items)
    for idx, item in enumerate(items):
        filename = os.path.basename(item.input_path)
        try:
            out_path = _unique_output_path(output_dir, filename)
            op(item.input_path, out_path)
            item.status = "done"
            item.output_path = out_path
            item.error = None
        except Exception as exc:
            item.status = "failed"
            item.error = str(exc)
            item.output_path = None
        if progress_cb:
            progress_cb(idx + 1, total, filename)
    return items


def batch_compress_pdfs(
    items: list[BatchPdfItem],
    output_dir: str,
    dpi: int = 120,
    quality: str = "ebook",
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> list[BatchPdfItem]:
    """Compress multiple PDFs, writing each to output_dir and tracking status per item."""
    return _run_pdf_batch(
        items, output_dir,
        lambda inp, out: compress_pdf(inp, out, dpi=dpi, quality=quality),
        progress_cb,
    )


def batch_add_pdf_watermark(
    items: list[BatchPdfItem],
    output_dir: str,
    text: str = "CONFIDENTIAL",
    opacity: float = 0.25,
    font_size: int = 64,
    color: tuple[float, float, float] = (0.8, 0.0, 0.0),
    angle: float = 45.0,
    pages: list[int] | None = None,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> list[BatchPdfItem]:
    """Stamp a text watermark on multiple PDFs, tracking status per item."""
    return _run_pdf_batch(
        items, output_dir,
        lambda inp, out: add_pdf_watermark(
            inp, out, text=text, opacity=opacity, font_size=font_size, color=color, angle=angle, pages=pages
        ),
        progress_cb,
    )


def batch_add_image_watermark(
    items: list[BatchPdfItem],
    output_dir: str,
    watermark_image_path: str,
    opacity: float = 0.3,
    position: str = "center",
    pages: list[int] | None = None,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> list[BatchPdfItem]:
    """Stamp an image watermark on multiple PDFs, tracking status per item."""
    return _run_pdf_batch(
        items, output_dir,
        lambda inp, out: add_image_watermark(
            inp, out, watermark_image_path, opacity=opacity, position=position, pages=pages
        ),
        progress_cb,
    )


def batch_protect_pdfs(
    items: list[BatchPdfItem],
    output_dir: str,
    user_password: str,
    owner_password: Optional[str] = None,
    allow_printing: bool = True,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> list[BatchPdfItem]:
    """Password-protect multiple PDFs, tracking status per item."""
    return _run_pdf_batch(
        items, output_dir,
        lambda inp, out: protect_pdf(inp, out, user_password, owner_password, allow_printing),
        progress_cb,
    )


def list_pdf_bookmarks(input_path: str) -> list[dict]:
    """Return PDF bookmark entries as a list of {level, title, page} dictionaries."""
    with pymupdf.open(input_path) as doc:
        entries = []
        for level, title, page, *_ in doc.get_toc(simple=True):
            entries.append({"level": int(level), "title": str(title), "page": int(page)})
        return entries


def add_pdf_bookmarks(input_path: str, output_path: str, bookmarks: list[dict]) -> str:
    """Create or replace PDF bookmark entries from a simple list of dicts."""
    with pymupdf.open(input_path) as doc:
        toc = []
        for item in bookmarks:
            level = int(item.get("level", 1))
            title = str(item.get("title", "Untitled"))
            page = int(item.get("page", 1))
            toc.append([level, title, max(1, page)])
        doc.set_toc(toc)
        doc.save(output_path, garbage=4, deflate=True)
    return output_path


def list_pdf_attachments(input_path: str) -> list[dict]:
    """Return metadata for all embedded PDF attachments."""
    with pymupdf.open(input_path) as doc:
        names = doc.embfile_names()
        attachments = []
        for name in names:
            info = doc.embfile_info(name)
            attachments.append({
                "name": info.get("name", name),
                "filename": info.get("filename", name),
                "description": info.get("description", ""),
                "size": int(info.get("size", 0)),
            })
        return attachments


def add_pdf_attachment(input_path: str, output_path: str, attachment_path: str, name: str | None = None, description: str | None = None) -> str:
    """Embed a file into a PDF as an attachment."""
    with pymupdf.open(input_path) as doc:
        with open(attachment_path, "rb") as fh:
            data = fh.read()
        emb_name = name or os.path.basename(attachment_path)
        doc.embfile_add(emb_name, data, filename=os.path.basename(attachment_path), desc=description or "")
        doc.save(output_path, garbage=4, deflate=True)
    return output_path


def add_pdf_signature(
    input_path: str,
    output_path: str,
    signature_image_path: str,
    x: float = 72.0,
    y: float = 72.0,
    width: float = 140.0,
    height: float = 40.0,
    pages: list[int] | None = None,
) -> str:
    """Stamp a signature image onto a PDF in a fixed corner placement."""
    with pymupdf.open(input_path) as doc:
        with open(signature_image_path, "rb") as fh:
            img_data = fh.read()
        for page_idx, page in enumerate(doc):
            if pages is not None and (page_idx + 1) not in pages:
                continue
            rect = pymupdf.Rect(x, y, x + width, y + height)
            page.insert_image(rect, stream=img_data, overlay=True)
        doc.save(output_path, garbage=4, deflate=True)
    return output_path


def add_page_numbers(
    input_path: str,
    output_path: str,
    format_str: str = "Page {n} of {total}",
    position: str = "bottom_center",
    font_size: float = 10.0,
    color: tuple[float, float, float] = (0.2, 0.2, 0.2),
    margin_x: float = 36.0,
    margin_y: float = 36.0,
    start_num: int = 1,
    pages: list[int] | None = None,
) -> str:
    """Stamp custom page numbers/labels with format keys {n}/{page}/{total} and position control."""
    with pymupdf.open(input_path) as doc:
        total = doc.page_count
        for page_idx, page in enumerate(doc):
            curr_page = page_idx + 1
            if pages is not None and curr_page not in pages:
                continue

            n_val = curr_page - 1 + start_num
            label = format_str.format(n=n_val, page=n_val, total=total)  # noqa: 16

            rect = page.rect
            text_width = pymupdf.get_text_length(label, fontname="helv", fontsize=font_size)

            pos = position.lower().replace("-", "_")
            if "top" in pos:
                y = margin_y + font_size
            else:  # bottom
                y = rect.height - margin_y

            if "left" in pos:
                x = margin_x
            elif "right" in pos:
                x = max(0, rect.width - margin_x - text_width)
            else:  # center
                x = max(0, (rect.width - text_width) / 2)

            page.insert_text(
                pymupdf.Point(x, y),
                label,
                fontsize=font_size,
                fontname="helv",
                color=color,
                overlay=True,
            )

        doc.save(output_path, garbage=4, deflate=True)
    return output_path


def convert_pdf_to_docx(input_path: str, output_path: str, start_page: int = 0, end_page: int | None = None) -> str:
    """Convert a PDF to an editable DOCX file, recovering text layout, tables, and headings."""
    from pdf2docx import Converter as _Pdf2DocxConverter  # noqa: 13 (heavy optional dep, kept out of the always-eager PDF-viewing import path)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    converter = _Pdf2DocxConverter(input_path)
    try:
        converter.convert(output_path, start=start_page, end=end_page)
    finally:
        converter.close()
    return output_path


def pdf_needs_ocr(input_path: str, min_chars_per_page: int = 20) -> bool:
    """Return True if no page in the PDF has a meaningful extractable text layer (i.e. it is scanned)."""
    with pymupdf.open(input_path) as doc:
        for page in doc:
            if len(page.get_text().strip()) >= min_chars_per_page:
                return False
    return True


def convert_scanned_pdf_to_docx(
    input_path: str,
    output_path: str,
    language: str = "eng",
    start_page: int = 0,
    end_page: int | None = None,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> str:
    """Convert a PDF to DOCX, running local OCR first only if the PDF has no real text layer.

    Text-based PDFs are delegated straight to convert_pdf_to_docx, which recovers layout,
    tables, and headings. A scanned/image-only PDF has no visual text for pdf2docx to
    reconstruct (it ignores the invisible OCR text layer), so its recovered OCR text (via
    ocr_ops.ocr_pdf) is written out directly as DOCX paragraphs, one page section at a time.
    """
    if not pdf_needs_ocr(input_path):
        if progress_cb:
            progress_cb(1, 1, "Converting to DOCX...")
        return convert_pdf_to_docx(input_path, output_path, start_page=start_page, end_page=end_page)

    from app.features.ocr import ops as ocr_ops  # noqa: 13 (keeps PIL out of every PDF tab's cold-start import)
    with pymupdf.open(input_path) as doc:
        total_pages = len(doc)
    last_page = end_page if end_page is not None else total_pages
    page_numbers = list(range(start_page + 1, last_page + 1))

    def _ocr_progress(done: int, total: int) -> None:
        if progress_cb:
            progress_cb(done, total, "Running OCR on scanned pages...")

    result = ocr_ops.ocr_pdf(input_path, pages=page_numbers, language=language, progress_callback=_ocr_progress)

    if progress_cb:
        progress_cb(1, 1, "Writing Word document...")

    from docx import Document as _DocxDocument  # noqa: 13 (heavy optional dep, kept out of the always-eager PDF-viewing import path)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    document = _DocxDocument()
    for page_number, page_text in zip(page_numbers, result["page_texts"]):
        document.add_heading(f"Page {page_number}", level=2)
        for line in page_text.splitlines():
            if line.strip():
                document.add_paragraph(line.strip())
    document.save(output_path)
    return output_path

