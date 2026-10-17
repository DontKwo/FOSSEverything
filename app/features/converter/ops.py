"""Local, capability-driven file conversion operations.

The module exposes only conversions backed by FOSSEverything's installed engines.
Additional engines (for example FFmpeg or LibreOffice) can extend the same
functions later without making the UI promise unsupported conversions.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from fontTools.ttLib import TTFont

from app.features.data import ops as data_ops
from app.features.image import ops as image_ops
from app.features.pdf import ops as pdf_ops
from app.core.file_formats import extension_for_format, normalized_format


IMAGE_EXTENSIONS = {
    ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp",
    ".heic", ".heif", ".avif", ".svg", ".psd",
    ".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw",
}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma", ".opus"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".m4v"}
OFFICE_EXTENSIONS = {".docx", ".pptx", ".xlsx", ".odt", ".ods", ".odp", ".docm", ".pptm", ".xlsm"}
PDF_EXTENSION = ".pdf"
MODEL3D_EXTENSIONS = {".stl", ".obj", ".ply", ".step", ".stp", ".iges", ".igs"}
FONT_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2"}
EBOOK_EXTENSIONS = {".epub", ".mobi", ".azw", ".azw3", ".fb2"}
NOTE_EXTENSIONS = {".enex"}


def calibre_backend_available() -> bool:
    """Return True when Calibre's local ebook-convert CLI is installed and reachable."""
    return shutil.which("ebook-convert") is not None


