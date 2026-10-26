import os
from typing import Any

from app.features.office.ops import (
    docx_to_markdown,
    docx_to_pdf,
    extract_text_from_office,
    get_office_metadata,
    pptx_to_markdown,
    strip_office_metadata,
    xlsx_to_csv,
)
from app.web.api.result import api_method, ok, require


class OfficeApiMixin:
    @api_method
    def office_extract(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract text content from DOCX, PPTX, XLSX, ODT, ODS, ODP files.
        require(params, "file_path")
        file_path = str(params["file_path"])
        text = extract_text_from_office(file_path)
        meta = get_office_metadata(file_path)
        return ok(text=text, metadata=meta, file_path=file_path)

    @api_method
    def office_docx_to_pdf(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert DOCX word processing document to PDF.
        require(params, "input_path")
        in_p = str(params["input_path"])
        out_p = str(params.get("output_path", "")).strip()
        if not out_p:
            out_p = os.path.splitext(in_p)[0] + ".pdf"
        res_p = docx_to_pdf(in_p, out_p)
        return ok(output_path=res_p)

    @api_method
    def office_docx_to_markdown(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert DOCX word processing document to Markdown.
        require(params, "input_path")
        in_p = str(params["input_path"])
        out_p = str(params.get("output_path", "")).strip()
        if not out_p:
            out_p = os.path.splitext(in_p)[0] + ".md"
        md_text = docx_to_markdown(in_p)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(md_text)
        return ok(markdown=md_text, output_path=out_p)

    @api_method
    def office_pptx_to_markdown(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert PowerPoint presentation slides to Markdown outline.
        require(params, "input_path")
        in_p = str(params["input_path"])
        out_p = str(params.get("output_path", "")).strip()
        if not out_p:
            out_p = os.path.splitext(in_p)[0] + ".md"
        md_text = pptx_to_markdown(in_p)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(md_text)
        return ok(markdown=md_text, output_path=out_p)

    @api_method
    def office_xlsx_to_csv(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export Excel spreadsheet sheets to CSV format.
        require(params, "input_path")
        in_p = str(params["input_path"])
        out_p = str(params.get("output_path", params.get("output_dir", ""))).strip()
        if not out_p or os.path.isdir(out_p):
            base_dir = out_p if out_p and os.path.isdir(out_p) else os.path.dirname(in_p)
            out_p = os.path.join(base_dir, os.path.splitext(os.path.basename(in_p))[0] + ".csv")
        sheet_idx = int(params.get("sheet_index", 0))
        csv_path = xlsx_to_csv(in_p, out_p, sheet_index=sheet_idx)
        return ok(output_path=csv_path, csv_files=[csv_path])

    @api_method
    def office_metadata(self, params: dict[str, Any]) -> dict[str, Any]:
        # Inspect or strip office document metadata.
        require(params, "file_path")
        file_path = str(params["file_path"])
        action = str(params.get("action", "inspect")).lower()
        if action == "strip":
            out_p = str(params.get("output_path", "")).strip()
            if not out_p:
                stem, ext = os.path.splitext(file_path)
                out_p = f"{stem}_stripped{ext}"
            res_p = strip_office_metadata(file_path, out_p)
            return ok(output_path=res_p)
        meta = get_office_metadata(file_path)
        return ok(metadata=meta)
