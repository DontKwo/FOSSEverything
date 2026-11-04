"""OCR engine for extracting text from images and PDFs, and creating searchable PDFs.

Runs completely locally using PyMuPDF's built-in Tesseract engine with no
external binaries, cloud APIs, or network requests required.
"""

from __future__ import annotations

import io
import logging
import os
import sys
from typing import Callable, Sequence
from PIL import Image
import pymupdf

logger = logging.getLogger(__name__)


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



def parse_page_selection(spec: str | None, total_pages: int) -> list[int]:
    # Parse 1-indexed page selection string into ordered, deduplicated page indices.
    if total_pages <= 0:
        return []
    if spec is None or spec.strip().lower() in ("", "all", "*"):
        return list(range(1, total_pages + 1))

    tokens = [t.strip() for t in spec.split(",") if t.strip()]
    if not tokens:
        return list(range(1, total_pages + 1))

    selected: list[int] = []
    for token in tokens:
        if "-" in token:
            parts = token.split("-", 1)
            try:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
            except ValueError:
                raise ValueError(f"Invalid page range token: '{token}'")
            if start < 1 or end > total_pages or start > end:
                raise ValueError(f"Page range '{token}' out of bounds (1-{total_pages})")
            selected.extend(range(start, end + 1))
        else:
            try:
                page_num = int(token)
            except ValueError:
                raise ValueError(f"Invalid page number token: '{token}'")
            if page_num < 1 or page_num > total_pages:
                raise ValueError(f"Page number {page_num} out of bounds (1-{total_pages})")
            selected.append(page_num)

    return list(dict.fromkeys(selected))


def inspect_pdf_searchable_status(pdf_path: str, min_chars: int = 15) -> dict[str, Any]:
    # Inspect PDF pages for existing native text blocks vs uncovered raster images.
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    searchable_pages: list[int] = []
    hybrid_pages: list[int] = []
    scanned_pages: list[int] = []

    with pymupdf.open(pdf_path) as doc:
        total = len(doc)
        for idx in range(total):
            page_num = idx + 1
            page = doc[idx]

            text_blocks = [
                pymupdf.Rect(b[:4]) for b in page.get_text("blocks")
                if b[6] == 0 and len(str(b[4]).strip()) > 0
            ]
            char_count = sum(len(str(b[4]).strip()) for b in page.get_text("blocks") if b[6] == 0)

            image_infos = page.get_image_info()
            image_rects = [
                pymupdf.Rect(info["bbox"]) for info in image_infos
                if (info["bbox"][2] - info["bbox"][0]) >= 24 and (info["bbox"][3] - info["bbox"][1]) >= 24
            ]

            if char_count >= min_chars and not image_rects:
                searchable_pages.append(page_num)
            elif char_count >= min_chars and image_rects:
                uncovered = False
                for img_rect in image_rects:
                    img_area = img_rect.width * img_rect.height
                    if img_area <= 0:
                        continue
                    covered_area = sum((img_rect & tb).width * (img_rect & tb).height for tb in text_blocks if bool(img_rect & tb))
                    if (covered_area / img_area) < 0.20:
                        uncovered = True
                        break
                if uncovered:
                    hybrid_pages.append(page_num)
                else:
                    searchable_pages.append(page_num)
            else:
                scanned_pages.append(page_num)

    return {
        "page_count": total,
        "searchable_pages": searchable_pages,
        "hybrid_pages": hybrid_pages,
        "scanned_pages": scanned_pages,
        "is_fully_searchable": len(scanned_pages) == 0 and len(hybrid_pages) == 0,
    }


