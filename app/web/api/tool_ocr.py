# OCR API mixin for text recognition, searchable PDF creation, and batch jobs.
import base64
import io
from pathlib import Path
from typing import Any

from PIL import Image

from app.features.ocr.ops import (
    SUPPORTED_LANGUAGES,
    create_searchable_pdf,
    discover_tesseract_languages,
    expand_ocr_inputs,
    get_supported_languages,
    inspect_pdf_searchable_status,
    ocr_file,
    ocr_image,
    ocr_pdf,
    parse_page_selection,
    save_ocr_text,
)
from app.web.api.result import api_method, ok, require


def _force_reocr(params: dict[str, Any]) -> bool:
    # Read the force re-OCR flag from either accepted parameter name.
    return bool(params.get("force_reocr", params.get("force_overwrite", False)))


class OcrApiMixin:
    @api_method
    def ocr_recognize_image(self, params: dict[str, Any]) -> dict[str, Any]:
        # Perform optical character recognition on single image file.
        require(params, "file_path")
        file_path = str(params["file_path"])
        lang = str(params.get("language", "eng"))
        dpi = int(params.get("dpi", 150))
        res_dict = ocr_image(file_path, language=lang, dpi=dpi)
        text_out = str(res_dict.get("text", ""))
        out_p = params.get("output_path")
        if out_p:
            as_md = str(params.get("format", "")).lower() == "md" or str(
                out_p
            ).endswith(".md")
            save_ocr_text(res_dict, str(out_p), as_markdown=as_md)
        return ok(text=text_out, output_path=out_p, language=lang, page_count=1)

    @api_method
    def ocr_image(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for image OCR.
        return self.ocr_recognize_image(params)

    @api_method
    def ocr_recognize_pdf(self, params: dict[str, Any]) -> dict[str, Any]:
        # Perform OCR across pages of PDF document with optional page selection.
        require(params, "file_path")
        file_path = str(params["file_path"])
        lang = str(params.get("language", "eng"))
        dpi = int(params.get("dpi", 150))
        force_ow = _force_reocr(params)

        page_spec = params.get("page_range")
        parsed_pages = None
        if page_spec:
            status = inspect_pdf_searchable_status(file_path)
            parsed_pages = parse_page_selection(str(page_spec), status["page_count"])

        res_dict = ocr_pdf(
            file_path,
            pages=parsed_pages,
            language=lang,
            dpi=dpi,
            force_overwrite=force_ow,
        )
        text_out = str(res_dict.get("text", ""))
        out_p = params.get("output_path")
        if out_p:
            as_md = str(params.get("format", "")).lower() == "md" or str(
                out_p
            ).endswith(".md")
            save_ocr_text(res_dict, str(out_p), as_markdown=as_md)

        return ok(
            text=text_out,
            page_texts=res_dict.get("page_texts", []),
            page_count=res_dict.get("page_count", 1),
            skipped_searchable_pages=res_dict.get("skipped_searchable_pages", []),
            hybrid_pages=res_dict.get("hybrid_pages", []),
            ocr_pages=res_dict.get("ocr_pages", []),
            output_path=out_p,
        )

    @api_method
    def ocr_recognize_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Universal OCR dispatcher for images and PDF documents.
        require(params, "file_path")
        file_path = str(params["file_path"])
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return self.ocr_recognize_pdf(params)
        return self.ocr_recognize_image(params)

    @api_method
    def ocr_inspect_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Inspect searchable status and page breakdown for a PDF or image.
        require(params, "file_path")
        file_path = str(params["file_path"])
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            status = inspect_pdf_searchable_status(file_path)
            return ok(**status)
        return ok(
            page_count=1,
            searchable_pages=[],
            hybrid_pages=[],
            scanned_pages=[1],
            is_fully_searchable=False,
        )

    @api_method
    def ocr_preview_image(self, params: dict[str, Any]) -> dict[str, Any]:
        # Render the first frame of an image file as a bounded PNG data URL.
        require(params, "file_path")
        max_dim = int(params.get("max_dim", 1600))
        with Image.open(str(params["file_path"])) as img:
            frame = img.convert("RGB")
        frame.thumbnail((max_dim, max_dim))
        buffer = io.BytesIO()
        frame.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return ok(data_url=f"data:image/png;base64,{encoded}", width=frame.width, height=frame.height)

    @api_method
    def ocr_languages(self, params: dict[str, Any]) -> dict[str, Any]:
        # Query installed and supported Tesseract language packs.
        _ = params
        installed = discover_tesseract_languages()
        supported = get_supported_languages()
        raw_dict = dict(SUPPORTED_LANGUAGES)
        return ok(installed=installed, supported=supported, catalog=raw_dict)

    @api_method
    def ocr_scan_inputs(self, params: dict[str, Any]) -> dict[str, Any]:
        # Expand directory path into list of individual supported OCR files.
        raw_paths = list(params.get("paths") or [])
        recursive = bool(params.get("recursive", True))
        expanded = expand_ocr_inputs([str(p) for p in raw_paths], recursive=recursive)
        return ok(paths=expanded, count=len(expanded))

    @api_method
    def ocr_create_searchable_pdf(self, params: dict[str, Any]) -> dict[str, Any]:
        # Synthesize searchable PDF document preserving existing searchable text.
        require(params, "input_path", "output_path")
        in_p = str(params["input_path"])
        out_p = str(params["output_path"])
        lang = str(params.get("language", "eng"))
        dpi = int(params.get("dpi", 150))
        force_ow = _force_reocr(params)

        page_spec = params.get("pages") or params.get("page_range")
        parsed_pages = None
        if page_spec and in_p.lower().endswith(".pdf"):
            if isinstance(page_spec, str):
                parsed_pages = page_spec
            else:
                status = inspect_pdf_searchable_status(in_p)
                parsed_pages = parse_page_selection(
                    str(page_spec), status["page_count"]
                )

        res_p = create_searchable_pdf(
            in_p,
            out_p,
            pages=parsed_pages,
            language=lang,
            dpi=dpi,
            force_overwrite=force_ow,
            force_reocr=force_ow,
        )
        return ok(output_path=res_p)

    @api_method
    def ocr_batch(self, params: dict[str, Any]) -> dict[str, Any]:
        # Process multiple files and folders in batch OCR mode.
        raw_paths = params.get("paths") or params.get("file_paths") or []
        if not raw_paths:
            return ok(results=[], count=0)

        recursive = bool(params.get("recursive", True))
        expanded_files = expand_ocr_inputs(
            [str(p) for p in raw_paths], recursive=recursive
        )

        lang = str(params.get("language", "eng"))
        dpi = int(params.get("dpi", 150))
        out_format = str(params.get("format", "pdf")).lower()
        make_pdf = bool(params.get("searchable_pdf", False)) or out_format == "pdf"
        force_ow = _force_reocr(params)
        out_dir = params.get("output_dir")

        results: list[dict[str, Any]] = []
        for p in expanded_files:
            try:
                p_obj = Path(p)
                dest_dir = Path(out_dir) if out_dir else p_obj.parent
                dest_dir.mkdir(parents=True, exist_ok=True)

                if make_pdf:
                    dest = str(dest_dir / f"{p_obj.stem}_searchable.pdf")
                    res_p = create_searchable_pdf(
                        p, dest, language=lang, dpi=dpi, force_overwrite=force_ow
                    )
                    results.append({"path": p, "ok": True, "output_path": res_p})
                else:
                    ext = ".md" if out_format == "md" else ".txt"
                    txt_dest = str(dest_dir / f"{p_obj.stem}_ocr{ext}")
                    res_dict = ocr_file(
                        p, language=lang, dpi=dpi, force_overwrite=force_ow
                    )
                    save_ocr_text(res_dict, txt_dest, as_markdown=(out_format == "md"))
                    results.append(
                        {
                            "path": p,
                            "ok": True,
                            "output_path": txt_dest,
                            "length": len(res_dict.get("text", "")),
                        }
                    )
            except Exception as e:
                results.append({"path": p, "ok": False, "error": str(e)})

        return ok(results=results, count=len(results))
