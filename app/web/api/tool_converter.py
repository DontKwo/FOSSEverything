from pathlib import Path
from typing import Any

from app.features.converter.ops import (
    BatchConversionItem,
    available_targets,
    batch_convert_files,
    conversion_summary,
    convert_file,
    export_enex,
    source_family,
)
from app.features.media.ops import compress_media
from app.web.api.result import api_method, ok, require


class ConverterApiMixin:
    @api_method
    def converter_available_targets(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return list of compatible destination formats for source file.
        require(params, "file_path")
        file_path = str(params["file_path"])
        family = source_family(file_path)
        targets = available_targets(file_path)
        return ok(family=family, targets=targets, file_path=file_path)

    @api_method
    def converter_convert_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert file to target format with optional quality and DPI parameters.
        require(params, "file_path", "target_format")
        file_path = str(params["file_path"])
        target_fmt = str(params["target_format"])
        out_p = params.get("output_path")
        dpi = int(params.get("dpi", 150))
        if out_p:
            out_dir = str(Path(out_p).parent)
            out_stem = Path(out_p).stem
        else:
            out_dir = str(Path(file_path).parent)
            out_stem = None
        created_files = convert_file(file_path, out_dir, target_fmt, dpi=dpi, output_stem=out_stem)
        res_path = created_files[0] if created_files else str(out_p or file_path)
        return ok(output_path=res_path, files=created_files)

    @api_method
    def convert_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for single file conversion.
        return self.converter_convert_file(params)

    @api_method
    def converter_batch_convert(self, params: dict[str, Any]) -> dict[str, Any]:
        # Batch convert list of files to respective target formats.
        require(params, "items")
        raw_items = list(params["items"])
        batch_items = [
            BatchConversionItem(
                input_path=str(item.get("input_path", item.get("source_path", ""))),
                target_format=str(item.get("target_format", "")),
                output_stem=item.get("output_stem"),
            )
            for item in raw_items
        ]
        out_dir = str(params.get("output_dir", ""))
        if not out_dir and batch_items:
            out_dir = str(Path(batch_items[0].input_path).parent)
        results = batch_convert_files(batch_items, out_dir)
        summary = f"Converted {len(results)} file(s)"
        return ok(results=results, summary=summary)

    @api_method
    def converter_summary(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return explanation of output shape before conversion.
        require(params, "file_path", "target_format")
        file_path = str(params["file_path"])
        target_fmt = str(params["target_format"])
        summary_text = conversion_summary(file_path, target_fmt)
        return ok(summary=summary_text)

    @api_method
    def conversion_summary(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for converter summary.
        return self.converter_summary(params)

    @api_method
    def converter_batch(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for batch conversion.
        return self.converter_batch_convert(params)

    @api_method
    def converter_export_enex(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export notes collection to Evernote ENEX XML archive.
        require(params, "notes", "output_path")
        notes = list(params["notes"])
        out_path = str(params["output_path"])
        res_p = export_enex(notes, out_path)
        return ok(output_path=res_p)

    @api_method
    def converter_source_family(self, params: dict[str, Any]) -> dict[str, Any]:
        # Identify source file media family (image, document, audio, video, ebook).
        require(params, "file_path")
        family = source_family(str(params["file_path"]))
        return ok(family=family)

    @api_method
    def converter_compress_media_helper(self, params: dict[str, Any]) -> dict[str, Any]:
        # Helper invoking media compressor when media conversions require recompression.
        require(params, "file_path", "output_path")
        target_size = int(params.get("target_size_mb", 25))
        res_p = compress_media(str(params["file_path"]), str(params["output_path"]), target_size_mb=target_size)
        return ok(output_path=res_p)
