"""OCR engine for extracting text from images and PDFs, and creating searchable PDFs.

Runs completely locally using PyMuPDF's built-in Tesseract engine with no
external binaries, cloud APIs, or network requests required.
"""

from __future__ import annotations

import io
import os
import sys
from typing import Callable, Sequence
from PIL import Image
import pymupdf


SUPPORTED_LANGUAGES = {
    "eng": "English",
    "spa": "Spanish",
    "fra": "French",
    "deu": "German",
    "ita": "Italian",
    "por": "Portuguese",
    "chi_sim": "Chinese (Simplified)",
    "chi_tra": "Chinese (Traditional)",
    "jpn": "Japanese",
    "kor": "Korean",
    "rus": "Russian",
    "ara": "Arabic",
    "hin": "Hindi",
    "nld": "Dutch",
    "pol": "Polish",
    "tur": "Turkish",
    "ukr": "Ukrainian",
    "vie": "Vietnamese",
}


def get_supported_languages() -> dict[str, str]:
    """Return dictionary of supported OCR language codes and their display names."""
    return dict(SUPPORTED_LANGUAGES)


def discover_tesseract_languages(data_dir: str | None = None) -> list[str]:
    """Discover installed local Tesseract language packs from common tessdata folders."""
    candidates: set[str] = set()
    search_dirs: list[str] = []

    if data_dir:
        search_dirs.append(data_dir)
    env_dir = os.environ.get("TESSDATA_PREFIX")
    if env_dir:
        search_dirs.append(env_dir)
    search_dirs.extend([
        os.path.join(sys.prefix, "share", "tesseract-ocr", "tessdata"),
        os.path.join(sys.prefix, "local", "share", "tesseract-ocr", "tessdata"),
        "/usr/share/tesseract-ocr/4.00/tessdata",
        "/usr/share/tesseract-ocr/5/tessdata",
        "/usr/local/share/tesseract-ocr/tessdata",
    ])

    for dir_path in search_dirs:
        if not dir_path or not os.path.isdir(dir_path):
            continue
        for entry in os.scandir(dir_path):
            if entry.is_file() and entry.name.endswith(".traineddata"):
                code = entry.name[:-len(".traineddata")]
                if code in SUPPORTED_LANGUAGES:
                    candidates.add(code)

    if not candidates:
        return sorted(SUPPORTED_LANGUAGES)
    return sorted(candidates)


