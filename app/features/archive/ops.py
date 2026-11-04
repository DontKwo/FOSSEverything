"""Archive helpers for creating and extracting ZIP/TAR bundles locally."""
from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import os
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any

def compute_file_sha256(path: str) -> str:
    # Compute SHA-256 digest of file for archive verification.
    hasher = hashlib.sha256()
    with open(path, "rb") as stream:
        while chunk := stream.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def archive_format_for_path(path: str) -> str:
    # Return the archive format implied by a filename.
    lower = path.lower()
    if lower.endswith(".tar.gz") or lower.endswith(".tgz"):
        return "tar.gz"
    if lower.endswith(".tar.xz") or lower.endswith(".txz"):
        return "tar.xz"
    if lower.endswith(".tar.bz2") or lower.endswith(".tbz2"):
        return "tar.bz2"
    if lower.endswith(".tar"):
        return "tar"
    if lower.endswith(".zip"):
        return "zip"
    if lower.endswith(".fossbundle") or lower.endswith(".enc"):
        return "fossbundle"
    if lower.endswith(".gz"):
        return "tar.gz"
    if lower.endswith(".xz"):
        return "tar.xz"
    if lower.endswith(".bz2"):
        return "tar.bz2"
    raise ValueError(f"Unsupported archive extension for: {path}")


def _resolve_safe_member_path(dest_root: Path, member_name: str) -> Path:
    # Reject archive entries that escape dest_root via .. or absolute roots.
    candidate = (dest_root / member_name.lstrip("/\\")).resolve()
    if candidate != dest_root and not candidate.is_relative_to(dest_root):
        raise ValueError(f"Unsafe archive member path blocked: {member_name}")
    return candidate


def create_archive(source_path: str, output_path: str, archive_format: str | None = None) -> str:
    # Create a ZIP or TAR archive from a file or directory.
    source_path = os.path.abspath(source_path)
    output_path = os.path.abspath(output_path)
    fmt = (archive_format or archive_format_for_path(output_path)).lower()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if fmt == "zip":
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            if os.path.isdir(source_path):
                parent = os.path.dirname(source_path) or os.getcwd()
                for root, _, files in os.walk(source_path):
                    for file_name in files:
                        full = os.path.join(root, file_name)
                        arc_name = os.path.relpath(full, parent)
                        zip_file.write(full, arcname=arc_name)
            else:
                zip_file.write(source_path, arcname=os.path.basename(source_path))
    elif fmt in ("tar", "tar.gz", "tar.xz", "tar.bz2"):
        mode_map = {"tar": "w", "tar.gz": "w:gz", "tar.xz": "w:xz", "tar.bz2": "w:bz2"}
        mode = mode_map.get(fmt, "w")
        with tarfile.open(output_path, mode) as tar_file:
            tar_file.add(source_path, arcname=os.path.basename(source_path))
    else:
        raise ValueError(f"Unsupported archive format: {fmt}")

    return output_path


def create_multi_source_archive(
    sources: list[str],
    output_path: str,
    fmt: str = "zip",
    compression_level: int = 6,
) -> str:
    # Create archive directly from multiple source files and directories without temp staging.
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fmt_clean = fmt.lower().lstrip(".")

    if fmt_clean == "zip":
        comp = zipfile.ZIP_STORED if compression_level == 0 else zipfile.ZIP_DEFLATED
        kwargs: dict[str, Any] = {"compression": comp}
        if comp == zipfile.ZIP_DEFLATED:
            kwargs["compresslevel"] = compression_level
        with zipfile.ZipFile(output_path, "w", **kwargs) as zip_file:
            for source_entry in sources:
                src_path = Path(source_entry).resolve()
                if not src_path.exists():
                    continue
                if src_path.is_file():
                    zip_file.write(src_path, arcname=src_path.name)
                elif src_path.is_dir():
                    for item in sorted(src_path.rglob("*")):
                        arc = str(src_path.name / item.relative_to(src_path)).replace("\\", "/")
                        zip_file.write(item, arcname=arc)
    elif fmt_clean in ("tar", "tar.gz", "tar.xz", "tar.bz2"):
        mode_map = {
            "tar": "w:",
            "tar.gz": "w:gz",
            "tar.xz": "w:xz",
            "tar.bz2": "w:bz2",
        }
        tar_mode = mode_map.get(fmt_clean, "w:")
        tar_kwargs: dict[str, Any] = {}
        if fmt_clean == "tar.gz" and compression_level in (0, 6, 9):
            tar_kwargs["compresslevel"] = compression_level
        with tarfile.open(output_path, tar_mode, **tar_kwargs) as tar_file:
            for source_entry in sources:
                src_path = Path(source_entry).resolve()
                if not src_path.exists():
                    continue
                tar_file.add(src_path, arcname=src_path.name)
    else:
        raise ValueError(f"Unsupported archive format: {fmt_clean}")
    return output_path