def expand_ocr_inputs(paths: Sequence[str], recursive: bool = True) -> list[str]:
    # Expand mix of files and directories into sorted list of OCR-supported file paths.
    supported_exts = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp"}
    collected: list[str] = []

    for item in paths:
        if os.path.isfile(item):
            if os.path.splitext(item)[1].lower() in supported_exts:
                collected.append(os.path.abspath(item))
        elif os.path.isdir(item):
            if recursive:
                for root, _, files in os.walk(item):
                    for file_name in files:
                        if os.path.splitext(file_name)[1].lower() in supported_exts:
                            collected.append(os.path.abspath(os.path.join(root, file_name)))
            else:
                for entry in os.scandir(item):
                    if entry.is_file() and os.path.splitext(entry.name)[1].lower() in supported_exts:
                        collected.append(os.path.abspath(entry.path))

    return sorted(dict.fromkeys(collected))


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
    force_overwrite: bool = False,
) -> dict:
    """Run OCR on a PDF document across all or selected pages."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    page_texts: list[str] = []
    words_by_page: list[list[dict]] = []
    blocks_by_page: list[list[dict]] = []

    with pymupdf.open(pdf_path) as doc:
        total_pages = len(doc)
        target_indices = [target_idx for target_idx in range(total_pages) if pages is None or (target_idx + 1) in pages]

        skipped_searchable: list[int] = []
        hybrid_processed: list[int] = []
        ocr_processed: list[int] = []

        for step, page_idx in enumerate(target_indices):
            if progress_callback:
                progress_callback(step + 1, len(target_indices))

            page = doc[page_idx]
            page_num = page_idx + 1
            existing_text = page.get_text().strip()
            images_on_page = [
                info for info in page.get_image_info()
                if (info["bbox"][2] - info["bbox"][0]) >= 24 and (info["bbox"][3] - info["bbox"][1]) >= 24
            ]

            if not force_overwrite and len(existing_text) >= 15 and not images_on_page:
                page_text = existing_text
                page_words = []
                page_blocks = []
                skipped_searchable.append(page_num)
            else:
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
                            "block_no": b[5] if len(b) > 5 else block_idx,
                        }
                        for block_idx, b in enumerate(raw_blocks)
                    ]
                    if len(existing_text) >= 15 and images_on_page:
                        hybrid_processed.append(page_num)
                    else:
                        ocr_processed.append(page_num)
                except Exception:
                    page_text = existing_text
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
        "skipped_searchable_pages": skipped_searchable,
        "hybrid_pages": hybrid_processed,
        "ocr_pages": ocr_processed,
    }


def ocr_file(
    file_path: str,
    pages: Sequence[int] | None = None,
    language: str = "eng",
    dpi: int = 150,
    progress_callback: Callable[[int, int], None] | None = None,
    force_overwrite: bool = False,
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
            force_overwrite=force_overwrite,
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
    pages: str | Sequence[int] | None = None,
    language: str = "eng",
    dpi: int = 150,
    progress_callback: Callable[[int, int], None] | None = None,
    force_overwrite: bool = False,
    force_reocr: bool = False,
) -> str:
    # Create searchable PDF preserving existing vector text layers unless forced.
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    ext = os.path.splitext(input_path)[1].lower()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    is_forced = bool(force_reocr or force_overwrite)

    if ext == ".pdf":
        doc = pymupdf.open(input_path)
        total_pages = len(doc)
        if isinstance(pages, str):
            selected_pages = set(parse_page_selection(pages, total_pages))
        elif pages is not None:
            selected_pages = set(pages)
        else:
            selected_pages = set(range(1, total_pages + 1))

        target_indices = [idx for idx in range(total_pages) if (idx + 1) in selected_pages]

        for step, page_idx in enumerate(target_indices):
            if progress_callback:
                progress_callback(step + 1, len(target_indices))

            page = doc[page_idx]
            existing_text = page.get_text().strip()

            if len(existing_text) >= 15 and not is_forced:
                continue

            try:
                tp = page.get_textpage_ocr(language=language, dpi=dpi, full=True)
                words = tp.extractWORDS()
                if words:
                    shape = page.new_shape()
                    for word_tuple in words:
                        x0, y0, x1, y1, word_text = word_tuple[0], word_tuple[1], word_tuple[2], word_tuple[3], word_tuple[4]
                        font_size = max(4.0, (y1 - y0) * 0.9)
                        shape.insert_text(
                            pymupdf.Point(x0, y1),
                            word_text,
                            fontsize=font_size,
                            render_mode=3,
                        )
                    shape.commit(overlay=True)
            except Exception as exc:
                logger.debug("Failed OCR text overlay on page %d: %s", page_idx + 1, exc)

        doc.save(output_path, garbage=3, deflate=True)
        doc.close()
        return output_path

    # Image input: create single page PDF with image and invisible text layer
    img_doc = pymupdf.open()
    try:
        pix = pymupdf.Pixmap(input_path)
        page = img_doc.new_page(width=pix.width, height=pix.height)
        page.insert_image(page.rect, filename=input_path)
        try:
            tp = page.get_textpage_ocr(language=language, dpi=dpi, full=True)
            words = tp.extractWORDS()
            if words:
                shape = page.new_shape()
                for word_tuple in words:
                    x0, y0, x1, y1, word_text = word_tuple[0], word_tuple[1], word_tuple[2], word_tuple[3], word_tuple[4]
                    font_size = max(4.0, (y1 - y0) * 0.9)
                    shape.insert_text(
                        pymupdf.Point(x0, y1),
                        word_text,
                        fontsize=font_size,
                        render_mode=3,
                    )
                shape.commit(overlay=True)
        except Exception as exc:
            logger.debug("Failed image OCR text overlay: %s", exc)

        img_doc.save(output_path, garbage=3, deflate=True)
        return output_path
    finally:
        img_doc.close()


def save_ocr_text(
    ocr_result: dict | str,
    output_path: str,
    as_markdown: bool = False,
) -> str:
    # Save extracted OCR text to plain text or Markdown format.
    if isinstance(ocr_result, str):
        page_texts = [ocr_result]
    else:
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
