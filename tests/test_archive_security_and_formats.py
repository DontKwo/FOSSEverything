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
    extract_archive_bounded,
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


def test_drive_letter_path_rejected(tmp_path: Path) -> None:
    # Verify archive member paths attempting drive letter escapes are blocked.
    evil_zip = tmp_path / "drive_evil.zip"
    with zipfile.ZipFile(evil_zip, "w") as zip_file:
        zip_file.writestr("C:evil.txt", "payload")

    dest_dir = tmp_path / "extracted_drive"
    with pytest.raises(ValueError, match="drive letter"):
        extract_archive(str(evil_zip), str(dest_dir))


def test_decompression_bomb_size_limit(tmp_path: Path) -> None:
    # Verify decompression bomb exceeding total bytes threshold is aborted.
    bomb_zip = tmp_path / "bomb.zip"
    with zipfile.ZipFile(bomb_zip, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("huge_sparse.txt", "A" * (200 * 1024))

    dest_dir = tmp_path / "extracted_bomb"
    with pytest.raises(ValueError, match="Archive decompression bomb detected"):
        extract_archive_bounded(str(bomb_zip), str(dest_dir), max_total_bytes=100 * 1024)
    assert not (dest_dir / "huge_sparse.txt").exists()


def test_member_count_limit_rejected(tmp_path: Path) -> None:
    # Verify archives exceeding allowed member count are rejected.
    many_zip = tmp_path / "many_files.zip"
    with zipfile.ZipFile(many_zip, "w") as zip_file:
        for idx in range(15):
            zip_file.writestr(f"item_{idx}.txt", f"data {idx}")

    dest_dir = tmp_path / "extracted_many"
    with pytest.raises(ValueError, match="maximum allowed member count"):
        extract_archive_bounded(str(many_zip), str(dest_dir), max_members=10)


def test_unsafe_tar_symlink_rejected(tmp_path: Path) -> None:
    # Verify tar archives with symlinks pointing outside target directory are blocked.
    evil_tar = tmp_path / "symlink_evil.tar"
    with tarfile.open(evil_tar, "w") as tar_file:
        link_info = tarfile.TarInfo(name="symlink_escape")
        link_info.type = tarfile.SYMTYPE
        link_info.linkname = "../../etc/passwd"
        tar_file.addfile(link_info)

    dest_dir = tmp_path / "extracted_symlink"
    with pytest.raises(ValueError, match="Unsafe archive link target blocked"):
        extract_archive(str(evil_tar), str(dest_dir))