def list_archive_contents(archive_path: str) -> list[str]:
    # Return a list of member names in the archive.
    archive_path = os.path.abspath(archive_path)
    lower = archive_path.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zip_file:
            return zip_file.namelist()
    if lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz2", ".gz", ".xz", ".bz2")):
        with tarfile.open(archive_path, "r:*") as tar_file:
            return tar_file.getnames()
    raise ValueError(f"Unsupported archive type: {archive_path}")


def inspect_archive_members(archive_path: str) -> list[dict[str, Any]]:
    # Return rich inspection data for all members in an archive.
    archive_path = os.path.abspath(archive_path)
    lower = archive_path.lower()
    results: list[dict[str, Any]] = []

    if lower.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zip_file:
            for info in zip_file.infolist():
                size = int(info.file_size)
                csize = int(info.compress_size)
                ratio = round((1.0 - (csize / size)) * 100, 1) if size > 0 else 0.0
                dt_str = datetime.datetime(*info.date_time).isoformat()
                results.append({
                    "path": info.filename,
                    "is_dir": info.is_dir(),
                    "size_bytes": size,
                    "compressed_bytes": csize,
                    "ratio_pct": ratio,
                    "modified_iso": dt_str,
                })
    elif lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz2", ".gz", ".xz", ".bz2")):
        with tarfile.open(archive_path, "r:*") as tar_file:
            for member in tar_file.getmembers():
                size = int(member.size)
                dt_str = datetime.datetime.fromtimestamp(member.mtime, tz=datetime.timezone.utc).isoformat()
                results.append({
                    "path": member.name,
                    "is_dir": member.isdir(),
                    "size_bytes": size,
                    "compressed_bytes": size,
                    "ratio_pct": 0.0,
                    "modified_iso": dt_str,
                })
    else:
        raise ValueError(f"Unsupported archive type: {archive_path}")
    return results


