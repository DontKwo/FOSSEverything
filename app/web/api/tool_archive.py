from pathlib import Path
from typing import Any

from app.features.archive.ops import (
    archive_format_for_path,
    compare_directory_snapshots,
    convert_archive_format,
    create_archive,
    create_incremental_backup,
    create_password_protected_bundle,
    extract_archive,
    extract_password_protected_bundle,
    list_archive_contents,
    rotate_bundle_key,
    snapshot_directory,
    test_archive,
    verify_bundle_integrity,
)
from app.web.api.result import api_method, ok, require


class ArchiveApiMixin:
    @api_method
    def archive_create(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compress files or folders into archive (zip, tar, gz, bz2, xz).
        require(params, "sources", "output_path")
        sources = list(params["sources"])
        output_path = str(params["output_path"])
        fmt = params.get("format")
        src = str(sources[0]) if sources else ""
        created = create_archive(src, output_path, archive_format=str(fmt) if fmt else None)
        return ok(output_path=created)

    @api_method
    def archive_extract(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract files from archive to target folder.
        require(params, "archive_path", "target_dir")
        arch_path = str(params["archive_path"])
        target_dir = str(params["target_dir"])
        members = params.get("members")
        extracted = extract_archive(arch_path, target_dir, members=members)
        return ok(extracted=extracted, target_dir=target_dir)

    @api_method
    def archive_list(self, params: dict[str, Any]) -> dict[str, Any]:
        # List contents and file sizes inside archive.
        require(params, "archive_path")
        arch_path = str(params["archive_path"])
        contents = list_archive_contents(arch_path)
        fmt = archive_format_for_path(arch_path)
        return ok(contents=contents, count=len(contents), format=fmt)

    @api_method
    def archive_test(self, params: dict[str, Any]) -> dict[str, Any]:
        # Test archive integrity and detect corrupt files.
        require(params, "archive_path")
        arch_path = str(params["archive_path"])
        valid, msg = test_archive(arch_path)
        return ok(valid=valid, message=msg)

    @api_method
    def archive_convert(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert archive format to another compression type.
        require(params, "archive_path", "output_path")
        arch_path = str(params["archive_path"])
        out_path = str(params["output_path"])
        converted = convert_archive_format(arch_path, out_path)
        return ok(output_path=converted)

    @api_method
    def archive_protect(self, params: dict[str, Any]) -> dict[str, Any]:
        # Create encrypted password-protected bundle.
        require(params, "source_paths", "output_path", "password")
        sources = list(params["source_paths"])
        out_path = str(params["output_path"])
        pw = str(params["password"])
        bundle_path = create_password_protected_bundle(sources, out_path, pw)
        return ok(output_path=bundle_path)

    @api_method
    def archive_unprotect(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract password-protected bundle.
        require(params, "bundle_path", "target_dir", "password")
        b_path = str(params["bundle_path"])
        target = str(params["target_dir"])
        pw = str(params["password"])
        extracted = extract_password_protected_bundle(b_path, target, pw)
        return ok(extracted=extracted)

    @api_method
    def archive_verify_integrity(self, params: dict[str, Any]) -> dict[str, Any]:
        # Verify bundle integrity and tamper resistance.
        require(params, "bundle_path", "password")
        valid, err = verify_bundle_integrity(str(params["bundle_path"]), str(params["password"]))
        return ok(valid=valid, error=err)

    @api_method
    def archive_rotate_key(self, params: dict[str, Any]) -> dict[str, Any]:
        # Re-encrypt bundle with new password.
        require(params, "bundle_path", "old_password", "new_password")
        rotate_bundle_key(str(params["bundle_path"]), str(params["old_password"]), str(params["new_password"]))
        return ok(rotated=True)

    @api_method
    def archive_snapshot(self, params: dict[str, Any]) -> dict[str, Any]:
        # Take filesystem snapshot of directory tree.
        require(params, "directory_path")
        snap = snapshot_directory(str(params["directory_path"]))
        return ok(snapshot=snap)

    @api_method
    def archive_compare_snapshots(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compare two directory snapshots for incremental backup.
        require(params, "old_snapshot", "new_snapshot")
        added, modified, removed = compare_directory_snapshots(dict(params["old_snapshot"]), dict(params["new_snapshot"]))
        return ok(added=added, modified=modified, removed=removed)

    @api_method
    def archive_incremental_backup(self, params: dict[str, Any]) -> dict[str, Any]:
        # Create incremental backup archive based on changed files.
        require(params, "directory_path", "previous_snapshot", "output_path")
        arch_p, new_snap = create_incremental_backup(
            str(params["directory_path"]),
            dict(params["previous_snapshot"]),
            str(params["output_path"]),
        )
        return ok(archive_path=arch_p, new_snapshot=new_snap)
