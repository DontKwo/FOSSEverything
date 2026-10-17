"""Universal Office document engine: text extraction, metadata reading/stripping, and conversions.

Zero external dependencies beyond standard library (zipfile, xml.etree.ElementTree) and PyMuPDF.
Supports: .docx, .pptx, .xlsx, .odt, .ods, .odp
"""
from __future__ import annotations

import os
import io
import csv
import json
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime

OFFICE_EXTENSIONS = {".docx", ".pptx", ".xlsx", ".odt", ".ods", ".odp", ".docm", ".pptm", ".xlsm"}

# OpenXML XML Namespaces
NS_CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
NS_DC = "http://purl.org/dc/elements/1.1/"
NS_DCTERMS = "http://purl.org/dc/terms/"
NS_EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


# ─── Text Extraction ─────────────────────────────────────────────────────────
def extract_text_from_office(path: str) -> str:
    """Extract full structured text from any supported Office document."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".docx", ".docm"):
        return extract_text_docx(path)
    elif ext in (".pptx", ".pptm"):
        return extract_text_pptx(path)
    elif ext in (".xlsx", ".xlsm"):
        return extract_text_xlsx(path)
    elif ext in (".odt", ".ods", ".odp"):
        return extract_text_opendocument(path)
    else:
        raise ValueError(f"Unsupported office format: {ext}")


def extract_text_docx(path: str) -> str:
    """Extract text paragraphs, headings, and tables from a DOCX document."""
    paragraphs = []
    with zipfile.ZipFile(path, "r") as z:
        if "word/document.xml" not in z.namelist():
            return ""
        xml_bytes = z.read("word/document.xml")
        root = ET.fromstring(xml_bytes)

        for elem in root.iter():
            if elem.tag.endswith("}p"):
                texts = [node.text for node in elem.iter() if node.tag.endswith("}t") and node.text]
                if texts:
                    p_text = "".join(texts).strip()
                    if p_text:
                        paragraphs.append(p_text)
            elif elem.tag.endswith("}tr"):
                row_cells = []
                for cell in elem.iter():
                    if cell.tag.endswith("}tc"):
                        cell_texts = [node.text for node in cell.iter() if node.tag.endswith("}t") and node.text]
                        row_cells.append("".join(cell_texts).strip())
                if row_cells:
                    paragraphs.append(" | ".join(row_cells))

    return "\n\n".join(paragraphs)


def extract_text_pptx(path: str) -> str:
    """Extract text from PPTX slides with slide headers."""
    slides_text = []
    with zipfile.ZipFile(path, "r") as z:
        slide_files = sorted([f for f in z.namelist() if f.startswith("ppt/slides/slide") and f.endswith(".xml")])
        for idx, slide_file in enumerate(slide_files, start=1):
            root = ET.fromstring(z.read(slide_file))
            slide_lines = [f"=== Slide {idx} ==="]
            for elem in root.iter():
                if elem.tag.endswith("}p"):
                    texts = [node.text for node in elem.iter() if node.tag.endswith("}t") and node.text]
                    if texts:
                        line = "".join(texts).strip()
                        if line:
                            slide_lines.append(line)
            if len(slide_lines) > 1:
                slides_text.append("\n".join(slide_lines))

    return "\n\n".join(slides_text)


def extract_text_xlsx(path: str) -> str:
    """Extract cell values and shared strings from XLSX workbook sheets."""
    sheet_data = []
    with zipfile.ZipFile(path, "r") as z:
        shared_strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            sst_root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in sst_root.iter():
                if si.tag.endswith("}si"):
                    t_nodes = [node.text for node in si.iter() if node.tag.endswith("}t") and node.text]
                    shared_strings.append("".join(t_nodes))

        sheet_files = sorted([f for f in z.namelist() if f.startswith("xl/worksheets/sheet") and f.endswith(".xml")])
        for idx, sheet_file in enumerate(sheet_files, start=1):
            sheet_root = ET.fromstring(z.read(sheet_file))
            sheet_lines = [f"=== Sheet {idx} ==="]
            for row in sheet_root.iter():
                if row.tag.endswith("}row"):
                    row_vals = []
                    for c in row.iter():
                        if c.tag.endswith("}c"):
                            cell_type = c.get("t")
                            v_elem = next((child for child in c if child.tag.endswith("}v")), None)
                            if v_elem is not None and v_elem.text:
                                val = v_elem.text
                                if cell_type == "s" and val.isdigit():
                                    s_idx = int(val)
                                    if 0 <= s_idx < len(shared_strings):
                                        val = shared_strings[s_idx]
                                row_vals.append(val)
                    if row_vals:
                        sheet_lines.append("\t".join(row_vals))
            if len(sheet_lines) > 1:
                sheet_data.append("\n".join(sheet_lines))

    return "\n\n".join(sheet_data)


def extract_text_opendocument(path: str) -> str:
    """Extract text from OpenDocument format (ODT, ODS, ODP) content.xml."""
    with zipfile.ZipFile(path, "r") as z:
        if "content.xml" not in z.namelist():
            return ""
        root = ET.fromstring(z.read("content.xml"))
        lines = []
        for elem in root.iter():
            if elem.tag.endswith("}p") or elem.tag.endswith("}h"):
                text = "".join(elem.itertext()).strip()
                if text:
                    lines.append(text)
        return "\n\n".join(lines)


# ─── Metadata Inspector & Stripping ──────────────────────────────────────────
def get_office_metadata(path: str) -> dict[str, str]:
    """Read metadata properties from an Office document (DOCX, PPTX, XLSX)."""
    meta = {}
    if not os.path.exists(path):
        return meta

    ext = os.path.splitext(path)[1].lower()
    if ext not in OFFICE_EXTENSIONS:
        return meta

    try:
        with zipfile.ZipFile(path, "r") as z:
            names = z.namelist()
            if "docProps/core.xml" in names:
                root = ET.fromstring(z.read("docProps/core.xml"))
                for elem in root:
                    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    text = elem.text
                    if text:
                        if tag == "title":
                            meta["Title"] = text
                        elif tag == "creator":
                            meta["Author / Creator"] = text
                        elif tag == "subject":
                            meta["Subject"] = text
                        elif tag == "description":
                            meta["Description"] = text
                        elif tag == "keywords":
                            meta["Keywords"] = text
                        elif tag == "lastModifiedBy":
                            meta["Last Modified By"] = text
                        elif tag == "revision":
                            meta["Revision"] = text
                        elif tag == "created":
                            meta["Created Date"] = text
                        elif tag == "modified":
                            meta["Modified Date"] = text

            if "docProps/app.xml" in names:
                root = ET.fromstring(z.read("docProps/app.xml"))
                for elem in root:
                    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    text = elem.text
                    if text:
                        if tag == "Application":
                            meta["Application"] = text
                        elif tag == "Company":
                            meta["Company"] = text
                        elif tag == "Pages":
                            meta["Pages"] = text
                        elif tag == "Words":
                            meta["Words"] = text
                        elif tag == "Characters":
                            meta["Characters"] = text
                        elif tag == "TotalTime":
                            meta["Total Edit Time (mins)"] = text

            if "meta.xml" in names:
                root = ET.fromstring(z.read("meta.xml"))
                for elem in root.iter():
                    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    if elem.text and elem.text.strip():
                        if tag in ("title", "creator", "date", "editing-duration", "generator"):
                            meta[tag.capitalize()] = elem.text.strip()
    except Exception as exc:
        raise RuntimeError(f"Could not read office metadata: {exc}") from exc

    return meta


def strip_office_metadata(input_path: str, output_path: str) -> str:
    """Create a copy of the Office document with all metadata and author information cleanly stripped."""
    with zipfile.ZipFile(input_path, "r") as zin:
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                filename = item.filename
                if filename == "docProps/core.xml":
                    blank_core = (
                        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                        f'<cp:coreProperties xmlns:cp="{NS_CP}" xmlns:dc="{NS_DC}" xmlns:dcterms="{NS_DCTERMS}">\n'
                        '    <dc:title></dc:title>\n'
                        '    <dc:creator></dc:creator>\n'
                        '    <cp:lastModifiedBy></cp:lastModifiedBy>\n'
                        '    <cp:revision>1</cp:revision>\n'
                        '</cp:coreProperties>'
                    )
                    zout.writestr(item, blank_core.encode("utf-8"))
                elif filename == "docProps/app.xml":
                    blank_app = (
                        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                        f'<Properties xmlns="{NS_EP}">\n'
                        '    <Application>FOSSEverything</Application>\n'
                        '    <Company></Company>\n'
                        '</Properties>'
                    )
                    zout.writestr(item, blank_app.encode("utf-8"))
                elif filename == "meta.xml":
                    blank_meta = '<?xml version="1.0" encoding="UTF-8"?><office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"/>'
                    zout.writestr(item, blank_meta.encode("utf-8"))
                else:
                    zout.writestr(item, zin.read(filename))

    return output_path


# ─── Conversions ─────────────────────────────────────────────────────────────
def docx_to_markdown(path: str) -> str:
    """Convert DOCX paragraphs and tables to clean Markdown."""
    paragraphs = []
    with zipfile.ZipFile(path, "r") as z:
        if "word/document.xml" not in z.namelist():
            return ""
        root = ET.fromstring(z.read("word/document.xml"))

        for elem in root.iter():
            if elem.tag.endswith("}p"):
                style_node = elem.find(".//w:pStyle", {"w": NS_W}) if hasattr(elem, "find") else None
                style_val = style_node.attrib.get(f"{{{NS_W}}}val", "") if style_node is not None else ""
                texts = [node.text for node in elem.iter() if node.tag.endswith("}t") and node.text]
                p_text = "".join(texts).strip()
                if p_text:
                    if "Heading1" in style_val or style_val == "1":
                        paragraphs.append(f"# {p_text}")
                    elif "Heading2" in style_val or style_val == "2":
                        paragraphs.append(f"## {p_text}")
                    elif "Heading3" in style_val or style_val == "3":
                        paragraphs.append(f"### {p_text}")
                    else:
                        paragraphs.append(p_text)
            elif elem.tag.endswith("}tbl"):
                rows = []
                for tr in elem.iter():
                    if tr.tag.endswith("}tr"):
                        cells = []
                        for tc in tr.iter():
                            if tc.tag.endswith("}tc"):
                                c_txt = "".join(n.text for n in tc.iter() if n.tag.endswith("}t") and n.text).strip()
                                cells.append(c_txt)
                        if cells:
                            rows.append(cells)
                if rows:
                    max_cols = max(len(r) for r in rows)
                    norm_rows = [r + [""] * (max_cols - len(r)) for r in rows]
                    header = "| " + " | ".join(norm_rows[0]) + " |"
                    divider = "| " + " | ".join(["---"] * max_cols) + " |"
                    tbl_lines = [header, divider]
                    for r in norm_rows[1:]:
                        tbl_lines.append("| " + " | ".join(r) + " |")
                    paragraphs.append("\n".join(tbl_lines))

    return "\n\n".join(paragraphs)


def docx_to_pdf(input_path: str, output_path: str) -> str:
    """Convert DOCX document to formatted PDF using PyMuPDF."""
    import pymupdf  # noqa: 13 (deferred: only needed for PDF export)
    md_text = docx_to_markdown(input_path)
    if not md_text.strip():
        md_text = extract_text_docx(input_path)

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4

    margin = 54
    y = margin
    line_height = 14

    for paragraph in md_text.split("\n\n"):
        p = paragraph.strip()
        if not p:
            continue

        fontsize = 10
        fontname = "helv"

        if p.startswith("# "):
            fontsize = 18
            fontname = "hebo"
            p = p[2:]
            line_height = 24
            y += 8
        elif p.startswith("## "):
            fontsize = 14
            fontname = "hebo"
            p = p[3:]
            line_height = 18
            y += 6
        elif p.startswith("### "):
            fontsize = 12
            fontname = "hebo"
            p = p[4:]
            line_height = 16
            y += 4
        else:
            line_height = 14

        max_chars = max(20, int((595 - 2 * margin) / (fontsize * 0.52)))
        words = p.split()
        current_line = []

        for word in words:
            if len(" ".join(current_line + [word])) <= max_chars:
                current_line.append(word)
            else:
                if y > 842 - margin:
                    page = doc.new_page(width=595, height=842)
                    y = margin
                page.insert_text(pymupdf.Point(margin, y), " ".join(current_line), fontname=fontname, fontsize=fontsize)
                y += line_height
                current_line = [word]

        if current_line:
            if y > 842 - margin:
                page = doc.new_page(width=595, height=842)
                y = margin
            page.insert_text(pymupdf.Point(margin, y), " ".join(current_line), fontname=fontname, fontsize=fontsize)
            y += line_height + 6

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return output_path


def xlsx_to_csv(input_path: str, output_path: str, sheet_index: int = 0) -> str:
    """Convert XLSX worksheet to standard CSV."""
    with zipfile.ZipFile(input_path, "r") as z:
        shared_strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            sst_root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in sst_root.iter():
                if si.tag.endswith("}si"):
                    t_nodes = [node.text for node in si.iter() if node.tag.endswith("}t") and node.text]
                    shared_strings.append("".join(t_nodes))

        sheet_files = sorted([f for f in z.namelist() if f.startswith("xl/worksheets/sheet") and f.endswith(".xml")])
        if not sheet_files or sheet_index >= len(sheet_files):
            raise ValueError("No worksheet found in XLSX file.")

        sheet_root = ET.fromstring(z.read(sheet_files[sheet_index]))
        rows = []
        for row in sheet_root.iter():
            if row.tag.endswith("}row"):
                row_vals = []
                for c in row.iter():
                    if c.tag.endswith("}c"):
                        cell_type = c.get("t")
                        v_elem = next((child for child in c if child.tag.endswith("}v")), None)
                        val = ""
                        if v_elem is not None and v_elem.text:
                            val = v_elem.text
                            if cell_type == "s" and val.isdigit():
                                s_idx = int(val)
                                if 0 <= s_idx < len(shared_strings):
                                    val = shared_strings[s_idx]
                        row_vals.append(val)
                if any(row_vals):
                    rows.append(row_vals)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

    return output_path


def pptx_to_markdown(input_path: str) -> str:
    """Convert PPTX presentation slides to clean Markdown."""
    return extract_text_pptx(input_path)