def extract_archive(archive_path: str, destination_dir: str) -> list[str]:
    # Extract an archive safely to a destination directory and return written file paths.
    archive_path = os.path.abspath(archive_path)
    destination_dir = os.path.abspath(destination_dir)
    os.makedirs(destination_dir, exist_ok=True)
    dest_path = Path(destination_dir).resolve()

    extracted: list[str] = []
    lower = archive_path.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zip_file:
            for info in zip_file.infolist():
                target_p = _resolve_safe_member_path(dest_path, info.filename)
                if info.is_dir():
                    target_p.mkdir(parents=True, exist_ok=True)
                else:
                    target_p.parent.mkdir(parents=True, exist_ok=True)
                    with zip_file.open(info) as src, open(target_p, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    extracted.append(str(target_p))
    elif lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz2", ".gz", ".xz", ".bz2")):
        with tarfile.open(archive_path, "r:*") as tar_file:
            for member in tar_file.getmembers():
                target_p = _resolve_safe_member_path(dest_path, member.name)
                if member.issym() or member.islnk():
                    link_target = (dest_path / member.linkname).resolve()
                    if not link_target.is_relative_to(dest_path):
                        raise ValueError(f"Unsafe archive link target blocked: {member.linkname}")
                if member.isdir():
                    target_p.mkdir(parents=True, exist_ok=True)
                else:
                    target_p.parent.mkdir(parents=True, exist_ok=True)
                    fobj = tar_file.extractfile(member)
                    if fobj is not None:
                        with fobj, open(target_p, "wb") as dst:
                            shutil.copyfileobj(fobj, dst)
                        extracted.append(str(target_p))
    else:
        raise ValueError(f"Unsupported archive type: {archive_path}")

    return extracted


def extract_selected_members(archive_path: str, members: list[str], output_dir: str) -> list[str]:
    # Extract specific archive members safely.
    archive_path = os.path.abspath(archive_path)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    dest_path = Path(output_dir).resolve()
    member_set = set(members)
    extracted: list[str] = []

    lower = archive_path.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zip_file:
            for info in zip_file.infolist():
                if info.filename in member_set:
                    target_p = _resolve_safe_member_path(dest_path, info.filename)
                    if info.is_dir():
                        target_p.mkdir(parents=True, exist_ok=True)
                    else:
                        target_p.parent.mkdir(parents=True, exist_ok=True)
                        with zip_file.open(info) as src, open(target_p, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        extracted.append(str(target_p))
    elif lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz2", ".gz", ".xz", ".bz2")):
        with tarfile.open(archive_path, "r:*") as tar_file:
            for member in tar_file.getmembers():
                if member.name in member_set:
                    target_p = _resolve_safe_member_path(dest_path, member.name)
                    if member.isdir():
                        target_p.mkdir(parents=True, exist_ok=True)
                    else:
                        target_p.parent.mkdir(parents=True, exist_ok=True)
                        fobj = tar_file.extractfile(member)
                        if fobj is not None:
                            with fobj, open(target_p, "wb") as dst:
                                shutil.copyfileobj(fobj, dst)
                            extracted.append(str(target_p))
    else:
        raise ValueError(f"Unsupported archive type: {archive_path}")

    return extracted


def convert_archive_format(input_path: str, output_path: str, archive_format: str | None = None, overwrite: bool = False) -> str:
    # Convert ZIP/TAR bundles into another supported local archive format.
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)
    fmt = (archive_format or archive_format_for_path(output_path)).lower().lstrip(".")
    if fmt in ("tgz", "gz"):
        fmt = "tar.gz"
    elif fmt in ("txz", "xz"):
        fmt = "tar.xz"
    elif fmt in ("tbz2", "bz2"):
        fmt = "tar.bz2"
    if fmt not in {"zip", "tar", "tar.gz", "tar.xz", "tar.bz2"}:
        raise ValueError(f"Unsupported archive output format: {archive_format or output_path}")
    if os.path.exists(output_path) and not overwrite:
        raise FileExistsError(f"Output archive already exists: {output_path}")

    temp_dir = tempfile.mkdtemp(prefix="archive_convert_")
    try:
        if os.path.isdir(input_path):
            source_dir = input_path
        else:
            source_root = os.path.join(temp_dir, "source")
            os.makedirs(source_root, exist_ok=True)
            extracted = extract_archive(input_path, source_root)
            if not extracted:
                raise ValueError(f"No files were extracted from archive: {input_path}")
            source_dir = source_root
        items = [os.path.join(source_dir, item) for item in os.listdir(source_dir)]
        create_multi_source_archive(items, output_path, fmt=fmt)
        return output_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _xor_stream_key(key: bytes, length: int) -> bytes:
    # Generate a deterministic keystream derived from a password and a counter.
    blocks = bytearray()
    counter = 0
    while len(blocks) < length:
        blocks.extend(hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha256).digest())
        counter += 1
    return bytes(blocks[:length])


def create_password_protected_bundle(source_path: str, output_path: str, password: str, archive_format: str = "zip") -> str:
    # Create an encrypted local bundle around a ZIP or TAR archive using a password-derived XOR stream.
    source_path = os.path.abspath(source_path)
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    code_map = {
        "zip": b"0",
        "tar.gz": b"1",
        "tar": b"2",
        "tar.xz": b"3",
        "tar.bz2": b"4",
    }
    fmt = archive_format.lower().lstrip(".")
    if fmt in ("tgz", "gz"):
        fmt = "tar.gz"
    elif fmt in ("txz", "xz"):
        fmt = "tar.xz"
    elif fmt in ("tbz2", "bz2"):
        fmt = "tar.bz2"
    archive_code = code_map.get(fmt, b"0")

    temp_archive = tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False)
    temp_archive.close()
    try:
        create_multi_source_archive([source_path], temp_archive.name, fmt=fmt)
        with open(temp_archive.name, "rb") as file_handle:
            archive_bytes = file_handle.read()

        salt = os.urandom(16)
        nonce = os.urandom(16)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt + nonce + archive_code, 200_000, dklen=32)
        keystream = _xor_stream_key(key, len(archive_bytes))
        encrypted = bytes([byte_val ^ key_val for byte_val, key_val in zip(archive_bytes, keystream)])

        with open(output_path, "wb") as file_handle:
            file_handle.write(salt)
            file_handle.write(nonce)
            file_handle.write(archive_code)
            file_handle.write(encrypted)
        return output_path
    finally:
        if os.path.exists(temp_archive.name):
            os.unlink(temp_archive.name)


