from pathlib import Path
from typing import Any

from app.features.metadata.ops import (
    batch_metadata_cleanup,
    editable_keys,
    export_metadata,
    inspect_metadata,
    save_edited_metadata,
    strip_metadata,
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
        # Remove all EXIF and identifying metadata fields from file.
        require(params, "file_path")
        file_path = str(params["file_path"])
        out_path = params.get("output_path")
        result_path = strip_metadata(file_path, output_path=str(out_path) if out_path else None)
        return ok(output_path=result_path)

    @api_method
    def metadata_save(self, params: dict[str, Any]) -> dict[str, Any]:
        # Save edited metadata tag values back to file.
        require(params, "file_path", "updates")
        file_path = str(params["file_path"])
        updates = dict(params["updates"])
        out_path = params.get("output_path")
        result_path = save_edited_metadata(file_path, updates, output_path=str(out_path) if out_path else None)
        return ok(output_path=result_path)

    @api_method
    def metadata_editable_keys(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return list of modifiable metadata fields for file kind.
        require(params, "file_path")
        file_path = str(params["file_path"])
        keys = editable_keys(file_path)
        return ok(keys=keys, file_path=file_path)

    @api_method
    def metadata_batch_cleanup(self, params: dict[str, Any]) -> dict[str, Any]:
        # Batch strip or clean metadata across multiple files.
        require(params, "file_paths")
        paths = list(params["file_paths"])
        inplace = bool(params.get("inplace", True))
        results = batch_metadata_cleanup(paths, inplace=inplace)
        return ok(results=results)

    @api_method
    def metadata_export(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export metadata report to JSON or text file.
        require(params, "file_path", "output_path")
        file_path = str(params["file_path"])
        out_path = str(params["output_path"])
        export_metadata(file_path, out_path)
        return ok(output_path=out_path)
