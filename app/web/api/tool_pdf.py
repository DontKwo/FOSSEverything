import base64
from pathlib import Path
from typing import Any

import pymupdf

from app.features.ocr.ops import (
    create_searchable_pdf,
    get_supported_languages,
    ocr_pdf,
    save_ocr_text,
)
from app.features.pdf.ops import (
    BatchPdfItem,
    PAGE_IMAGE_FORMATS,
    add_page_numbers,
    add_pdf_watermark,
    bake_annotations,
    batch_add_image_watermark,
    batch_add_pdf_watermark,
    batch_compress_pdfs,
    batch_protect_pdfs,
    break_pdf_into_pages,
    compress_pdf,
    convert_scanned_pdf_to_docx,
    export_pdf_pages,
    merge_pdfs,
    open_pdf,
    page_count,
    pdf_needs_ocr,
    protect_pdf,
    render_page,
    reorganize_pdf_pages,
    save_annotated_pdf,
    save_pdf_text,
    split_pdf,
    text_in_line_range,
    text_in_rect,
    unlock_pdf,
)
from app.web.api.result import api_method, fail, ok, require


class PdfApiMixin:
    @api_method
    def pdf_open_doc(self, params: dict[str, Any]) -> dict[str, Any]:
        # Open PDF document and return page count and metadata.
        require(params, "file_path")
        file_path = str(params["file_path"])
        doc = open_pdf(file_path)
        count = page_count(doc)
        needs_ocr = pdf_needs_ocr(doc)
        formats = PAGE_IMAGE_FORMATS
        doc.close()
        return ok(page_count=count, needs_ocr=needs_ocr, formats=formats, file_path=file_path)

    @api_method
    def pdf_render_page(self, params: dict[str, Any]) -> dict[str, Any]:
        # Render PDF page to base64 PNG data URL with specified DPI.
        require(params, "file_path", "page_number")
        file_path = str(params["file_path"])
        page_num = int(params["page_number"])
        dpi = int(params.get("dpi", 150))
        doc = open_pdf(file_path)
        if page_num < 0 or page_num >= len(doc):
            doc.close()
            return fail(f"Page index {page_num} out of bounds (0..{len(doc)-1})", code="IndexError")
        page = doc[page_num]
        pix = page.get_pixmap(dpi=dpi)
        data = pix.tobytes("png")
        doc.close()
        b64 = base64.b64encode(data).decode("ascii")
        return ok(data_url=f"data:image/png;base64,{b64}", width=pix.width, height=pix.height, page_number=page_num)

    @api_method
    def pdf_rotate_page(self, params: dict[str, Any]) -> dict[str, Any]:
        # Rotate specific PDF page by degrees.
        require(params, "file_path", "page_number", "degrees")
        file_path = str(params["file_path"])
        page_num = int(params["page_number"])
        degrees = int(params["degrees"])
        out_p = str(params.get("output_path", file_path))
        doc = open_pdf(file_path)
        if page_num < 0 or page_num >= len(doc):
            doc.close()
            return fail("Page index out of bounds", code="IndexError")
        doc[page_num].set_rotation(degrees % 360)
        data = doc.tobytes()
        doc.close()
        Path(out_p).write_bytes(data)
        return ok(output_path=out_p)

    @api_method
    def pdf_rotate_pages(self, params: dict[str, Any]) -> dict[str, Any]:
        # Rotate multiple PDF pages simultaneously by specified degrees.
        require(params, "file_path", "pages", "degrees")
        file_path = str(params["file_path"])
        pages = [int(p) for p in params["pages"]]
        degrees = int(params["degrees"])
        out_p = str(params.get("output_path", file_path))
        doc = open_pdf(file_path)
        for page_num in pages:
            if 0 <= page_num < len(doc):
                current_rot = doc[page_num].rotation
                doc[page_num].set_rotation((current_rot + degrees) % 360)
        data = doc.tobytes()
        doc.close()
        Path(out_p).write_bytes(data)
        return ok(output_path=out_p, rotated_count=len(pages))

    @api_method
    def pdf_delete_page(self, params: dict[str, Any]) -> dict[str, Any]:
        # Delete page from PDF document.
        require(params, "file_path", "page_number")
        file_path = str(params["file_path"])
        page_num = int(params["page_number"])
        out_p = str(params.get("output_path", file_path))
        doc = open_pdf(file_path)
        if page_num < 0 or page_num >= len(doc):
            doc.close()
            return fail("Page index out of bounds", code="IndexError")
        doc.delete_page(page_num)
        count = len(doc)
        data = doc.tobytes()
        doc.close()
        Path(out_p).write_bytes(data)
        return ok(output_path=out_p, page_count=count)

    @api_method
    def pdf_extract_single_page(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract single page from PDF into standalone PDF document.
        require(params, "file_path", "page_number", "output_path")
        file_path = str(params["file_path"])
        page_num = int(params["page_number"])
        out_p = str(params["output_path"])
        if out_p.lower().endswith(".pdf"):
            op = [{"source_page": page_num + 1, "rotation": 0}]
            reorganize_pdf_pages(file_path, out_p, op)
        else:
            export_pdf_pages(file_path, [page_num], out_p)
        return ok(output_path=out_p)

    @api_method
    def pdf_extract_page(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for single page extraction.
        return self.pdf_extract_single_page(params)

    @api_method
    def pdf_reorder_pages(self, params: dict[str, Any]) -> dict[str, Any]:
        # Reorder pages of PDF according to index list.
        require(params, "file_path", "order")
        file_path = str(params["file_path"])
        raw_order = list(params["order"])
        out_p = str(params.get("output_path", file_path))
        ops: list[dict[str, Any]] = []
        for item in raw_order:
            if isinstance(item, dict):
                ops.append(item)
            elif isinstance(item, int):
                ops.append({"source_page": item + 1, "rotation": 0})
        reorganize_pdf_pages(file_path, out_p, ops)
        return ok(output_path=out_p)

    @api_method
    def pdf_reorganize(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for page reordering.
        return self.pdf_reorder_pages(params)

    @api_method
    def pdf_merge(self, params: dict[str, Any]) -> dict[str, Any]:
        # Merge multiple PDF documents into single PDF.
        require(params, "file_paths", "output_path")
        paths = list(params["file_paths"])
        out_p = str(params["output_path"])
        merge_pdfs(paths, out_p)
        return ok(output_path=out_p)

    @api_method
    def pdf_split(self, params: dict[str, Any]) -> dict[str, Any]:
        # Split PDF by page ranges or individual pages.
        require(params, "file_path", "output_dir")
        file_path = str(params["file_path"])
        out_dir = str(params["output_dir"])
        ranges = params.get("ranges")
        if ranges:
            files = split_pdf(file_path, str(ranges), out_dir)
        else:
            files = break_pdf_into_pages(file_path, out_dir)
        return ok(files=files, output_dir=out_dir)

    @api_method
    def pdf_compress(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compress PDF document to reduce file size.
        require(params, "file_path", "output_path")
        file_path = str(params["file_path"])
        out_p = str(params["output_path"])
        lvl = str(params.get("level", "medium"))
        res_p = compress_pdf(file_path, out_p, level=lvl)
        return ok(output_path=res_p)

    @api_method
    def pdf_extract_text(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract plain text content from PDF document.
        require(params, "file_path")
        file_path = str(params["file_path"])
        doc = open_pdf(file_path)
        pages_text: list[str] = []
        for p in doc:
            pages_text.append(p.get_text())
        full_text = "\n\n".join(pages_text)
        out_p = params.get("output_path")
        if out_p:
            save_pdf_text(full_text, str(out_p))
        doc.close()
        return ok(text=full_text, page_count=len(pages_text), output_path=out_p)

    @api_method
    def pdf_watermark(self, params: dict[str, Any]) -> dict[str, Any]:
        # Apply text watermark across all pages of PDF.
        require(params, "file_path", "output_path", "text")
        file_path = str(params["file_path"])
        out_p = str(params["output_path"])
        text = str(params["text"])
        f_size = int(params.get("font_size", 48))
        op = float(params.get("opacity", 0.25))
        res_p = add_pdf_watermark(file_path, text, out_p, font_size=f_size, opacity=op)
        return ok(output_path=res_p)

    @api_method
    def pdf_protect(self, params: dict[str, Any]) -> dict[str, Any]:
        # Password protect and encrypt PDF document.
        require(params, "file_path", "output_path", "password")
        file_path = str(params["file_path"])
        out_p = str(params["output_path"])
        pw = str(params["password"])
        res_p = protect_pdf(file_path, pw, out_p)
        return ok(output_path=res_p)

    @api_method
    def pdf_unlock(self, params: dict[str, Any]) -> dict[str, Any]:
        # Unlock password-protected PDF document.
        require(params, "file_path", "output_path", "password")
        file_path = str(params["file_path"])
        out_p = str(params["output_path"])
        pw = str(params["password"])
        res_p = unlock_pdf(file_path, pw, out_p)
        return ok(output_path=res_p)

    @api_method
    def pdf_add_page_numbers(self, params: dict[str, Any]) -> dict[str, Any]:
        # Add formatted page numbers to PDF footer or header.
        require(params, "file_path", "output_path")
        file_path = str(params["file_path"])
        out_p = str(params["output_path"])
        fmt = str(params.get("format", "Page {n} of {total}"))
        pos = str(params.get("position", "bottom_center"))
        res_p = add_page_numbers(file_path, out_p, format_str=fmt, position=pos)
        return ok(output_path=res_p)

    @api_method
    def pdf_page_numbers(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for adding page numbers.
        return self.pdf_add_page_numbers(params)

    @api_method
    def pdf_save_annotated_page(self, params: dict[str, Any]) -> dict[str, Any]:
        # Burn annotation markings into PDF.
        require(params, "file_path", "annotations", "output_path")
        file_path = str(params["file_path"])
        annots = list(params["annotations"])
        out_p = str(params["output_path"])
        page_num = int(params.get("page_number", 0))
        doc = open_pdf(file_path)
        norm_annots: list[dict[str, Any]] = []
        for a in annots:
            a_copy = dict(a)
            if "rect" not in a_copy and "x" in a_copy and "y" in a_copy:
                x0 = a_copy["x"]
                y0 = a_copy["y"]
                w_val = a_copy.get("w", a_copy.get("width", 0))
                h_val = a_copy.get("h", a_copy.get("height", 0))
                a_copy["rect"] = [x0, y0, x0 + w_val, y0 + h_val]
            norm_annots.append(a_copy)
        bake_annotations(doc, page_num, norm_annots)
        save_annotated_pdf(doc, out_p)
        doc.close()
        return ok(output_path=out_p)

    @api_method
    def pdf_to_docx(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert scanned or digital PDF document to editable DOCX.
        require(params, "file_path", "output_path")
        file_path = str(params["file_path"])
        out_p = str(params["output_path"])
        res_p = convert_scanned_pdf_to_docx(file_path, out_p)
        return ok(output_path=res_p)

    @api_method
    def pdf_create_searchable_pdf(self, params: dict[str, Any]) -> dict[str, Any]:
        # Create searchable PDF with OCR text layer.
        require(params, "file_path", "output_path")
        file_path = str(params["file_path"])
        out_p = str(params["output_path"])
        lang = str(params.get("language", "eng"))
        dpi = int(params.get("dpi", 150))
        res_p = create_searchable_pdf(file_path, out_p, language=lang, dpi=dpi)
        return ok(output_path=res_p)

    @api_method
    def pdf_batch_operations(self, params: dict[str, Any]) -> dict[str, Any]:
        # Run batch PDF operations (watermark, protect, compress).
        require(params, "items", "operation")
        op = str(params["operation"]).lower()
        items = [
            BatchPdfItem(
                source_path=str(it["source_path"]),
                output_path=it.get("output_path"),
                options=it.get("options", {}),
            )
            for it in params["items"]
        ]
        if op == "watermark_text":
            results = batch_add_pdf_watermark(items, str(params.get("watermark_text", "")))
        elif op == "watermark_image":
            results = batch_add_image_watermark(items, str(params.get("image_path", "")))
        elif op == "protect":
            results = batch_protect_pdfs(items, str(params.get("password", "")))
        elif op == "compress":
            results = batch_compress_pdfs(items)
        else:
            return fail(f"Unsupported batch op: {op}", code="InvalidOperation")
        return ok(results=results)

    @api_method
    def pdf_query_rect(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract text bounded within rectangular coordinates or line numbers.
        require(params, "file_path", "page_number")
        file_path = str(params["file_path"])
        page_num = int(params["page_number"])
        doc = open_pdf(file_path)
        page = doc[page_num]
        rect = params.get("rect")
        if rect:
            txt = text_in_rect(page, rect)
        else:
            txt = text_in_line_range(page, int(params.get("start_line", 0)), int(params.get("end_line", 100)))
        doc.close()
        return ok(text=txt)
