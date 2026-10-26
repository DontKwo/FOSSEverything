import os
import shutil
import tempfile
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
        # Compress files or folders into archive (zip, tar, tar.gz).
        require(params, "sources")
        sources = list(params["sources"])
        fmt = str(params.get("format", "zip")).lower()
        output_path = str(params.get("output_path", "")).strip()
        if not output_path and sources:
            base = os.path.splitext(str(sources[0]))[0]
            ext = ".tar.gz" if fmt in ("tar.gz", "tgz") else f".{fmt}"
            output_path = f"{base}_bundle{ext}"

        if len(sources) == 1:
            created = create_archive(str(sources[0]), output_path, archive_format=fmt)
        else:
            temp_dir = tempfile.mkdtemp(prefix="archive_src_")
            try:
                for s in sources:
                    dst = os.path.join(temp_dir, os.path.basename(s))
                    if os.path.isdir(s):
                        shutil.copytree(s, dst, dirs_exist_ok=True)
                    elif os.path.isfile(s):
                        shutil.copy2(s, dst)
                created = create_archive(temp_dir, output_path, archive_format=fmt)
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
        return ok(output_path=created)

    @api_method
    def archive_extract(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract files from archive to target folder.
        require(params, "archive_path")
        arch_path = str(params["archive_path"])
        target_dir = str(params.get("target_dir", "")).strip()
        if not target_dir:
            target_dir = os.path.splitext(arch_path)[0] + "_extracted"
        extracted = extract_archive(arch_path, target_dir)
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
        res = test_archive(arch_path)
        return ok(valid=res.get("valid", False), message=res.get("error", "Integrity check passed."), details=res)

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
        require(params, "source_paths", "password")
        sources = list(params["source_paths"])
        pw = str(params["password"])
        out_path = str(params.get("output_path", "")).strip()
        if not out_path and sources:
            out_path = os.path.splitext(str(sources[0]))[0] + "_protected.enc"
        fmt = str(params.get("format", "zip"))

        if len(sources) == 1:
            bundle_path = create_password_protected_bundle(str(sources[0]), out_path, pw, archive_format=fmt)
        else:
            temp_dir = tempfile.mkdtemp(prefix="bundle_src_")
            try:
                for s in sources:
                    dst = os.path.join(temp_dir, os.path.basename(s))
                    if os.path.isdir(s):
                        shutil.copytree(s, dst, dirs_exist_ok=True)
                    elif os.path.isfile(s):
                        shutil.copy2(s, dst)
                bundle_path = create_password_protected_bundle(temp_dir, out_path, pw, archive_format=fmt)
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
        return ok(output_path=bundle_path)

    @api_method
    def archive_unprotect(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract password-protected bundle.
        require(params, "bundle_path", "password")
        b_path = str(params["bundle_path"])
        target = str(params.get("target_dir", "")).strip()
        if not target:
            target = os.path.splitext(b_path)[0] + "_decrypted"
        pw = str(params["password"])
        extracted = extract_password_protected_bundle(b_path, target, pw)
        return ok(extracted=extracted, target_dir=target)

    @api_method
    def archive_verify_integrity(self, params: dict[str, Any]) -> dict[str, Any]:
        # Verify bundle integrity and tamper resistance.
        require(params, "bundle_path")
        b_path = str(params["bundle_path"])
        pw = params.get("password")
        res = verify_bundle_integrity(b_path, str(pw) if pw else None)
        return ok(valid=res.get("valid", False), entries=res.get("entries", []), error=res.get("error"))

    @api_method
    def archive_rotate_key(self, params: dict[str, Any]) -> dict[str, Any]:
        # Re-encrypt bundle with new password.
        require(params, "bundle_path", "old_password", "new_password")
        b_path = str(params["bundle_path"])
        old_pw = str(params["old_password"])
        new_pw = str(params["new_password"])
        out_p = params.get("output_path")
        rotated = rotate_bundle_key(b_path, old_pw, new_pw, str(out_p) if out_p else None)
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
        res = create_incremental_backup(src, backup_d, manifest_name=manifest_name, archive_format=fmt)
        return ok(
            archive_path=res["archive_path"],
            manifest_path=res["manifest_path"],
            files=res["files"],
            total_files=res["total_files"],
        )

    @api_method
    def archive_presets(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return predefined archive and backup policy presets.
        presets = [
            {
                "id": "photos",
                "name": "Personal Photos",
                "format": "zip",
                "encrypt": False,
                "description": "Standard ZIP container optimized for image collections.",
            },
            {
                "id": "code",
                "name": "Source Code",
                "format": "tar.gz",
                "encrypt": False,
                "description": "Compact TAR.GZ archive for project source trees.",
            },
            {
                "id": "sensitive",
                "name": "Sensitive Documents",
                "format": "zip",
                "encrypt": True,
                "description": "Password-protected encrypted bundle with key derivation.",
            },
            {
                "id": "media",
                "name": "Media Backup",
                "format": "tar",
                "encrypt": False,
                "description": "Uncompressed TAR bundle for fast multi-gigabyte media.",
            },
            {
                "id": "share",
                "name": "Quick Share",
                "format": "zip",
                "encrypt": False,
                "description": "Portable lightweight ZIP bundle for email or chat sharing.",
            },
            {
                "id": "longterm",
                "name": "Long-term Archive",
                "format": "tar.gz",
                "encrypt": False,
                "description": "Maximum compression TAR.GZ with manifest checksum tracking.",
            },
        ]
        return ok(presets=presets)
