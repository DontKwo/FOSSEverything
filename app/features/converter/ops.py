"""Local, capability-driven file conversion operations.

The module exposes only conversions backed by FOSSEverything's installed engines.
Additional engines (for example FFmpeg or LibreOffice) can extend the same
functions later without making the UI promise unsupported conversions.
"""
from __future__ import annotations

import csv
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
SUBTITLE_EXTENSIONS = {".srt", ".vtt"}
PLAYLIST_EXTENSIONS = {".m3u", ".m3u8"}
CALENDAR_EXTENSIONS = {".ics"}


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


def convert_subtitle(input_path: str, output_path: str, target_format: str) -> str:
    # Convert subtitles between SRT, VTT, and plain text.
    with open(input_path, "r", encoding="utf-8", errors="replace") as f_in:
        content = f_in.read()
    fmt = normalized_format(target_format)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    if fmt in ("TXT", "TEXT"):
        lines: list[str] = []
        for line in content.splitlines():
            line_str = line.strip()
            if not line_str or line_str.isdigit() or re.match(r"^\d{1,2}:\d{2}:\d{2}", line_str) or line_str == "WEBVTT":
                continue
            clean = re.sub(r"<[^>]+>", "", line_str).strip()
            if clean:
                lines.append(clean)
        with open(output_path, "w", encoding="utf-8") as f_out:
            f_out.write("\n".join(lines) + "\n")
    elif fmt == "VTT":
        converted = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", content)
        if not converted.lstrip().startswith("WEBVTT"):
            converted = "WEBVTT\n\n" + converted.lstrip()
        with open(output_path, "w", encoding="utf-8") as f_out:
            f_out.write(converted)
    elif fmt == "SRT":
        converted = re.sub(r"^WEBVTT[^\n]*\n+", "", content, flags=re.MULTILINE)
        converted = re.sub(r"(\d{2}:\d{2}:\d{2})\.(\d{3})", r"\1,\2", converted)
        blocks = [b.strip() for b in re.split(r"\n\s*\n", converted.strip()) if b.strip()]
        out_blocks: list[str] = []
        for idx, blk in enumerate(blocks, start=1):
            blines = blk.splitlines()
            if blines and blines[0].strip().isdigit():
                blines[0] = str(idx)
            else:
                blines.insert(0, str(idx))
            out_blocks.append("\n".join(blines))
        with open(output_path, "w", encoding="utf-8") as f_out:
            f_out.write("\n\n".join(out_blocks) + "\n")
    else:
        raise ValueError(f"Unsupported subtitle target format: {target_format}")
    return output_path


def convert_playlist(input_path: str, output_path: str, target_format: str) -> str:
    # Convert audio/video playlists between M3U8, CSV, JSON, and TXT tracklists.
    from app.features.playlist.ops import PlaylistTrack, export_csv_playlist, export_m3u8_playlist
    tracks: list[PlaylistTrack] = []
    ext = os.path.splitext(input_path)[1].lower()
    if ext in (".m3u", ".m3u8", ".txt"):
        with open(input_path, "r", encoding="utf-8", errors="replace") as f_in:
            lines = [raw_line.strip() for raw_line in f_in if raw_line.strip()]
        cur_title = ""
        cur_artist = ""
        for line in lines:
            if line.startswith("#EXTINF:"):
                info = line.split(":", 1)[1]
                parts = info.split(",", 1)
                name = parts[1].strip() if len(parts) > 1 else ""
                if " - " in name:
                    cur_artist, cur_title = name.split(" - ", 1)
                else:
                    cur_title = name
            elif not line.startswith("#"):
                p_url = line
                if not cur_title:
                    cur_title = os.path.splitext(os.path.basename(p_url))[0]
                tracks.append(PlaylistTrack(title=cur_title.strip(), artist=cur_artist.strip(), album="", duration="", url=p_url))
                cur_title = ""
                cur_artist = ""
    elif ext == ".csv":
        with open(input_path, "r", encoding="utf-8", errors="replace") as f_in:
            reader = csv.DictReader(f_in)
            for row in reader:
                tracks.append(PlaylistTrack(
                    title=row.get("title", row.get("Title", "")),
                    artist=row.get("artist", row.get("Artist", "")),
                    album=row.get("album", row.get("Album", "")),
                    duration=row.get("duration", row.get("Duration", "")),
                    url=row.get("url", row.get("URL", row.get("path", "")))
                ))
    elif ext == ".json":
        with open(input_path, "r", encoding="utf-8", errors="replace") as f_in:
            data = json.load(f_in)
            if isinstance(data, list):
                for row in data:
                    tracks.append(PlaylistTrack(
                        title=str(row.get("title", "")),
                        artist=str(row.get("artist", "")),
                        album=str(row.get("album", "")),
                        duration=str(row.get("duration", "")),
                        url=str(row.get("url", row.get("path", "")))
                    ))

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    fmt = normalized_format(target_format)
    if fmt in ("M3U", "M3U8"):
        export_m3u8_playlist(tracks, output_path)
    elif fmt == "CSV":
        export_csv_playlist(tracks, output_path)
    elif fmt == "JSON":
        with open(output_path, "w", encoding="utf-8") as f_out:
            json.dump([{"title": t.title, "artist": t.artist, "album": t.album, "duration": t.duration, "url": t.url} for t in tracks], f_out, indent=2)
    elif fmt in ("TXT", "TEXT"):
        with open(output_path, "w", encoding="utf-8") as f_out:
            for t in tracks:
                line = f"{t.artist} - {t.title}".strip(" -") if t.artist else t.title
                f_out.write(line + "\n")
    else:
        raise ValueError(f"Unsupported playlist target format: {target_format}")
    return output_path