def convert_ebook(input_path: str, output_path: str) -> str:
    """Convert between e-book formats using a locally installed Calibre."""
    exe = shutil.which("ebook-convert")
    if not exe:
        raise RuntimeError(
            "E-book conversion requires Calibre installed locally (ebook-convert on PATH). "
            "Install it from calibre-ebook.com to enable this feature."
        )
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    res = subprocess.run([exe, input_path, output_path], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Calibre conversion failed:\n{res.stderr}")
    return output_path


def _strip_enml_to_text(enml: str) -> str:
    """Reduce an ENML/XHTML note body to readable plain text (no rendering fidelity)."""
    text = re.sub(r"<br\s*/?>", "\n", enml, flags=re.IGNORECASE)
    text = re.sub(r"</div>|</en-note>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def parse_enex(input_path: str) -> list[dict]:
    """Parse an Evernote ENEX export into a list of note dictionaries.

    Each note dict has: title, content (plain text), created, updated, tags.
    Resource attachments are not extracted (text-only import).
    """
    tree = ET.parse(input_path)
    root = tree.getroot()
    notes: list[dict] = []
    for note_el in root.findall("note"):
        title = (note_el.findtext("title") or "Untitled Note").strip()
        content_raw = note_el.findtext("content") or ""
        tags = [tag_el.text.strip() for tag_el in note_el.findall("tag") if tag_el.text]
        notes.append({
            "title": title,
            "content": _strip_enml_to_text(content_raw),
            "created": (note_el.findtext("created") or "").strip(),
            "updated": (note_el.findtext("updated") or "").strip(),
            "tags": tags,
        })
    return notes


def export_enex(notes: list[dict], output_path: str) -> str:
    """Write a minimal, valid ENEX file from a list of note dictionaries."""
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = ET.Element("en-export")
    for note in notes:
        note_el = ET.SubElement(root, "note")
        ET.SubElement(note_el, "title").text = str(note.get("title", "Untitled Note"))
        body = html.escape(str(note.get("content", ""))).replace("\n", "<br/>")
        content_el = ET.SubElement(note_el, "content")
        content_el.text = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
            f'<en-note>{body}</en-note>'
        )
        ET.SubElement(note_el, "created").text = str(note.get("created") or now)
        ET.SubElement(note_el, "updated").text = str(note.get("updated") or now)
        for tag in note.get("tags", []):
            ET.SubElement(note_el, "tag").text = str(tag)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    ET.ElementTree(root).write(output_path, encoding="UTF-8", xml_declaration=True)
    return output_path


def _font_has_cff_outlines(path: str) -> bool:
    font = TTFont(path, lazy=True)
    try:
        return "CFF " in font
    finally:
        font.close()


def convert_font(input_path: str, output_path: str) -> str:
    """Repackage a font between raw TTF/OTF and compressed WOFF/WOFF2, keeping its outlines."""
    out_ext = os.path.splitext(output_path)[1].lower()
    font = TTFont(input_path)
    try:
        has_cff = "CFF " in font
        if out_ext == ".woff":
            font.flavor = "woff"  # noqa: 21
        elif out_ext == ".woff2":
            font.flavor = "woff2"  # noqa: 21
        elif out_ext in (".ttf", ".otf"):
            wants_cff = out_ext == ".otf"
            if has_cff != wants_cff:
                raise ValueError(
                    f"Cannot convert this font to {out_ext}: it has {'CFF' if has_cff else 'TrueType'} outlines, "
                    f"which cannot be changed to {'CFF' if wants_cff else 'TrueType'} outlines by repackaging alone."
                )
            font.flavor = None  # noqa: 21
        else:
            raise ValueError(f"Unsupported font output format: {out_ext}")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        font.save(output_path)
    finally:
        font.close()
    return output_path


def source_family(path: str) -> str | None:
    """Return the local converter family capable of reading *path*."""
    extension = os.path.splitext(path)[1].lower()
    if extension == PDF_EXTENSION:
        return "PDF"
    if extension in IMAGE_EXTENSIONS:
        return "Image"
    if extension in VIDEO_EXTENSIONS:
        return "Video"
    if extension in AUDIO_EXTENSIONS:
        return "Audio"
    if extension in OFFICE_EXTENSIONS:
        return "Office"
    if extension in MODEL3D_EXTENSIONS:
        return "Model3D"
    if extension in FONT_EXTENSIONS:
        return "Font"
    if extension in EBOOK_EXTENSIONS:
        return "Ebook"
    if extension in NOTE_EXTENSIONS:
        return "Note"
    if data_ops.data_format_for_path(path):
        return "Data"
    return None


def available_targets(path: str) -> list[str]:
    """List only formats the installed local engines can write for *path*."""
    family = source_family(path)
    ext = os.path.splitext(path)[1].lower()
    if family == "Image":
        return image_ops.SINGLE_IMAGE_EXPORT_FORMATS + ["PDF (Searchable)", "TXT", "MD"]
    if family == "PDF":
        return pdf_ops.PAGE_IMAGE_FORMATS + ["PDF (Searchable)", "DOCX", "TXT", "MD"]
    if family == "Office":
        if ext in (".docx", ".docm", ".odt"):
            return ["PDF", "TXT", "MD"]
        elif ext in (".xlsx", ".xlsm", ".ods"):
            return ["CSV", "JSON", "TXT", "MD"]
        elif ext in (".pptx", ".pptm", ".odp"):
            return ["TXT", "MD"]
        return ["TXT", "MD"]
    if family == "Video":
        return ["MP4", "MKV", "MOV", "WEBM", "AVI", "MP3", "WAV", "AAC", "FLAC", "M4A"]
    if family == "Audio":
        return ["MP3", "WAV", "AAC", "FLAC", "M4A", "OGG"]
    if family == "Data":
        return data_ops.DATA_FORMATS
    if family == "Model3D":
        from app.features.model3d import ops as model3d_ops
        targets = ["STL", "OBJ", "PLY"]
        if model3d_ops.brep_backend_available():
            targets += ["STEP", "IGES"]
        return targets
    if family == "Font":
        targets = ["WOFF", "WOFF2"]
        try:
            has_cff = _font_has_cff_outlines(path)
        except Exception:
            return targets
        targets.append("OTF" if has_cff else "TTF")
        return targets
    if family == "Ebook":
        if not calibre_backend_available():
            return []
        current_ext = os.path.splitext(path)[1].lower()
        return [normalized_format(e) for e in ("epub", "mobi", "azw3", "fb2") if e != current_ext.lstrip(".")]
    if family == "Note":
        return ["MD", "TXT"]
    return []


def conversion_summary(path: str, target_format: str) -> str:
    """Explain output shape before the user writes files."""
    family = source_family(path)
    target = normalized_format(target_format)
    if target_format == "PDF (Searchable)":
        return "The document/image will be converted to a PDF with an embedded invisible OCR text layer."
    if family == "PDF" and target == "DOCX":
        return "The PDF will be converted to an editable Word document, recovering text layout, tables, and headings where possible."
    if family == "Office":
        if target == "PDF":
            return "The Office document will be formatted and rendered into a high-quality PDF."
        if target in ("TXT", "TEXT"):
            return "Extract all text, paragraphs, and tables from the Office document into plain text."
        if target in ("MD", "MARKDOWN"):
            return "Convert headings, paragraphs, and tables from the Office document into clean Markdown."
        if target == "CSV":
            return "Extract the active spreadsheet worksheet into standard CSV format."
        if target == "JSON":
            return "Convert spreadsheet rows and columns into structured JSON format."
    if family == "Note":
        return f"Every note in the Evernote ENEX export will be combined into a single {target} file, separated by dividers."
    if target in ("TXT", "TEXT"):
        return f"Extract text from the {family} to a plain text file using local OCR/extraction."
    if target in ("MD", "MARKDOWN"):
        return f"Extract text from the {family} to a Markdown formatted document."
    if family == "Video":
        if target_format.upper() in ("MP3", "WAV", "AAC", "FLAC", "M4A", "OGG"):
            return f"Extract audio from video to {target_format.upper()} audio format."
        return f"Transcode video to {target_format.upper()} container."
    if family == "Audio":
        return f"Convert audio to {target_format.upper()} format."
    if family == "PDF":
        return f"Every PDF page will be exported as a separate {target} image."
    if family == "Image":
        return f"The image will be converted to {target}."
    if family == "Data":
        return f"Structured data will be converted to {target}. Nested values cannot be safely written to CSV."
    if family == "Model3D":
        if target in ("STEP", "IGES"):
            return f"The 3D model will be converted to a faceted (triangle-based) {target} solid or shell."
        return f"The 3D model will be tessellated (if needed) and converted to {target}."
    if family == "Font":
        if target in ("WOFF", "WOFF2"):
            return f"The font will be repackaged as a compressed {target} web font, keeping its existing outlines."
        return f"The font will be unpacked to a raw {target} file, keeping its existing outlines."
    if family == "Ebook":
        return f"The e-book will be converted to {target} using a locally installed Calibre."
    return "This file type is not supported by the installed local converters."


def convert_file(input_path: str, output_dir: str, target_format: str, dpi: int = 144, output_stem: str | None = None, progress_cb: Callable[[int, int, str], None] | None = None) -> list[str]:
    """Convert one file locally and return every output path written."""
    family = source_family(input_path)
    if target_format not in available_targets(input_path):
        target = normalized_format(target_format)
        if target not in [normalized_format(t) for t in available_targets(input_path)]:
            raise ValueError(f"Cannot convert this {family or 'unknown'} file to {target_format} with installed local engines.")
    os.makedirs(output_dir, exist_ok=True)
    base = output_stem or os.path.splitext(os.path.basename(input_path))[0]

    # Handle Video & Audio conversion
    if family in ("Video", "Audio"):
        from app.features.media import ops as media_ops
        ext = f".{target_format.lower().lstrip('.')}"
        output_path = os.path.join(output_dir, f"{base}{ext}")
        media_ops.convert_media(input_path, output_path, target_format=target_format)
        if progress_cb:
            progress_cb(1, 1, os.path.basename(output_path))
        return [output_path]


    # Handle Searchable PDF target
    if target_format == "PDF (Searchable)":
        from app.features.ocr import ops as ocr_ops
        output_path = os.path.join(output_dir, f"{base}_searchable.pdf")
        ocr_ops.create_searchable_pdf(input_path, output_path, dpi=dpi)
        if progress_cb:
            progress_cb(1, 1, os.path.basename(output_path))
        return [output_path]

    # Handle Office file conversions
    if family == "Office":
        from app.features.office import ops as office_ops
        norm_t = normalized_format(target_format)
        if norm_t == "PDF":
            output_path = os.path.join(output_dir, f"{base}.pdf")
            office_ops.docx_to_pdf(input_path, output_path)
            if progress_cb:
                progress_cb(1, 1, os.path.basename(output_path))
            return [output_path]
        elif norm_t in ("MD", "MARKDOWN"):
            output_path = os.path.join(output_dir, f"{base}.md")
            ext = os.path.splitext(input_path)[1].lower()
            if ext in (".docx", ".docm"):
                md = office_ops.docx_to_markdown(input_path)
            elif ext in (".pptx", ".pptm"):
                md = office_ops.pptx_to_markdown(input_path)
            else:
                md = office_ops.extract_text_from_office(input_path)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(md)
            if progress_cb:
                progress_cb(1, 1, os.path.basename(output_path))
            return [output_path]
        elif norm_t in ("TXT", "TEXT"):
            output_path = os.path.join(output_dir, f"{base}.txt")
            txt = office_ops.extract_text_from_office(input_path)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(txt)
            if progress_cb:
                progress_cb(1, 1, os.path.basename(output_path))
            return [output_path]
        elif norm_t == "CSV":
            output_path = os.path.join(output_dir, f"{base}.csv")
            office_ops.xlsx_to_csv(input_path, output_path)
            if progress_cb:
                progress_cb(1, 1, os.path.basename(output_path))
            return [output_path]
        elif norm_t == "JSON":
            output_path = os.path.join(output_dir, f"{base}.json")
            txt = office_ops.extract_text_xlsx(input_path)
            data = {"content": txt}
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            if progress_cb:
                progress_cb(1, 1, os.path.basename(output_path))
            return [output_path]

    # Handle Evernote ENEX notes export -> combined Markdown/plain-text file
    if family == "Note":
        norm_t = normalized_format(target_format)
        is_md = norm_t in ("MD", "MARKDOWN")
        ext = ".md" if is_md else ".txt"
        output_path = os.path.join(output_dir, f"{base}{ext}")
        notes = parse_enex(input_path)
        parts = []
        for note in notes:
            heading = f"## {note['title']}" if is_md else note["title"]
            meta = " / ".join(v for v in (note.get("created"), *note.get("tags", [])) if v)
            body = f"{heading}\n\n{meta}\n\n{note['content']}" if meta else f"{heading}\n\n{note['content']}"
            parts.append(body)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n\n---\n\n".join(parts) + "\n")
        if progress_cb:
            progress_cb(1, 1, os.path.basename(output_path))
        return [output_path]

    # Handle TXT / MD targets for Images/PDFs via OCR
    norm_t = normalized_format(target_format)
    if norm_t in ("TXT", "TEXT", "MD", "MARKDOWN"):
        from app.features.ocr import ops as ocr_ops
        is_md = norm_t in ("MD", "MARKDOWN")
        ext = ".md" if is_md else ".txt"
        output_path = os.path.join(output_dir, f"{base}{ext}")
        res = ocr_ops.ocr_file(input_path, dpi=dpi)
        ocr_ops.save_ocr_text(res, output_path, as_markdown=is_md)
        if progress_cb:
            progress_cb(1, 1, os.path.basename(output_path))
        return [output_path]

    target = norm_t
    if family == "Model3D":
        from app.features.model3d import ops as model3d_ops
        model = model3d_ops.load(input_path)
        output_path = os.path.join(output_dir, f"{base}{extension_for_format(target)}")
        model3d_ops.export(model, output_path, fmt=target)
        if progress_cb:
            progress_cb(1, 1, os.path.basename(output_path))
        return [output_path]
    if family == "Font":
        output_path = os.path.join(output_dir, f"{base}{extension_for_format(target)}")
        convert_font(input_path, output_path)
        if progress_cb:
            progress_cb(1, 1, os.path.basename(output_path))
        return [output_path]
    if family == "Ebook":
        output_path = os.path.join(output_dir, f"{base}{extension_for_format(target)}")
        convert_ebook(input_path, output_path)
        if progress_cb:
            progress_cb(1, 1, os.path.basename(output_path))
        return [output_path]
    if family == "PDF" and target == "DOCX":
        output_path = os.path.join(output_dir, f"{base}.docx")
        pdf_ops.convert_scanned_pdf_to_docx(input_path, output_path, progress_cb=progress_cb)
        if progress_cb:
            progress_cb(1, 1, os.path.basename(output_path))
        return [output_path]
    if family == "PDF":
        return pdf_ops.export_pdf_pages(input_path, output_dir, target, dpi, output_stem, progress_cb)
    if family == "Data":
        output_path = os.path.join(output_dir, f"{base}{extension_for_format(target)}")
        data_ops.save_data(data_ops.load_data(input_path), output_path, target)
        if progress_cb:
            progress_cb(1, 1, os.path.basename(output_path))
        return [output_path]

    image = image_ops.load_image(input_path)
    output_path = os.path.join(output_dir, f"{base}{extension_for_format(target)}")
    image_ops.save_image(image, output_path, format=target)
    if progress_cb:
        progress_cb(1, 1, os.path.basename(output_path))
    return [output_path]



@dataclass
class BatchConversionItem:
    input_path: str
    target_format: str
    output_stem: str | None = None
    status: str = "pending"  # "pending", "done", "failed"
    error: str | None = None
    output_paths: list[str] = field(default_factory=list)


def batch_convert_files(
    items: list[BatchConversionItem],
    output_dir: str,
    dpi: int = 144,
    progress_cb: Callable[[int, int, BatchConversionItem], None] | None = None,
) -> list[BatchConversionItem]:
    """Convert multiple files sequentially, tracking and updating item statuses."""
    os.makedirs(output_dir, exist_ok=True)
    total = len(items)
    for idx, item in enumerate(items):
        try:
            outs = convert_file(
                item.input_path,
                output_dir,
                item.target_format,
                dpi=dpi,
                output_stem=item.output_stem,
            )
            item.status = "done"
            item.output_paths = outs
            item.error = None
        except Exception as exc:
            item.status = "failed"
            item.error = str(exc)
            item.output_paths = []
        if progress_cb:
            progress_cb(idx + 1, total, item)
    return items