def extract_password_protected_bundle(bundle_path: str, destination_dir: str, password: str) -> list[str]:
    # Decrypt and extract a local password-protected bundle created by create_password_protected_bundle.
    bundle_path = os.path.abspath(bundle_path)
    destination_dir = os.path.abspath(destination_dir)
    os.makedirs(destination_dir, exist_ok=True)
    dest_path = Path(destination_dir).resolve()

    with open(bundle_path, "rb") as file_handle:
        payload = file_handle.read()
    if len(payload) < 33:
        raise ValueError("Encrypted bundle is too short to be valid.")

    salt = payload[:16]
    nonce = payload[16:32]
    archive_code = payload[32:33]
    encrypted = payload[33:]
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt + nonce + archive_code, 200_000, dklen=32)
    keystream = _xor_stream_key(key, len(encrypted))
    archive_bytes = bytes([byte_val ^ key_val for byte_val, key_val in zip(encrypted, keystream)])

    temp_archive = tempfile.NamedTemporaryFile(suffix=".bin", delete=False)
    temp_archive.close()
    extracted: list[str] = []
    try:
        with open(temp_archive.name, "wb") as file_handle:
            file_handle.write(archive_bytes)

        if archive_code == b"0":
            with zipfile.ZipFile(temp_archive.name, "r") as zip_file:
                for info in zip_file.infolist():
                    target_p = _resolve_safe_member_path(dest_path, info.filename)
                    if info.is_dir():
                        target_p.mkdir(parents=True, exist_ok=True)
                    else:
                        target_p.parent.mkdir(parents=True, exist_ok=True)
                        with zip_file.open(info) as src, open(target_p, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        extracted.append(str(target_p))
        else:
            mode_map = {
                b"1": "r:gz",
                b"2": "r:",
                b"3": "r:xz",
                b"4": "r:bz2",
            }
            open_mode = mode_map.get(archive_code, "r:*")
            with tarfile.open(temp_archive.name, open_mode) as tar_file:
                for member in tar_file.getmembers():
                    target_p = _resolve_safe_member_path(dest_path, member.name)
                    if member.isdir():
                        target_p.mkdir(parents=True, exist_ok=True)
                    else:
                        target_p.parent.mkdir(parents=True, exist_ok=True)
                        fobj = tar_file.extractfile(member)
                        if fobj is not None:
                            with fobj, open(target_p, "wb") as dst:
                                shutil.copyfileobj(fobj, dst)
                            extracted.append(str(target_p))
        return extracted
    finally:
        if os.path.exists(temp_archive.name):
            os.unlink(temp_archive.name)


def snapshot_directory(source_dir: str, manifest_path: str | None = None) -> dict[str, Any]:
    # Create a hash manifest for an entire directory tree for later diffing/backups.
    source_dir = os.path.abspath(source_dir)
    files: dict[str, dict[str, Any]] = {}
    for root, _, filenames in os.walk(source_dir):
        for filename in sorted(filenames):
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, source_dir).replace("\\", "/")
            files[rel_path] = {"size": os.path.getsize(full_path), "sha256": compute_file_sha256(full_path)}

    snapshot = {"root": source_dir, "files": files}
    if manifest_path:
        os.makedirs(os.path.dirname(manifest_path) or ".", exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as file_handle:
            json.dump(snapshot, file_handle, indent=2, sort_keys=True)
    return snapshot


def compare_directory_snapshots(previous_snapshot: dict[str, Any], current_snapshot: dict[str, Any]) -> dict[str, Any]:
    # Compare two directory snapshots and classify changes by relative path.
    prev_files = previous_snapshot.get("files", {})
    curr_files = current_snapshot.get("files", {})
    all_paths = sorted(set(prev_files) | set(curr_files))
    added: list[str] = []
    removed: list[str] = []
    changed: list[str] = []
    unchanged: list[str] = []

    for rel_path in all_paths:
        prev_entry = prev_files.get(rel_path)
        curr_entry = curr_files.get(rel_path)
        if prev_entry is None:
            added.append(rel_path)
        elif curr_entry is None:
            removed.append(rel_path)
        elif prev_entry.get("sha256") != curr_entry.get("sha256") or prev_entry.get("size") != curr_entry.get("size"):
            changed.append(rel_path)
        else:
            unchanged.append(rel_path)

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
        "total_changed": len(added) + len(removed) + len(changed),
    }