def convert_calendar(input_path: str, output_path: str, target_format: str) -> str:
    # Convert iCalendar (.ics) to JSON, CSV, or TXT track.
    ext = os.path.splitext(input_path)[1].lower()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    fmt = normalized_format(target_format)
    if ext == ".ics":
        events = data_ops.parse_ics(input_path)
        if fmt == "JSON":
            with open(output_path, "w", encoding="utf-8") as f_out:
                json.dump(events, f_out, indent=2)
        elif fmt == "CSV":
            if events:
                keys = list(events[0].keys())
                with open(output_path, "w", encoding="utf-8", newline="") as f_out:
                    writer = csv.DictWriter(f_out, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(events)
            else:
                with open(output_path, "w", encoding="utf-8") as f_out:
                    f_out.write("")
        elif fmt in ("TXT", "TEXT"):
            with open(output_path, "w", encoding="utf-8") as f_out:
                for ev in events:
                    f_out.write(f"Event: {ev.get('summary', 'Untitled')}\n")
                    f_out.write(f"Start: {ev.get('dtstart', '')}\n")
                    f_out.write(f"End: {ev.get('dtend', '')}\n")
                    if ev.get("description"):
                        f_out.write(f"Description: {ev['description']}\n")
                    f_out.write("\n")
        else:
            raise ValueError(f"Unsupported calendar target format: {target_format}")
    else:
        if ext == ".json":
            with open(input_path, "r", encoding="utf-8", errors="replace") as f_in:
                events = json.load(f_in)
        elif ext == ".csv":
            with open(input_path, "r", encoding="utf-8", errors="replace") as f_in:
                events = list(csv.DictReader(f_in))
        else:
            raise ValueError(f"Cannot convert {ext} to calendar format.")
        data_ops.generate_ics(events, output_path)
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
    if extension in SUBTITLE_EXTENSIONS:
        return "Subtitle"
    if extension in PLAYLIST_EXTENSIONS:
        return "Playlist"
    if extension in CALENDAR_EXTENSIONS:
        return "Calendar"
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
            return ["PDF", "MD", "TXT", "HTML"]
        elif ext in (".pptx", ".pptm", ".odp"):
            return ["PDF", "MD", "TXT", "HTML"]
        elif ext in (".xlsx", ".xlsm", ".ods"):
            return ["CSV", "JSON", "MD", "TXT", "PDF"]
        return ["TXT", "MD"]
    if family == "Video":
        return ["MP4", "MKV", "MOV", "WEBM", "AVI", "MP3", "WAV", "AAC", "FLAC", "M4A"]
    if family == "Audio":
        return ["MP3", "WAV", "AAC", "FLAC", "M4A", "OGG"]
    if family == "Data":
        return data_ops.DATA_FORMATS
    if family == "Subtitle":
        return ["VTT", "TXT"] if ext == ".srt" else ["SRT", "TXT"]
    if family == "Playlist":
        return ["M3U8", "CSV", "JSON", "TXT"]
    if family == "Calendar":
        return ["JSON", "CSV", "TXT"]
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
        return ["MD", "TXT", "HTML"]
    if ext in (".md", ".txt"):
        return ["ENEX"]
    return []


def conversion_summary(path: str, target_format: str) -> str:
    """Explain output shape before the user writes files."""
    family = source_family(path)
    target = normalized_format(target_format)
    if target_format == "PDF (Searchable)":
        return "The document/image will be converted to a PDF with an embedded invisible OCR text layer."
    if family == "PDF" and target == "DOCX":
        return "The PDF will be converted to an editable Word document, recovering text layout, tables, and headings where possible."
    if family == "Subtitle":
        return f"The subtitle file will be converted to {target} format."
    if family == "Playlist":
        return f"The playlist tracklist will be exported to {target} format."
    if family == "Calendar":
        return f"The calendar events will be converted to {target} format."
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
    fmt_norm = target_format.strip().lower()
    if fmt_norm in ("pdf (searchable)", "pdf_searchable"):
        target_format = "PDF (Searchable)"
    family = source_family(input_path)
    if target_format not in available_targets(input_path):
        target = normalized_format(target_format)
        if target not in [normalized_format(t) for t in available_targets(input_path)]:
            raise ValueError(f"Cannot convert this {family or 'unknown'} file to {target_format} with installed local engines.")
    os.makedirs(output_dir, exist_ok=True)
    base = output_stem or os.path.splitext(os.path.basename(input_path))[0]

    # Handle Subtitle conversion
    if family == "Subtitle":
        ext = ".txt" if target_format in ("TXT", "TEXT") else f".{target_format.lower()}"
        output_path = os.path.join(output_dir, f"{base}{ext}")
        convert_subtitle(input_path, output_path, target_format)
        if progress_cb:
            progress_cb(1, 1, os.path.basename(output_path))
        return [output_path]

    # Handle Playlist conversion
    if family == "Playlist":
        ext = ".txt" if target_format in ("TXT", "TEXT") else (".m3u8" if target_format in ("M3U8", "M3U") else f".{target_format.lower()}")
        output_path = os.path.join(output_dir, f"{base}{ext}")
        convert_playlist(input_path, output_path, target_format)
        if progress_cb:
            progress_cb(1, 1, os.path.basename(output_path))
        return [output_path]

    # Handle Calendar conversion
    if family == "Calendar":
        ext = ".txt" if target_format in ("TXT", "TEXT") else f".{target_format.lower()}"
        output_path = os.path.join(output_dir, f"{base}{ext}")
        convert_calendar(input_path, output_path, target_format)
        if progress_cb:
            progress_cb(1, 1, os.path.basename(output_path))
        return [output_path]

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
        stem_str = base if output_stem else f"{base}_searchable"
        output_path = os.path.join(output_dir, f"{stem_str}.pdf")
        ocr_ops.create_searchable_pdf(input_path, output_path, dpi=dpi)
        if progress_cb:
            progress_cb(1, 1, os.path.basename(output_path))
        return [output_path]

    # Handle Office file conversions
    if family == "Office":
        from app.features.converter import office_ops
        from app.features.markdown.ops import build_styled_markdown_document

        norm_t = normalized_format(target_format)
        ext = os.path.splitext(input_path)[1].lower()

        if norm_t == "PDF":
            output_path = os.path.join(output_dir, f"{base}.pdf")
            office_ops.office_to_pdf(input_path, output_path)
            if progress_cb:
                progress_cb(1, 1, os.path.basename(output_path))
            return [output_path]
        elif norm_t in ("MD", "MARKDOWN"):
            output_path = os.path.join(output_dir, f"{base}.md")
            if ext in (".docx", ".docm"):
                md = office_ops.docx_to_markdown(input_path)
            elif ext == ".odt":
                md = office_ops.odt_to_markdown(input_path)
            elif ext in (".pptx", ".pptm"):
                md = office_ops.pptx_to_markdown(input_path)
            elif ext == ".odp":
                md = office_ops.odp_to_markdown(input_path)
            elif ext in (".xlsx", ".xlsm", ".ods"):
                rows = office_ops.ods_to_rows(input_path) if ext == ".ods" else office_ops.xlsx_to_rows(input_path)
                if rows:
                    max_c = max(len(r) for r in rows)
                    norm = [r + [""] * (max_c - len(r)) for r in rows]
                    tbl = ["| " + " | ".join(norm[0]) + " |", "| " + " | ".join(["---"] * max_c) + " |"]
                    for r in norm[1:]:
                        tbl.append("| " + " | ".join(r) + " |")
                    md = "\n".join(tbl)
                else:
                    md = ""
            else:
                md = office_ops.extract_text_from_office(input_path)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(md)
            if progress_cb:
                progress_cb(1, 1, os.path.basename(output_path))
            return [output_path]
        elif norm_t == "HTML":
            output_path = os.path.join(output_dir, f"{base}.html")
            if ext in (".docx", ".docm"):
                md = office_ops.docx_to_markdown(input_path)
            elif ext == ".odt":
                md = office_ops.odt_to_markdown(input_path)
            elif ext in (".pptx", ".pptm"):
                md = office_ops.pptx_to_markdown(input_path)
            elif ext == ".odp":
                md = office_ops.odp_to_markdown(input_path)
            else:
                md = office_ops.extract_text_from_office(input_path)
            doc_html = build_styled_markdown_document(md, flavor="github", theme_mode="light", for_pdf=False)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(doc_html)
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
            office_ops.spreadsheet_to_csv(input_path, output_path)
            if progress_cb:
                progress_cb(1, 1, os.path.basename(output_path))
            return [output_path]
        elif norm_t == "JSON":
            output_path = os.path.join(output_dir, f"{base}.json")
            office_ops.spreadsheet_to_json(input_path, output_path)
            if progress_cb:
                progress_cb(1, 1, os.path.basename(output_path))
            return [output_path]

    # Handle Evernote ENEX notes export -> combined Markdown/plain-text/HTML file
    if family == "Note":
        norm_t = normalized_format(target_format)
        if norm_t == "HTML":
            output_path = os.path.join(output_dir, f"{base}.html")
            notes = parse_enex(input_path)
            parts = [f"<article><h2>{html.escape(n['title'])}</h2><p>{html.escape(n['content'])}</p></article>" for n in notes]
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>" + "<hr/>".join(parts) + "</body></html>\n")
            if progress_cb:
                progress_cb(1, 1, os.path.basename(output_path))
            return [output_path]
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

    # Handle text/markdown to Evernote ENEX export
    if normalized_format(target_format) == "ENEX":
        output_path = os.path.join(output_dir, f"{base}.enex")
        with open(input_path, "r", encoding="utf-8", errors="replace") as f_in:
            body = f_in.read()
        lines = body.splitlines()
        title = base
        if lines and lines[0].startswith("# "):
            title = lines[0][2:].strip()
        export_enex([{"title": title, "content": body}], output_path)
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_path": self.input_path,
            "target_format": self.target_format,
            "output_stem": self.output_stem,
            "status": self.status,
            "error": self.error,
            "output_paths": self.output_paths,
        }


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