def reconstruct_page_layout(words: Sequence[dict] | None) -> dict:
    """Infer logical columns and simple table-like grouping from OCR words."""
    items = list(words or [])
    if not items:
        return {"layout_type": "single_column", "columns": [], "tables": []}

    lines: list[list[dict]] = []
    for word in sorted(items, key=lambda x: (x.get("bbox", [0, 0, 0, 0])[1], x.get("bbox", [0, 0, 0, 0])[0])):
        bbox = word.get("bbox", [0, 0, 0, 0])
        y_center = (bbox[1] + bbox[3]) / 2
        placed = False
        for line in lines:
            prev = line[-1]
            prev_box = prev.get("bbox", [0, 0, 0, 0])
            prev_center = (prev_box[1] + prev_box[3]) / 2
            if abs(y_center - prev_center) <= 12:
                line.append(word)
                placed = True
                break
        if not placed:
            lines.append([word])

    line_text = [" ".join(w.get("text", "") for w in line if w.get("text")) for line in lines]
    x_centers = [((w.get("bbox", [0, 0, 0, 0])[0] + w.get("bbox", [0, 0, 0, 0])[2]) / 2) for w in items if w.get("bbox")]
    if x_centers:
        median_x = sorted(x_centers)[len(x_centers) // 2]
        left_words = [w for w in items if ((w.get("bbox", [0, 0, 0, 0])[0] + w.get("bbox", [0, 0, 0, 0])[2]) / 2) < median_x]
        right_words = [w for w in items if ((w.get("bbox", [0, 0, 0, 0])[0] + w.get("bbox", [0, 0, 0, 0])[2]) / 2) >= median_x]
        columns = []
        if left_words and right_words:
            left_text = " ".join(w.get("text", "") for w in sorted(left_words, key=lambda w: (w.get("bbox", [0, 0, 0, 0])[1], w.get("bbox", [0, 0, 0, 0])[0])) if w.get("text"))
            right_text = " ".join(w.get("text", "") for w in sorted(right_words, key=lambda w: (w.get("bbox", [0, 0, 0, 0])[1], w.get("bbox", [0, 0, 0, 0])[0])) if w.get("text"))
            columns = [{"label": "left", "text": left_text.strip()}, {"label": "right", "text": right_text.strip()}]
    else:
        columns = []

    tables = []
    if len(line_text) >= 3:
        rows = []
        for line in lines:
            row_text = " ".join(w.get("text", "") for w in line if w.get("text"))
            if row_text.strip():
                rows.append(row_text.strip())
        if rows:
            tables.append({"rows": rows[:5], "estimated_columns": max(1, len(rows) // 2)})

    if columns:
        return {"layout_type": "multi_column", "columns": columns, "tables": tables, "text": "\n".join(line_text)}
    return {"layout_type": "single_column", "columns": [], "tables": tables, "text": "\n".join(line_text)}


def _pil_to_pdf_bytes(img: Image.Image) -> bytes:
    """Convert a PIL Image to a single-page PDF bytes stream for PyMuPDF."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    with pymupdf.open(stream=buf.getvalue(), filetype="png") as img_doc:
        return img_doc.convert_to_pdf()


def ocr_image(
    image_input: str | bytes | Image.Image,
    language: str = "eng",
    dpi: int = 200,
) -> dict:
    """Run Tesseract OCR on image path/bytes/PIL Image; return text and metadata."""
    if isinstance(image_input, Image.Image):
        pdf_bytes = _pil_to_pdf_bytes(image_input)
        doc = pymupdf.open("pdf", pdf_bytes)
    elif isinstance(image_input, bytes):
        try:
            with pymupdf.open(stream=image_input) as img_doc:
                pdf_bytes = img_doc.convert_to_pdf()
            doc = pymupdf.open("pdf", pdf_bytes)
        except Exception:
            pil_img = Image.open(io.BytesIO(image_input))
            pdf_bytes = _pil_to_pdf_bytes(pil_img)
            doc = pymupdf.open("pdf", pdf_bytes)
    elif isinstance(image_input, str):
        if not os.path.exists(image_input):
            raise FileNotFoundError(f"Image not found: {image_input}")
        try:
            with pymupdf.open(image_input) as img_doc:
                pdf_bytes = img_doc.convert_to_pdf()
            doc = pymupdf.open("pdf", pdf_bytes)
        except Exception:
            with Image.open(image_input) as pil_img:
                pdf_bytes = _pil_to_pdf_bytes(pil_img)
            doc = pymupdf.open("pdf", pdf_bytes)
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input)}")

    try:
        page = doc[0]
        tp = page.get_textpage_ocr(language=language, dpi=dpi, full=True)
        raw_text = tp.extractText()

        raw_words = tp.extractWORDS()
        words = [
            {
                "bbox": [w[0], w[1], w[2], w[3]],
                "text": w[4],
                "block_no": w[5],
                "line_no": w[6],
                "word_no": w[7],
            }
            for w in raw_words
        ]

        raw_blocks = tp.extractBLOCKS()
        blocks = [
            {
                "bbox": [b[0], b[1], b[2], b[3]],
                "text": b[4].strip() if len(b) > 4 and isinstance(b[4], str) else "",
                "block_no": b[5] if len(b) > 5 else idx,
            }
            for idx, b in enumerate(raw_blocks)
        ]

        return {
            "text": raw_text.strip(),
            "words": words,
            "blocks": blocks,
            "page_count": 1,
            "language": language,
        }
    finally:
        doc.close()


def ocr_pdf(
    pdf_path: str,
    pages: Sequence[int] | None = None,
    language: str = "eng",
    dpi: int = 150,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict:
    """Run OCR on a PDF document across all or selected pages."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    page_texts: list[str] = []
    words_by_page: list[list[dict]] = []
    blocks_by_page: list[list[dict]] = []

    with pymupdf.open(pdf_path) as doc:
        total_pages = len(doc)
        target_indices = [
            i for i in range(total_pages)
            if pages is None or (i + 1) in pages
        ]

        for step, page_idx in enumerate(target_indices):
            if progress_callback:
                progress_callback(step + 1, len(target_indices))

            page = doc[page_idx]
            try:
                tp = page.get_textpage_ocr(language=language, dpi=dpi, full=True)
                page_text = tp.extractText().strip()

                raw_words = tp.extractWORDS()
                page_words = [
                    {
                        "bbox": [w[0], w[1], w[2], w[3]],
                        "text": w[4],
                        "block_no": w[5],
                        "line_no": w[6],
                        "word_no": w[7],
                    }
                    for w in raw_words
                ]

                raw_blocks = tp.extractBLOCKS()
                page_blocks = [
                    {
                        "bbox": [b[0], b[1], b[2], b[3]],
                        "text": b[4].strip() if len(b) > 4 and isinstance(b[4], str) else "",
                        "block_no": b[5] if len(b) > 5 else idx,
                    }
                    for idx, b in enumerate(raw_blocks)
                ]
            except Exception:
                page_text = page.get_text().strip()
                page_words = []
                page_blocks = []

            page_texts.append(page_text)
            words_by_page.append(page_words)
            blocks_by_page.append(page_blocks)

    combined_text = "\n\n--- Page Break ---\n\n".join(
        t for t in page_texts if t
    )

    return {
        "text": combined_text,
        "page_texts": page_texts,
        "words_by_page": words_by_page,
        "blocks_by_page": blocks_by_page,
        "page_count": len(target_indices),
        "language": language,
    }


def ocr_file(
    file_path: str,
    pages: Sequence[int] | None = None,
    language: str = "eng",
    dpi: int = 150,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict:
    """Universal OCR dispatcher for PDFs and any supported image format."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return ocr_pdf(
            file_path,
            pages=pages,
            language=language,
            dpi=dpi,
            progress_callback=progress_callback,
        )
    else:
        res = ocr_image(file_path, language=language, dpi=dpi)
        res["page_texts"] = [res["text"]]
        res["words_by_page"] = [res["words"]]
        res["blocks_by_page"] = [res["blocks"]]
        if progress_callback:
            progress_callback(1, 1)
        return res


def create_searchable_pdf(
    input_path: str,
    output_path: str,
    pages: Sequence[int] | None = None,
    language: str = "eng",
    dpi: int = 150,
    progress_callback: Callable[[int, int], None] | None = None,
) -> str:
    """Create a searchable PDF from a scanned PDF or image with invisible text layer."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    ext = os.path.splitext(input_path)[1].lower()
    out_doc = pymupdf.open()

    try:
        if ext == ".pdf":
            with pymupdf.open(input_path) as src_doc:
                total_pages = len(src_doc)
                target_indices = [
                    i for i in range(total_pages)
                    if pages is None or (i + 1) in pages
                ]

                for step, page_idx in enumerate(target_indices):
                    if progress_callback:
                        progress_callback(step + 1, len(target_indices))

                    src_page = src_doc[page_idx]
                    rect = src_page.rect

                    out_page = out_doc.new_page(width=rect.width, height=rect.height)
                    out_page.show_pdf_page(out_page.rect, src_doc, page_idx)

                    try:
                        tp = src_page.get_textpage_ocr(language=language, dpi=dpi, full=True)
                        words = tp.extractWORDS()

                        if words:
                            shape = out_page.new_shape()
                            for w in words:
                                x0, y0, x1, y1, word_text = w[0], w[1], w[2], w[3], w[4]
                                font_size = max(4.0, (y1 - y0) * 0.9)
                                shape.insert_text(
                                    pymupdf.Point(x0, y1),
                                    word_text,
                                    fontsize=font_size,
                                    render_mode=3,
                                )
                            shape.commit(overlay=True)
                    except Exception:  # noqa: 10 (skip text layer for this page only; export must continue)
                        pass
        else:
            if progress_callback:
                progress_callback(1, 1)

            try:
                with pymupdf.open(input_path) as img_doc:
                    pdf_bytes = img_doc.convert_to_pdf()
            except Exception:
                with Image.open(input_path) as pil_img:
                    pdf_bytes = _pil_to_pdf_bytes(pil_img)

            with pymupdf.open("pdf", pdf_bytes) as temp_pdf:
                src_page = temp_pdf[0]
                rect = src_page.rect

                out_page = out_doc.new_page(width=rect.width, height=rect.height)
                out_page.insert_image(out_page.rect, filename=input_path)

                try:
                    tp = src_page.get_textpage_ocr(language=language, dpi=dpi, full=True)
                    words = tp.extractWORDS()

                    if words:
                        shape = out_page.new_shape()
                        for w in words:
                            x0, y0, x1, y1, word_text = w[0], w[1], w[2], w[3], w[4]
                            font_size = max(4.0, (y1 - y0) * 0.9)
                            shape.insert_text(
                                pymupdf.Point(x0, y1),
                                word_text,
                                fontsize=font_size,
                                render_mode=3,
                            )
                        shape.commit(overlay=True)
                except Exception:  # noqa: 10 (skip text layer for this page only; export must continue)
                    pass

        out_doc.save(output_path, garbage=4, deflate=True)
    finally:
        out_doc.close()

    return output_path


def save_ocr_text(
    ocr_result: dict,
    output_path: str,
    as_markdown: bool = False,
) -> str:
    """Save extracted OCR text to a .txt or .md file."""
    page_texts = ocr_result.get("page_texts", [ocr_result.get("text", "")])

    parts = []
    if as_markdown:
        parts.append("# OCR Extracted Document\n\n")
        for idx, pt in enumerate(page_texts, start=1):
            parts.extend((f"## Page {idx}\n\n", pt, "\n\n---\n\n"))
    else:
        multipage = len(page_texts) > 1
        for idx, pt in enumerate(page_texts, start=1):
            if multipage:
                parts.append(f"=== Page {idx} ===\n\n")
            parts.extend((pt, "\n\n"))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("".join(parts))

    return output_path


def export_ocr_hocr(ocr_result: dict, output_path: str) -> str:
    """Export OCR results to a basic hOCR XML document."""
    word_pages = ocr_result.get("words_by_page") or [ocr_result.get("words", [])]
    hocr_pages = []
    for page_idx, page_words in enumerate(word_pages, start=1):
        page_lines = []
        for group_idx, word in enumerate(page_words):
            bbox = word.get("bbox", [0, 0, 0, 0])
            if len(bbox) != 4:
                continue
            text = word.get("text", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            page_lines.append(
                f'<span class="ocrx_word" id="word_{page_idx}_{group_idx}" title="bbox {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}">{text}</span>'
            )
        hocr_pages.append(
            f'<div class="ocr_page" id="page_{page_idx}" title="bbox 0 0 1000 1000">' + ' '.join(page_lines) + '</div>'
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
        '<html xmlns="http://www.w3.org/1999/xhtml">\n'
        '<body>' + ''.join(hocr_pages) + '</body>\n'
        '</html>\n'
    )
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml)
    return output_path


def export_ocr_alto(ocr_result: dict, output_path: str) -> str:
    """Export OCR results to ALTO XML for downstream document processing tools."""
    word_pages = ocr_result.get("words_by_page") or [ocr_result.get("words", [])]
    page_blocks = []
    for page_idx, page_words in enumerate(word_pages, start=1):
        strings = []
        for word_idx, word in enumerate(page_words):
            bbox = word.get("bbox", [0, 0, 0, 0])
            if len(bbox) != 4:
                continue
            text = word.get("text", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            strings.append(
                f'        <String ID="word_{page_idx}_{word_idx}" CONTENT="{text}" HPOS="{bbox[0]}" VPOS="{bbox[1]}" WIDTH="{max(0, bbox[2] - bbox[0])}" HEIGHT="{max(0, bbox[3] - bbox[1])}" />'
            )
        lines = "\n".join(strings)
        page_blocks.append(
            (
                f'    <Page ID="page_{page_idx}" PHYSICAL_IMG_NR="{page_idx}" WIDTH="1000" HEIGHT="1000">\n'
                '      <PrintSpace>\n'
                '        <TextBlock>\n'
                '          <TextLine>\n'
                f'{lines}\n'
                '          </TextLine>\n'
                '        </TextBlock>\n'
                '      </PrintSpace>\n'
                '    </Page>'
            )
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<alto xmlns="http://www.loc.gov/standards/alto/ns-v4#">\n'
        '  <Layout>\n'
        + '\n'.join(page_blocks) + '\n'
        '  </Layout>\n'
        '</alto>\n'
    )
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml)
    return output_path