def create_incremental_backup(
    source_dir: str,
    backup_dir: str,
    manifest_name: str = "snapshot.json",
    archive_name: str | None = None,
    archive_format: str = "zip",
) -> dict[str, Any]:
    # Create a backup archive containing only files that changed since the last snapshot.
    source_dir = os.path.abspath(source_dir)
    backup_dir = os.path.abspath(backup_dir)
    os.makedirs(backup_dir, exist_ok=True)

    manifest_path = os.path.join(backup_dir, manifest_name)
    current_snapshot = snapshot_directory(source_dir)
    previous_snapshot: dict[str, Any] = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as file_handle:
            previous_snapshot = json.load(file_handle)

    diff = compare_directory_snapshots(previous_snapshot, current_snapshot)
    changed_paths = diff["added"] + diff["changed"]

    temp_dir = tempfile.mkdtemp(prefix="backup_snapshot_")
    try:
        for rel_path in changed_paths:
            src_file = os.path.join(source_dir, rel_path)
            dst_file = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
            shutil.copy2(src_file, dst_file)

        archive_name = archive_name or f"{os.path.basename(source_dir)}_incremental_{len(changed_paths)}_files_{archive_format}.zip"
        archive_path = os.path.join(backup_dir, archive_name)
        if archive_format.lower() == "zip":
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
                for root, _, files in os.walk(temp_dir):
                    for file_name in sorted(files):
                        full_path = os.path.join(root, file_name)
                        rel = os.path.relpath(full_path, temp_dir).replace("\\", "/")
                        zip_file.write(full_path, arcname=rel)
        else:
            with tarfile.open(archive_path, "w:gz") as tar_file:
                for root, _, files in os.walk(temp_dir):
                    for file_name in sorted(files):
                        full_path = os.path.join(root, file_name)
                        rel = os.path.relpath(full_path, temp_dir).replace("\\", "/")
                        tar_file.add(full_path, arcname=rel)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    with open(manifest_path, "w", encoding="utf-8") as file_handle:
        json.dump(current_snapshot, file_handle, indent=2, sort_keys=True)

    return {
        "archive_path": archive_path,
        "manifest_path": manifest_path,
        "files": changed_paths,
        "total_files": len(changed_paths),
        "diff": diff,
    }


def verify_bundle_integrity(bundle_path: str, password: str | None = None) -> dict[str, Any]:
    # Verify a bundle and report each member hash plus overall validity.
    bundle_path = os.path.abspath(bundle_path)
    temp_dir = tempfile.mkdtemp(prefix="bundle_verify_")
    try:
        if password is not None:
            extracted = extract_password_protected_bundle(bundle_path, temp_dir, password)
        else:
            extracted = [bundle_path]
        entries: list[dict[str, Any]] = []
        for path in extracted:
            if os.path.isdir(path):
                for root, _, filenames in os.walk(path):
                    for filename in sorted(filenames):
                        full = os.path.join(root, filename)
                        rel = os.path.relpath(full, path).replace("\\", "/")
                        entries.append({"path": rel, "size": os.path.getsize(full), "sha256": compute_file_sha256(full)})
            elif os.path.isfile(path):
                entries.append({"path": os.path.basename(path), "size": os.path.getsize(path), "sha256": compute_file_sha256(path)})
        return {"valid": bool(entries), "entries": entries, "issue_count": 0}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def rotate_bundle_key(bundle_path: str, old_password: str, new_password: str, output_path: str | None = None) -> str:
    # Re-encrypt a bundle with a new password while keeping the same payload contents.
    bundle_path = os.path.abspath(bundle_path)
    alt_output = output_path or os.path.splitext(bundle_path)[0] + "_rotated.enc"
    temp_dir = tempfile.mkdtemp(prefix="bundle_rotate_")
    try:
        extracted = extract_password_protected_bundle(bundle_path, temp_dir, old_password)
        if not extracted:
            raise ValueError("No files were extracted from the supplied bundle.")
        created = create_password_protected_bundle(temp_dir, alt_output, new_password)
        return created
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_archive(archive_path: str) -> dict[str, Any]:
    # Test archive integrity and return entry count or error details.
    archive_path = os.path.abspath(archive_path)
    lower = archive_path.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zip_file:
            bad_file = zip_file.testzip()
            if bad_file:
                return {"valid": False, "error": f"Corrupt entry in archive: {bad_file}"}
            return {"valid": True, "count": len(zip_file.infolist())}
    if lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz2", ".gz", ".xz", ".bz2")):
        with tarfile.open(archive_path, "r:*") as tar_file:
            members = tar_file.getmembers()
            for member in members:
                if member.isfile():
                    extracted_file = tar_file.extractfile(member)
                    if extracted_file:
                        while extracted_file.read(65536):
                            pass
            return {"valid": True, "count": len(members)}
    return verify_bundle_integrity(archive_path)
