from __future__ import annotations

import os
from typing import Any

from app.features.archive.ops import (
    archive_format_for_path,
    compare_directory_snapshots,
    convert_archive_format,
    create_incremental_backup,
    create_multi_source_archive,
    create_password_protected_bundle,
    extract_archive,
    extract_password_protected_bundle,
    extract_selected_members,
    inspect_archive_members,
    rotate_bundle_key,
    snapshot_directory,
    test_archive,
    verify_bundle_integrity,
)
from app.web.api.result import api_method, ok, require


def _strip_archive_suffix(path_str: str) -> str:
    # Strip compound archive extensions cleanly before appending suffixes.
    raw_path = str(path_str)
    compound_exts = (
        ".tar.gz", ".tar.xz", ".tar.bz2",
        ".tgz", ".txz", ".tbz2",
        ".zip", ".tar", ".fossbundle", ".enc",
    )
    lower = raw_path.lower()
    for ext in compound_exts:
        if lower.endswith(ext):
            return raw_path[:-len(ext)]
    return os.path.splitext(raw_path)[0]


class ArchiveApiMixin:
    @api_method
    def archive_presets(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return archive format and compression presets.
        presets = [
            {"id": "zip_store", "name": "zip_store", "format": "zip", "level": 0, "description": "Store without compression"},
            {"id": "zip_balanced", "name": "zip_balanced", "format": "zip", "level": 6, "description": "Standard balanced compression"},
            {"id": "zip_maximum", "name": "zip_maximum", "format": "zip", "level": 9, "description": "Maximum compression level"},
        ]
        return ok(presets=presets)
    @api_method
    def archive_create(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compress files or folders into archive (zip, tar, tar.gz, tar.xz, tar.bz2).
        sources = list(params.get("sources") or params.get("source_paths") or [])
        if not sources:
            require(params, "sources")
        fmt = str(params.get("format", "zip")).lower().lstrip(".")
        compression_level = int(params.get("compression_level", 6))
        output_path = str(params.get("output_path", "")).strip()
        if not output_path and sources:
            base = _strip_archive_suffix(str(sources[0]))
            ext = ".tar.gz" if fmt in ("tar.gz", "tgz") else f".{fmt}"
            output_path = f"{base}_bundle{ext}"

        created = create_multi_source_archive(
            [str(source_item) for source_item in sources],
            output_path,
            fmt=fmt,
            compression_level=compression_level,
        )
        return ok(output_path=created)

    @api_method
    def archive_extract(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract files from archive to target folder.
        require(params, "archive_path")
        arch_path = str(params["archive_path"])
        target_dir = str(params.get("target_dir", "")).strip()
        if not target_dir:
            target_dir = _strip_archive_suffix(arch_path) + "_extracted"
        extracted = extract_archive(arch_path, target_dir)
        return ok(extracted=extracted, target_dir=target_dir)

    @api_method
    def archive_extract_selected(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract specific chosen members from archive to target folder.
        require(params, "archive_path", "members")
        arch_path = str(params["archive_path"])
        members = [str(m) for m in params["members"]]
        target_dir = str(params.get("target_dir", "")).strip()
        if not target_dir:
            target_dir = _strip_archive_suffix(arch_path) + "_extracted"
        extracted = extract_selected_members(arch_path, members, target_dir)
        return ok(extracted=extracted, target_dir=target_dir)

    @api_method
    def archive_list(self, params: dict[str, Any]) -> dict[str, Any]:
        # List contents and rich file metadata inside archive.
        require(params, "archive_path")
        arch_path = str(params["archive_path"])
        members = inspect_archive_members(arch_path)
        contents = [m["path"] for m in members]
        fmt = archive_format_for_path(arch_path)
        total_size = sum(m["size_bytes"] for m in members)
        total_compressed = sum(m["compressed_bytes"] for m in members)
        return ok(
            contents=contents,
            files=contents,
            members=members,
            count=len(members),
            format=fmt,
            total_size_bytes=total_size,
            total_compressed_bytes=total_compressed,
        )

    @api_method
    def archive_test(self, params: dict[str, Any]) -> dict[str, Any]:
        # Test archive integrity and detect corrupt files.
        require(params, "archive_path")
        arch_path = str(params["archive_path"])
        res = test_archive(arch_path)
        return ok(valid=res.get("valid", False), message=res.get("error", "Integrity check passed."), details=res)

    @api_method
    def archive_convert(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert archive format to another compression type.
        require(params, "archive_path", "output_path")
        arch_path = str(params["archive_path"])
        out_path = str(params["output_path"])
        converted = convert_archive_format(arch_path, out_path, overwrite=bool(params.get("overwrite", True)))
        return ok(output_path=converted)

    @api_method
    def archive_protect(self, params: dict[str, Any]) -> dict[str, Any]:
        # Create encrypted password-protected bundle.
        sources = list(params.get("source_paths") or params.get("sources") or [])
        if not sources:
            require(params, "source_paths")
        require(params, "password")
        password_val = str(params["password"])
        out_path = str(params.get("output_path", "")).strip()
        if not out_path and sources:
            out_path = _strip_archive_suffix(str(sources[0])) + "_protected.fossbundle"
        fmt = str(params.get("format", "zip"))

        if len(sources) == 1:
            bundle_path = create_password_protected_bundle(str(sources[0]), out_path, password_val, archive_format=fmt)
        else:
            import tempfile
            temp_bundle_src = tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False)
            temp_bundle_src.close()
            try:
                create_multi_source_archive([str(s) for s in sources], temp_bundle_src.name, fmt=fmt)
                bundle_path = create_password_protected_bundle(temp_bundle_src.name, out_path, password_val, archive_format=fmt)
            finally:
                if os.path.exists(temp_bundle_src.name):
                    os.unlink(temp_bundle_src.name)
        return ok(output_path=bundle_path)

    @api_method
    def archive_unprotect(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract password-protected bundle.
        require(params, "bundle_path", "password")
        b_path = str(params["bundle_path"])
        target = str(params.get("target_dir", "")).strip()
        if not target:
            target = _strip_archive_suffix(b_path) + "_decrypted"
        password_val = str(params["password"])
        extracted = extract_password_protected_bundle(b_path, target, password_val)
        return ok(extracted=extracted, target_dir=target)

    @api_method
    def archive_verify_integrity(self, params: dict[str, Any]) -> dict[str, Any]:
        # Verify bundle integrity and tamper resistance.
        require(params, "bundle_path")
        b_path = str(params["bundle_path"])
        password_val = params.get("password")
        res = verify_bundle_integrity(b_path, str(password_val) if password_val else None)
        return ok(valid=res.get("valid", False), entries=res.get("entries", []), error=res.get("error"))

    @api_method
    def archive_rotate_key(self, params: dict[str, Any]) -> dict[str, Any]:
        # Re-encrypt bundle with new password.
        require(params, "bundle_path", "old_password", "new_password")
        b_path = str(params["bundle_path"])
        old_password = str(params["old_password"])
        new_password = str(params["new_password"])
        out_p = params.get("output_path")
        rotated = rotate_bundle_key(b_path, old_password, new_password, str(out_p) if out_p else None)
        return ok(rotated=True, output_path=rotated)

    @api_method
    def archive_snapshot(self, params: dict[str, Any]) -> dict[str, Any]:
        # Take filesystem snapshot of directory tree.
        require(params, "directory_path")
        dir_p = str(params["directory_path"])
        out_manifest = params.get("manifest_path")
        snap = snapshot_directory(dir_p, str(out_manifest) if out_manifest else None)
        return ok(snapshot=snap, file_count=len(snap.get("files", {})))

    @api_method
    def archive_compare_snapshots(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compare two directory snapshots for incremental backup.
        require(params, "old_snapshot", "new_snapshot")
        old_s = dict(params["old_snapshot"])
        new_s = dict(params["new_snapshot"])
        diff = compare_directory_snapshots(old_s, new_s)
        return ok(
            diff=diff,
            added=diff["added"],
            modified=diff["changed"],
            removed=diff["removed"],
            total_changed=diff["total_changed"],
        )

    @api_method
    def archive_incremental_backup(self, params: dict[str, Any]) -> dict[str, Any]:
        # Create incremental backup archive based on changed files.
        require(params, "directory_path", "backup_dir")
        src = str(params["directory_path"])
        backup_d = str(params["backup_dir"])
        manifest_name = str(params.get("manifest_name", "snapshot.json"))
        fmt = str(params.get("format", "zip"))
        archive_name = params.get("archive_name")
        res = create_incremental_backup(
            src,
            backup_d,
            manifest_name=manifest_name,
            archive_name=str(archive_name) if archive_name else None,
            archive_format=fmt,
        )
        return ok(
            archive_path=res["archive_path"],
            manifest_path=res["manifest_path"],
            files=res["files"],
            total_files=res["total_files"],
            diff=res["diff"],
        )
