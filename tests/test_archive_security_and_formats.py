from __future__ import annotations

import io
import os
import tarfile
import zipfile
from pathlib import Path

import pytest

from app.features.archive.ops import (
    create_multi_source_archive,
    create_password_protected_bundle,
    extract_archive,
    extract_password_protected_bundle,
    inspect_archive_members,
)


def test_zip_slip_rejected(tmp_path: Path) -> None:
    # Verify Zip-Slip path traversal attack is blocked.
    evil_zip = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil_zip, "w") as zip_file:
        zip_file.writestr("../../evil.txt", "pwned")

    dest_dir = tmp_path / "extracted"
    with pytest.raises(ValueError, match="Unsafe archive member path blocked"):
        extract_archive(str(evil_zip), str(dest_dir))


def test_tar_slip_rejected(tmp_path: Path) -> None:
    # Verify Tar-Slip path traversal attack is blocked.
    evil_tar = tmp_path / "evil.tar"
    with tarfile.open(evil_tar, "w") as tar_file:
        info = tarfile.TarInfo(name="../../evil.txt")
        info.size = 5
        tar_file.addfile(info, io.BytesIO(b"pwned"))

    dest_dir = tmp_path / "extracted_tar"
    with pytest.raises(ValueError, match="Unsafe archive member path blocked"):
        extract_archive(str(evil_tar), str(dest_dir))


@pytest.mark.parametrize("fmt", ["zip", "tar", "tar.gz", "tar.xz"])
def test_password_protected_bundle_roundtrip(tmp_path: Path, fmt: str) -> None:
    # Verify password bundles round-trip across formats.
    source_file = tmp_path / f"secret_{fmt}.txt"
    source_file.write_text(f"confidential content for {fmt}", encoding="utf-8")

    bundle_path = tmp_path / f"bundle_{fmt}.fossbundle"
    password = "CorrectHorseBatteryStaple123!"

    created = create_password_protected_bundle(str(source_file), str(bundle_path), password, archive_format=fmt)
    assert os.path.exists(created)
    assert os.path.getsize(created) > 0

    dest_dir = tmp_path / f"decrypted_{fmt}"
    extracted = extract_password_protected_bundle(str(bundle_path), str(dest_dir), password)
    assert len(extracted) > 0

    recovered_file = dest_dir / source_file.name
    assert recovered_file.exists()
    assert recovered_file.read_text(encoding="utf-8") == f"confidential content for {fmt}"


def test_multi_source_archive_flat_root(tmp_path: Path) -> None:
    # Verify multi-source archiving creates flat root entries without wrapper directory.
    file_a = tmp_path / "doc_a.txt"
    file_a.write_text("Hello A", encoding="utf-8")

    sub_dir = tmp_path / "sub_folder"
    sub_dir.mkdir()
    file_b = sub_dir / "nested.txt"
    file_b.write_text("Nested content", encoding="utf-8")

    out_zip = tmp_path / "flat_output.zip"
    create_multi_source_archive([str(file_a), str(sub_dir)], str(out_zip), fmt="zip")

    members = inspect_archive_members(str(out_zip))
    member_paths = [m["path"] for m in members]

    assert "doc_a.txt" in member_paths
    assert any(p.startswith("sub_folder/nested.txt") for p in member_paths)
    assert not any("archive_src_" in p for p in member_paths)

