from typing import Any

from app.features.ocr.ops import (
    SUPPORTED_LANGUAGES,
    create_searchable_pdf,
    discover_tesseract_languages,
    get_supported_languages,
    ocr_file,
    ocr_image,
    ocr_pdf,
    save_ocr_text,
)
from app.web.api.result import api_method, ok, require


class OcrApiMixin:
    @api_method
    def ocr_recognize_image(self, params: dict[str, Any]) -> dict[str, Any]:
        # Perform optical character recognition on single image file.
        require(params, "file_path")
        file_path = str(params["file_path"])
        lang = str(params.get("language", "eng"))
        text = ocr_image(file_path, language=lang)
        out_p = params.get("output_path")
        if out_p:
            save_ocr_text(text, str(out_p))
        return ok(text=text, output_path=out_p, language=lang)

    @api_method
    def ocr_image(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for image OCR.
        return self.ocr_recognize_image(params)

    @api_method
    def ocr_recognize_pdf(self, params: dict[str, Any]) -> dict[str, Any]:
        # Perform OCR across pages of scanned PDF document.
        require(params, "file_path")
        file_path = str(params["file_path"])
        lang = str(params.get("language", "eng"))
        dpi = int(params.get("dpi", 150))
        results = ocr_pdf(file_path, language=lang, dpi=dpi)
        text = "\n\n".join(results)
        out_p = params.get("output_path")
        if out_p:
            save_ocr_text(text, str(out_p))
        return ok(text=text, pages=results, page_count=len(results), output_path=out_p)

    @api_method
    def ocr_recognize_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Detect whether file is image or PDF and execute appropriate OCR.
        require(params, "file_path")
        file_path = str(params["file_path"])
        lang = str(params.get("language", "eng"))
        dpi = int(params.get("dpi", 150))
        text = ocr_file(file_path, language=lang, dpi=dpi)
        out_p = params.get("output_path")
        if out_p:
            save_ocr_text(text, str(out_p))
        return ok(text=text, output_path=out_p)

    @api_method
    def ocr_languages(self, params: dict[str, Any]) -> dict[str, Any]:
        # Query installed and supported Tesseract language packs.
        installed = discover_tesseract_languages()
        supported = get_supported_languages()
        raw_dict = dict(SUPPORTED_LANGUAGES)
        return ok(installed=installed, supported=supported, catalog=raw_dict)

    @api_method
    def ocr_create_searchable_pdf(self, params: dict[str, Any]) -> dict[str, Any]:
        # Synthesize searchable PDF document with embedded OCR text layer.
        require(params, "input_path", "output_path")
        in_p = str(params["input_path"])
        out_p = str(params["output_path"])
        lang = str(params.get("language", "eng"))
        dpi = int(params.get("dpi", 150))
        res_p = create_searchable_pdf(in_p, out_p, language=lang, dpi=dpi)
        return ok(output_path=res_p)
