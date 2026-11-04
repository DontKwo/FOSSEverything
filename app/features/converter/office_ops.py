"""Universal Office document engine: extraction and multi-format conversion.

Consolidated engine for DOCX, PPTX, XLSX, ODT, ODS, ODP, DOCM, PPTM, XLSM.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Any

from app.features.markdown.ops import build_styled_markdown_document
from app.features.metadata.ops import get_office_metadata, strip_office_metadata

OFFICE_EXTENSIONS: set[str] = {
    ".docx", ".pptx", ".xlsx", ".odt", ".ods", ".odp", ".docm", ".pptm", ".xlsm"
}

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
NS_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"


def _col_letter_to_index(col_str: str) -> int:
    # Convert Excel column letters (A, B, ..., Z, AA, AB) to 0-based column index.
    idx = 0
    for char in col_str.upper():
        if "A" <= char <= "Z":
            idx = idx * 26 + (ord(char) - ord("A") + 1)
    return max(0, idx - 1)


# Text Extraction

def extract_text_from_office(path: str) -> str:
    # Extract structured text from any supported Office document.
    ext = os.path.splitext(path)[1].lower()
    if ext in (".docx", ".docm"):
        return extract_text_docx(path)
    if ext in (".pptx", ".pptm"):
        return extract_text_pptx(path)
    if ext in (".xlsx", ".xlsm"):
        return extract_text_xlsx(path)
    if ext in (".odt", ".ods", ".odp"):
        return extract_text_opendocument(path)
    raise ValueError(f"Unsupported office format: {ext}")


def extract_text_docx(path: str) -> str:
    # Extract text from DOCX iterating body children to prevent duplicate table text.
    paragraphs: list[str] = []
    with zipfile.ZipFile(path, "r") as archive:
        if "word/document.xml" not in archive.namelist():
            return ""
        root = ET.fromstring(archive.read("word/document.xml"))
        body = next((child for child in root if child.tag.endswith("}body")), root)

        for child in body:
            if child.tag.endswith("}p"):
                texts = [node.text for node in child.iter() if node.tag.endswith("}t") and node.text]
                if texts:
                    paragraph_text = "".join(texts).strip()
                    if paragraph_text:
                        paragraphs.append(paragraph_text)
            elif child.tag.endswith("}tbl"):
                for row_elem in child:
                    if row_elem.tag.endswith("}tr"):
                        row_cells: list[str] = []
                        for cell_elem in row_elem:
                            if cell_elem.tag.endswith("}tc"):
                                cell_texts = [
                                    node.text for node in cell_elem.iter()
                                    if node.tag.endswith("}t") and node.text
                                ]
                                row_cells.append("".join(cell_texts).strip())
                        if row_cells:
                            paragraphs.append(" | ".join(row_cells))

    return "\n\n".join(paragraphs)


def extract_text_pptx(path: str) -> str:
    # Extract text from PPTX slides sorted by integer slide number.
    slides_text: list[str] = []
    with zipfile.ZipFile(path, "r") as archive:
        candidates = [name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")]

        def _slide_num(name: str) -> int:
            match = re.search(r"slide(\d+)\.xml$", name)
            return int(match.group(1)) if match else 9999

        slide_files = sorted(candidates, key=_slide_num)
        for idx, slide_file in enumerate(slide_files, start=1):
            root = ET.fromstring(archive.read(slide_file))
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


def xlsx_to_rows(path: str, sheet_index: int = 0) -> list[list[str]]:
    # Parse XLSX sheet into aligned row cells, resolving shared and inline strings.
    with zipfile.ZipFile(path, "r") as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            sst_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for si in sst_root.iter():
                if si.tag.endswith("}si"):
                    t_nodes = [node.text for node in si.iter() if node.tag.endswith("}t") and node.text]
                    shared_strings.append("".join(t_nodes))

        candidates = [name for name in archive.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")]

        def _sheet_num(name: str) -> int:
            match = re.search(r"sheet(\d+)\.xml$", name)
            return int(match.group(1)) if match else 9999

        sheet_files = sorted(candidates, key=_sheet_num)
        if not sheet_files or sheet_index >= len(sheet_files):
            raise ValueError(f"No worksheet found at index {sheet_index} in XLSX file.")

        sheet_root = ET.fromstring(archive.read(sheet_files[sheet_index]))
        rows: list[list[str]] = []

        for row in sheet_root.iter():
            if row.tag.endswith("}row"):
                cell_dict: dict[int, str] = {}
                max_col = -1
                for cell in row:
                    if cell.tag.endswith("}c"):
                        cell_ref = cell.get("r", "")
                        match = re.match(r"^([A-Za-z]+)", cell_ref)
                        col_idx = _col_letter_to_index(match.group(1)) if match else max_col + 1
                        max_col = max(max_col, col_idx)

                        cell_type = cell.get("t")
                        cell_value = ""
                        if cell_type == "inlineStr":
                            inline_texts = [node.text for node in cell.iter() if node.tag.endswith("}t") and node.text]
                            cell_value = "".join(inline_texts)
                        else:
                            v_elem = next((child for child in cell if child.tag.endswith("}v")), None)
                            if v_elem is not None and v_elem.text:
                                raw_text = v_elem.text
                                if cell_type == "s" and raw_text.isdigit():
                                    str_index = int(raw_text)
                                    cell_value = shared_strings[str_index] if 0 <= str_index < len(shared_strings) else raw_text
                                else:
                                    cell_value = raw_text
                        cell_dict[col_idx] = cell_value

                if cell_dict:
                    row_cells = [cell_dict.get(column_idx, "") for column_idx in range(max_col + 1)]
                    if any(row_cells):
                        rows.append(row_cells)

        return rows


def ods_to_rows(path: str, sheet_index: int = 0) -> list[list[str]]:
    # Parse ODS content.xml table rows into aligned 2D string matrix.
    with zipfile.ZipFile(path, "r") as archive:
        if "content.xml" not in archive.namelist():
            return []
        root = ET.fromstring(archive.read("content.xml"))
        tables = [elem for elem in root.iter() if elem.tag.endswith("}table")]
        if not tables or sheet_index >= len(tables):
            return []

        target_table = tables[sheet_index]
        rows: list[list[str]] = []

        for row_elem in target_table.iter():
            if row_elem.tag.endswith("}table-row"):
                row_vals: list[str] = []
                for cell_elem in row_elem:
                    if cell_elem.tag.endswith("}table-cell"):
                        cell_text = "".join(cell_elem.itertext()).strip()
                        repeat_attr = cell_elem.get(f"{{{NS_TABLE}}}number-columns-repeated") or cell_elem.get("number-columns-repeated")
                        repeat_count = int(repeat_attr) if repeat_attr and repeat_attr.isdigit() else 1
                        repeat_count = min(repeat_count, 100)
                        for _ in range(repeat_count):
                            row_vals.append(cell_text)
                while row_vals and not row_vals[-1]:
                    row_vals.pop()
                if any(row_vals):
                    rows.append(row_vals)

        return rows


def extract_text_xlsx(path: str) -> str:
    # Extract spreadsheet cell text across all worksheets in XLSX workbook.
    sheets_text: list[str] = []
    with zipfile.ZipFile(path, "r") as archive:
        candidates = [name for name in archive.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")]

        def _sheet_num(name: str) -> int:
            match = re.search(r"sheet(\d+)\.xml$", name)
            return int(match.group(1)) if match else 9999

        for idx, _ in enumerate(sorted(candidates, key=_sheet_num)):
            rows = xlsx_to_rows(path, sheet_index=idx)
            if rows:
                lines = [f"=== Sheet {idx + 1} ==="]
                for row in rows:
                    lines.append("\t".join(row))
                sheets_text.append("\n".join(lines))

    return "\n\n".join(sheets_text)


def extract_text_opendocument(path: str) -> str:
    # Extract text from ODT, ODS, or ODP OpenDocument format.
    ext = os.path.splitext(path)[1].lower()
    if ext == ".ods":
        rows = ods_to_rows(path, sheet_index=0)
        return "\n".join("\t".join(r) for r in rows)

    with zipfile.ZipFile(path, "r") as archive:
        if "content.xml" not in archive.namelist():
            return ""
        root = ET.fromstring(archive.read("content.xml"))
        lines: list[str] = []
        for elem in root.iter():
            if elem.tag.endswith("}p") or elem.tag.endswith("}h"):
                text = "".join(elem.itertext()).strip()
                if text:
                    lines.append(text)
        return "\n\n".join(lines)


# Format Conversions

def docx_to_markdown(path: str) -> str:
    # Convert DOCX paragraphs, headings, and tables to formatted Markdown.
    paragraphs: list[str] = []
    with zipfile.ZipFile(path, "r") as archive:
        if "word/document.xml" not in archive.namelist():
            return ""
        root = ET.fromstring(archive.read("word/document.xml"))
        body = next((child for child in root if child.tag.endswith("}body")), root)

        for child in body:
            if child.tag.endswith("}p"):
                style_node = child.find(f".//{{{NS_W}}}pStyle")
                style_val = style_node.attrib.get(f"{{{NS_W}}}val", "") if style_node is not None else ""
                texts = [node.text for node in child.iter() if node.tag.endswith("}t") and node.text]
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
            elif child.tag.endswith("}tbl"):
                rows: list[list[str]] = []
                for tr in child:
                    if tr.tag.endswith("}tr"):
                        cells: list[str] = []
                        for tc in tr:
                            if tc.tag.endswith("}tc"):
                                cell_texts = [n.text for n in tc.iter() if n.tag.endswith("}t") and n.text]
                                cells.append("".join(cell_texts).strip())
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


def odt_to_markdown(path: str) -> str:
    # Convert ODT document paragraphs and headings to Markdown.
    with zipfile.ZipFile(path, "r") as archive:
        if "content.xml" not in archive.namelist():
            return ""
        root = ET.fromstring(archive.read("content.xml"))
        paragraphs: list[str] = []
        for elem in root.iter():
            if elem.tag.endswith("}h"):
                level_str = elem.get(f"{{{NS_TEXT}}}outline-level") or "1"
                level = int(level_str) if level_str.isdigit() else 1
                text = "".join(elem.itertext()).strip()
                if text:
                    paragraphs.append(f"{'#' * min(6, level)} {text}")
            elif elem.tag.endswith("}p"):
                text = "".join(elem.itertext()).strip()
                if text:
                    paragraphs.append(text)
        return "\n\n".join(paragraphs)


def pptx_to_markdown(input_path: str) -> str:
    # Convert PPTX presentation slides to Markdown with slide headers.
    slides_md: list[str] = []
    with zipfile.ZipFile(input_path, "r") as archive:
        candidates = [name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")]

        def _slide_num(name: str) -> int:
            match = re.search(r"slide(\d+)\.xml$", name)
            return int(match.group(1)) if match else 9999

        for idx, slide_file in enumerate(sorted(candidates, key=_slide_num), start=1):
            root = ET.fromstring(archive.read(slide_file))
            slide_lines = [f"## Slide {idx}"]
            for elem in root.iter():
                if elem.tag.endswith("}p"):
                    texts = [node.text for node in elem.iter() if node.tag.endswith("}t") and node.text]
                    if texts:
                        line = "".join(texts).strip()
                        if line:
                            slide_lines.append(f"- {line}")
            if len(slide_lines) > 1:
                slides_md.append("\n".join(slide_lines))

    return "\n\n".join(slides_md)


def odp_to_markdown(path: str) -> str:
    # Convert ODP presentation slides to Markdown headers and bullets.
    with zipfile.ZipFile(path, "r") as archive:
        if "content.xml" not in archive.namelist():
            return ""
        root = ET.fromstring(archive.read("content.xml"))
        pages = [elem for elem in root.iter() if elem.tag.endswith("}page")]
        slides_md: list[str] = []
        for idx, page in enumerate(pages, start=1):
            lines = [f"## Slide {idx}"]
            for p in page.iter():
                if p.tag.endswith("}p"):
                    t = "".join(p.itertext()).strip()
                    if t:
                        lines.append(f"- {t}")
            if len(lines) > 1:
                slides_md.append("\n".join(lines))
        return "\n\n".join(slides_md)


def spreadsheet_to_csv(input_path: str, output_path: str, sheet_index: int = 0) -> str:
    # Convert XLSX or ODS spreadsheet sheet to standard CSV.
    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".ods":
        rows = ods_to_rows(input_path, sheet_index=sheet_index)
    else:
        rows = xlsx_to_rows(input_path, sheet_index=sheet_index)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerows(rows)
    return output_path


def spreadsheet_to_json(input_path: str, output_path: str) -> str:
    # Convert spreadsheet to structured JSON keyed by first row headers.
    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".ods":
        rows = ods_to_rows(input_path, sheet_index=0)
    else:
        rows = xlsx_to_rows(input_path, sheet_index=0)

    records: list[dict[str, str]] = []
    if len(rows) > 1:
        headers = [h or f"col_{i + 1}" for i, h in enumerate(rows[0])]
        for row in rows[1:]:
            record = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            records.append(record)
    elif rows:
        records = [{"value": item_text} for item_text in rows[0]]

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2)
    return output_path


def office_to_pdf(input_path: str, output_path: str) -> str:
    # Convert Office document (DOCX, ODT, PPTX, ODP, XLSX, ODS) to styled PDF.
    import pymupdf

    ext = os.path.splitext(input_path)[1].lower()
    if ext in (".docx", ".docm"):
        md_text = docx_to_markdown(input_path)
    elif ext == ".odt":
        md_text = odt_to_markdown(input_path)
    elif ext in (".pptx", ".pptm"):
        md_text = pptx_to_markdown(input_path)
    elif ext == ".odp":
        md_text = odp_to_markdown(input_path)
    elif ext in (".xlsx", ".xlsm", ".ods"):
        rows = ods_to_rows(input_path) if ext == ".ods" else xlsx_to_rows(input_path)
        if rows:
            max_c = max(len(r) for r in rows)
            norm = [r + [""] * (max_c - len(r)) for r in rows]
            tbl = ["| " + " | ".join(norm[0]) + " |", "| " + " | ".join(["---"] * max_c) + " |"]
            for r in norm[1:]:
                tbl.append("| " + " | ".join(r) + " |")
            md_text = "\n".join(tbl)
        else:
            md_text = "Empty spreadsheet"
    else:
        md_text = extract_text_from_office(input_path)

    if not md_text.strip():
        md_text = "Empty document"

    html_content = build_styled_markdown_document(md_text, flavor="github", theme_mode="light", for_pdf=True)
    story = pymupdf.Story(html=html_content)
    writer = pymupdf.DocumentWriter(output_path)
    mediabox = pymupdf.paper_rect("letter")
    where = mediabox + (36, 36, -36, -36)
    more = 1
    while more:
        device = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(device)
        writer.end_page()
    writer.close()
    return output_path


def docx_to_pdf(input_path: str, output_path: str) -> str:
    # Convert DOCX document directly to PDF format.
    return office_to_pdf(input_path, output_path)


def xlsx_to_csv(input_path: str, output_path: str, sheet_index: int = 0) -> str:
    # Convert XLSX worksheet directly to CSV format.
    return spreadsheet_to_csv(input_path, output_path, sheet_index=sheet_index)
