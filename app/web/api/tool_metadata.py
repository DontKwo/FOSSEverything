import os
from pathlib import Path
from typing import Any

from app.features.metadata.ops import (
    batch_metadata_cleanup,
    camera_field_presets,
    compare_metadata,
    editable_keys,
    export_metadata,
    gps_preview_for_metadata,
    inspect_metadata,
    metadata_support_report,
    save_edited_metadata,
    strip_with_backup,
)
from app.web.api.result import api_method, ok, require


class MetadataApiMixin:
    @api_method
    def metadata_inspect(self, params: dict[str, Any]) -> dict[str, Any]:
        # Inspect and extract EXIF and document metadata from file.
        require(params, "file_path")
        file_path = str(params["file_path"])
        data = inspect_metadata(file_path)
        return ok(metadata=data, file_path=file_path)

    @api_method
    def metadata_strip(self, params: dict[str, Any]) -> dict[str, Any]:
        # Remove identifying metadata from a file, optionally keeping a backup of the original.
        require(params, "file_path")
        file_path = str(params["file_path"])
        p = Path(file_path)
        out_path = str(params["output_path"]) if params.get("output_path") else str(p.parent / f"{p.stem}_clean{p.suffix}")
        res = strip_with_backup(file_path, out_path, backup=bool(params.get("backup", False)))
        return ok(output_path=res["output_path"], removed_fields_count=res["removed_fields_count"], backup_path=res["backup_path"])

    @api_method
    def metadata_strip_any(self, params: dict[str, Any]) -> dict[str, Any]:
        # Universal metadata stripper returning count and output path.
        return self.metadata_strip(params)

    @api_method
    def metadata_save(self, params: dict[str, Any]) -> dict[str, Any]:
        # Save edited metadata tag values back to file.
        require(params, "file_path", "updates")
        file_path = str(params["file_path"])
        updates = dict(params["updates"])
        p = Path(file_path)
        out_path = str(params["output_path"]) if params.get("output_path") else str(p.parent / f"{p.stem}_edited{p.suffix}")
        result_path = save_edited_metadata(file_path, out_path, updates)
        return ok(output_path=result_path)

    @api_method
    def metadata_editable_keys(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return list of modifiable metadata fields for file kind.
        require(params, "file_path")
        file_path = str(params["file_path"])
        keys = editable_keys(file_path)
        return ok(keys=list(keys), file_path=file_path)

    @api_method
    def metadata_batch_cleanup(self, params: dict[str, Any]) -> dict[str, Any]:
        # Batch strip or clean metadata across directory.
        require(params, "input_dir")
        in_dir = str(params["input_dir"])
        out_dir = str(params["output_dir"]) if params.get("output_dir") else f"{in_dir}_clean"
        if os.path.abspath(in_dir) == os.path.abspath(out_dir):
            out_dir = f"{in_dir}_clean"
        recursive = bool(params.get("recursive", True))
        preview = bool(params.get("preview", False))
        results = batch_metadata_cleanup(in_dir, out_dir, recursive=recursive, preview=preview)
        return ok(results=results)

    @api_method
    def metadata_export(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export metadata report to JSON or text file.
        require(params, "file_path", "output_path")
        file_path = str(params["file_path"])
        out_path = str(params["output_path"])
        export_metadata(file_path, out_path)
        return ok(output_path=out_path)

    @api_method
    def metadata_compare(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compare before and after metadata records.
        require(params, "before", "after")
        diff = compare_metadata(params["before"], params["after"])
        return ok(**diff)

    @api_method
    def metadata_gps_preview(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compute GPS location readout from metadata map or file path.
        fpath = str(params.get("file_path", ""))
        if "metadata" in params:
            meta = dict(params["metadata"])
        elif fpath:
            meta = inspect_metadata(fpath)
        else:
            meta = {}
        gps = gps_preview_for_metadata(meta, file_path=fpath)
        return ok(gps=gps)

    @api_method
    def metadata_presets(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return standard camera field presets.
        return ok(presets=camera_field_presets())

    @api_method
    def metadata_support_report(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return format capability and backend safety report for file.
        require(params, "file_path")
        rep = metadata_support_report(str(params["file_path"]))
        return ok(**rep)
