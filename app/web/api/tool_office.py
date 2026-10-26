from pathlib import Path
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
        require(params, "input_path", "output_path")
        out_p = docx_to_pdf(str(params["input_path"]), str(params["output_path"]))
        return ok(output_path=out_p)

    @api_method
    def office_docx_to_markdown(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert DOCX word processing document to Markdown.
        require(params, "input_path")
        in_p = str(params["input_path"])
        out_p = params.get("output_path")
        md_text = docx_to_markdown(in_p, str(out_p) if out_p else None)
        return ok(markdown=md_text, output_path=out_p)

    @api_method
    def office_pptx_to_markdown(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert PowerPoint presentation slides to Markdown outline.
        require(params, "input_path")
        in_p = str(params["input_path"])
        out_p = params.get("output_path")
        md_text = pptx_to_markdown(in_p, str(out_p) if out_p else None)
        return ok(markdown=md_text, output_path=out_p)

    @api_method
    def office_xlsx_to_csv(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export Excel spreadsheet sheets to CSV format.
        require(params, "input_path", "output_dir")
        csv_files = xlsx_to_csv(str(params["input_path"]), str(params["output_dir"]))
        return ok(csv_files=csv_files)

    @api_method
    def office_metadata(self, params: dict[str, Any]) -> dict[str, Any]:
        # Inspect or strip office document metadata.
        require(params, "file_path")
        file_path = str(params["file_path"])
        action = str(params.get("action", "inspect")).lower()
        if action == "strip":
            out_p = params.get("output_path")
            res_p = strip_office_metadata(file_path, str(out_p) if out_p else None)
            return ok(output_path=res_p)
        meta = get_office_metadata(file_path)
        return ok(metadata=meta)
