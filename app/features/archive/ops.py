"""Archive helpers for creating and extracting ZIP/TAR bundles locally."""
from __future__ import annotations

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

from app.features.hash.ops import hash_file


def archive_format_for_path(path: str) -> str:
    """Return the archive format implied by a filename."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".zip",):
        return "zip"
    if ext in (".tar",):
        return "tar"
    if ext in (".tgz", ".gz"):
        return "tar.gz"
    raise ValueError(f"Unsupported archive extension for: {path}")


def create_archive(source_path: str, output_path: str, archive_format: str | None = None) -> str:
    """Create a ZIP or TAR archive from a file or directory."""
    source_path = os.path.abspath(source_path)
    output_path = os.path.abspath(output_path)
    fmt = (archive_format or archive_format_for_path(output_path)).lower()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if fmt == "zip":
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            if os.path.isdir(source_path):
                parent = os.path.dirname(source_path) or os.getcwd()
                for root, _, files in os.walk(source_path):
                    for file_name in files:
                        full = os.path.join(root, file_name)
                        arc_name = os.path.relpath(full, parent)
                        zf.write(full, arcname=arc_name)
            else:
                zf.write(source_path, arcname=os.path.basename(source_path))
    elif fmt in ("tar", "tar.gz"):
        mode = "w:gz" if fmt == "tar.gz" else "w"
        with tarfile.open(output_path, mode) as tf:
            if os.path.isdir(source_path):
                tf.add(source_path, arcname=os.path.basename(source_path))
            else:
                tf.add(source_path, arcname=os.path.basename(source_path))
    else:
        raise ValueError(f"Unsupported archive format: {fmt}")

    return output_path


def list_archive_contents(archive_path: str) -> list[str]:
    """Return a list of member names in the archive."""
    archive_path = os.path.abspath(archive_path)
    ext = os.path.splitext(archive_path)[1].lower()
    if ext == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zf:
            return zf.namelist()
    if ext in (".tar", ".gz", ".tgz"):
        mode = "r:gz" if ext in (".gz", ".tgz") else "r"
        with tarfile.open(archive_path, mode) as tf:
            return tf.getnames()
    raise ValueError(f"Unsupported archive type: {archive_path}")


def extract_archive(archive_path: str, destination_dir: str) -> list[str]:
    """Extract an archive to a destination directory and return written file paths."""
    archive_path = os.path.abspath(archive_path)
    destination_dir = os.path.abspath(destination_dir)
    os.makedirs(destination_dir, exist_ok=True)

    extracted: list[str] = []
    ext = os.path.splitext(archive_path)[1].lower()
    if ext == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(destination_dir)
            for name in zf.namelist():
                target = os.path.join(destination_dir, name)
                if os.path.exists(target):
                    extracted.append(target)
    elif ext in (".tar", ".gz", ".tgz"):
        mode = "r:gz" if ext in (".gz", ".tgz") else "r"
        with tarfile.open(archive_path, mode) as tf:
            tf.extractall(destination_dir)
            for member in tf.getmembers():
                target = os.path.join(destination_dir, member.name)
                if os.path.exists(target):
                    extracted.append(target)
    else:
        raise ValueError(f"Unsupported archive type: {archive_path}")

    return extracted


def convert_archive_format(input_path: str, output_path: str, archive_format: str | None = None, overwrite: bool = False) -> str:
    """Convert ZIP/TAR bundles into another supported local archive format."""
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)
    fmt = (archive_format or os.path.splitext(output_path)[1]).lower().lstrip(".")
    if not fmt:
        fmt = "zip"
    if fmt == "tar.gz":
        fmt = "tar.gz"
    if fmt not in {"zip", "tar", "tar.gz"}:
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
            child_dirs = [os.path.join(source_root, name) for name in os.listdir(source_root) if os.path.isdir(os.path.join(source_root, name))]
            source_dir = child_dirs[0] if len(child_dirs) == 1 else source_root
        create_archive(source_dir, output_path, archive_format=fmt)
        return output_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _xor_stream_key(key: bytes, length: int) -> bytes:
    """Generate a deterministic keystream derived from a password and a counter."""
    blocks = bytearray()
    counter = 0
    while len(blocks) < length:
        blocks.extend(hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha256).digest())
        counter += 1
    return bytes(blocks[:length])


def create_password_protected_bundle(source_path: str, output_path: str, password: str, archive_format: str = "zip") -> str:
    """Create an encrypted local bundle around a ZIP or TAR archive using a password-derived XOR stream."""
    source_path = os.path.abspath(source_path)
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    temp_archive = tempfile.NamedTemporaryFile(suffix=f".{archive_format.lower()}", delete=False)
    temp_archive.close()
    try:
        create_archive(source_path, temp_archive.name, archive_format=archive_format)
        with open(temp_archive.name, "rb") as fh:
            archive_bytes = fh.read()

        salt = os.urandom(16)
        nonce = os.urandom(16)
        archive_code = b"1" if archive_format.lower() in ("tar", "tar.gz") else b"0"
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt + nonce + archive_code, 200_000, dklen=32)
        keystream = _xor_stream_key(key, len(archive_bytes))
        encrypted = bytes([b ^ k for b, k in zip(archive_bytes, keystream)])

        with open(output_path, "wb") as fh:
            fh.write(salt)
            fh.write(nonce)
            fh.write(archive_code)
            fh.write(encrypted)
        return output_path
    finally:
        if os.path.exists(temp_archive.name):
            os.unlink(temp_archive.name)


def extract_password_protected_bundle(bundle_path: str, destination_dir: str, password: str) -> list[str]:
    """Decrypt and extract a local password-protected bundle created by create_password_protected_bundle."""
    bundle_path = os.path.abspath(bundle_path)
    destination_dir = os.path.abspath(destination_dir)
    os.makedirs(destination_dir, exist_ok=True)

    with open(bundle_path, "rb") as fh:
        payload = fh.read()
    if len(payload) < 33:
        raise ValueError("Encrypted bundle is too short to be valid.")

    salt = payload[:16]
    nonce = payload[16:32]
    archive_code = payload[32:33]
    encrypted = payload[33:]
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt + nonce + archive_code, 200_000, dklen=32)
    keystream = _xor_stream_key(key, len(encrypted))
    archive_bytes = bytes([b ^ k for b, k in zip(encrypted, keystream)])

    archive_format = "zip" if archive_code == b"0" else "tar"

    temp_archive = tempfile.NamedTemporaryFile(suffix=".bin", delete=False)
    temp_archive.close()
    try:
        with open(temp_archive.name, "wb") as fh:
            fh.write(archive_bytes)
        if archive_format == "zip":
            with zipfile.ZipFile(temp_archive.name, "r") as zf:
                zf.extractall(destination_dir)
                return [os.path.join(destination_dir, name) for name in zf.namelist() if os.path.exists(os.path.join(destination_dir, name))]
        with tarfile.open(temp_archive.name, "r:gz") as tf:
            tf.extractall(destination_dir)
            return [os.path.join(destination_dir, member.name) for member in tf.getmembers() if os.path.exists(os.path.join(destination_dir, member.name))]
    finally:
        if os.path.exists(temp_archive.name):
            os.unlink(temp_archive.name)


def snapshot_directory(source_dir: str, manifest_path: str | None = None) -> dict:
    """Create a hash manifest for an entire directory tree for later diffing/backups."""
    source_dir = os.path.abspath(source_dir)
    files: dict[str, dict] = {}
    for root, _, filenames in os.walk(source_dir):
        for filename in sorted(filenames):
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, source_dir).replace("\\", "/")
            files[rel_path] = {"size": os.path.getsize(full_path), "sha256": hash_file(full_path, "sha256")}

    snapshot = {"root": source_dir, "files": files}
    if manifest_path:
        os.makedirs(os.path.dirname(manifest_path) or ".", exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh, indent=2, sort_keys=True)
    return snapshot


def compare_directory_snapshots(previous_snapshot: dict, current_snapshot: dict) -> dict:
    """Compare two directory snapshots and classify changes by relative path."""
    prev_files = previous_snapshot.get("files", {})
    curr_files = current_snapshot.get("files", {})
    all_paths = sorted(set(prev_files) | set(curr_files))
    added = []
    removed = []
    changed = []
    unchanged = []

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


def create_incremental_backup(source_dir: str, backup_dir: str, manifest_name: str = "snapshot.json", archive_name: str | None = None, archive_format: str = "zip") -> dict:
    """Create a backup archive containing only files that changed since the last snapshot."""
    source_dir = os.path.abspath(source_dir)
    backup_dir = os.path.abspath(backup_dir)
    os.makedirs(backup_dir, exist_ok=True)

    manifest_path = os.path.join(backup_dir, manifest_name)
    current_snapshot = snapshot_directory(source_dir)
    previous_snapshot = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as fh:
            previous_snapshot = json.load(fh)

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
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(temp_dir):
                    for file_name in sorted(files):
                        full_path = os.path.join(root, file_name)
                        rel = os.path.relpath(full_path, temp_dir).replace("\\", "/")
                        zf.write(full_path, arcname=rel)
        else:
            with tarfile.open(archive_path, "w:gz") as tf:
                for root, _, files in os.walk(temp_dir):
                    for file_name in sorted(files):
                        full_path = os.path.join(root, file_name)
                        rel = os.path.relpath(full_path, temp_dir).replace("\\", "/")
                        tf.add(full_path, arcname=rel)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(current_snapshot, fh, indent=2, sort_keys=True)

    return {
        "archive_path": archive_path,
        "manifest_path": manifest_path,
        "files": changed_paths,
        "total_files": len(changed_paths),
        "diff": diff,
    }


def verify_bundle_integrity(bundle_path: str, password: str | None = None) -> dict:
    """Verify a bundle and report each member hash plus overall validity."""
    bundle_path = os.path.abspath(bundle_path)
    temp_dir = tempfile.mkdtemp(prefix="bundle_verify_")
    try:
        if password is not None:
            extracted = extract_password_protected_bundle(bundle_path, temp_dir, password)
        else:
            extracted = [bundle_path]
        entries = []
        for path in extracted:
            if os.path.isdir(path):
                for root, _, filenames in os.walk(path):
                    for filename in sorted(filenames):
                        full = os.path.join(root, filename)
                        rel = os.path.relpath(full, path).replace("\\", "/")
                        entries.append({"path": rel, "size": os.path.getsize(full), "sha256": hash_file(full, "sha256")})
            elif os.path.isfile(path):
                entries.append({"path": os.path.basename(path), "size": os.path.getsize(path), "sha256": hash_file(path, "sha256")})
        return {"valid": bool(entries), "entries": entries, "issue_count": 0}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def rotate_bundle_key(bundle_path: str, old_password: str, new_password: str, output_path: str | None = None) -> str:
    """Re-encrypt a bundle with a new password while keeping the same payload contents."""
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
    """Test archive integrity and return entry count or error details."""
    archive_path = os.path.abspath(archive_path)
    ext = os.path.splitext(archive_path)[1].lower()
    if ext == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zf:
            bad_file = zf.testzip()
            if bad_file:
                return {"valid": False, "error": f"Corrupt entry in archive: {bad_file}"}
            return {"valid": True, "count": len(zf.infolist())}
    if ext in (".tar", ".gz", ".tgz"):
        mode = "r:gz" if ext in (".gz", ".tgz") else "r"
        with tarfile.open(archive_path, mode) as tf:
            members = tf.getmembers()
            for member in members:
                if member.isfile():
                    extracted_file = tf.extractfile(member)
                    if extracted_file:
                        while extracted_file.read(65536):
                            pass
            return {"valid": True, "count": len(members)}
    return verify_bundle_integrity(archive_path)