def convert_office_doc(input_path: str, output_path: str, target_format: str) -> str:
    # Convert Microsoft Office formats to PDF or structured data.
    import os
    ext = os.path.splitext(input_path)[1].lower()
    tgt = target_format.lower().strip(".")

    if ext == ".docx" and tgt == "pdf":
        try:
            import docx2pdf  # noqa: 22
            docx2pdf.convert(input_path, output_path)
            return output_path
        except Exception:
            from app.features.converter import office_ops  # noqa: 22
            return office_ops.office_to_pdf(input_path, output_path)

    if ext == ".xlsx" and tgt == "csv":
        try:
            import openpyxl  # noqa: 22
            import csv  # noqa: 22
            wb = openpyxl.load_workbook(input_path, data_only=True)
            sheet = wb.active
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for row in sheet.iter_rows(values_only=True):
                    writer.writerow(row)
            return output_path
        except Exception:
            from app.features.converter import office_ops  # noqa: 22
            return office_ops.spreadsheet_to_csv(input_path, output_path)

    if ext in (".xlsx", ".pptx", ".docx") and tgt == "pdf":
        from app.features.converter import office_ops
        return office_ops.office_to_pdf(input_path, output_path)

    raise ValueError(f"Unsupported office conversion from {ext} to {tgt}")


