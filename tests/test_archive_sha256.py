from __future__ import annotations

import hashlib
from pathlib import Path

from app.web.api import WebApi


def test_archive_checksums_and_verify_round_trip(tmp_path: Path) -> None:
    # Member and archive digests match hashlib and verification flags mismatches.
    api = WebApi()
    src = tmp_path / "note.txt"
    src.write_bytes(b"sha payload")
    out = tmp_path / "bundle.tar.gz"
    created = api.archive_create({"sources": [str(src)], "format": "tar.gz", "output_path": str(out), "compression_level": 9})
    assert created["ok"] is True
    assert created["sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()

    sums = api.archive_checksums({"archive_path": str(out)})
    assert sums["members"][0]["sha256"] == hashlib.sha256(b"sha payload").hexdigest()
    assert sums["archive_sha256"] == created["sha256"]

    good = api.archive_verify_sha256({"archive_path": str(out), "expected_sha256": created["sha256"].upper()})
    assert good["valid"] is True
    bad = api.archive_verify_sha256({"archive_path": str(out), "expected_sha256": "0" * 64})
    assert bad["valid"] is False


def test_archive_extract_rejects_wrong_digest(tmp_path: Path) -> None:
    # Extraction stops before writing files when the expected digest is wrong.
    api = WebApi()
    src = tmp_path / "a.txt"
    src.write_text("a", encoding="utf-8")
    out = tmp_path / "a.zip"
    api.archive_create({"sources": [str(src)], "format": "zip", "output_path": str(out)})
    dest = tmp_path / "dest"
    res = api.archive_extract({"archive_path": str(out), "target_dir": str(dest), "expected_sha256": "f" * 64})
    assert res["ok"] is False
    assert not dest.exists()
    res = api.archive_extract({"archive_path": str(out), "target_dir": str(dest)})
    assert res["ok"] is True
    assert (dest / "a.txt").exists()


def test_archive_zip_member_hashes(tmp_path: Path) -> None:
    # ZIP members are hashed through the same API.
    api = WebApi()
    src = tmp_path / "z.txt"
    src.write_bytes(b"zip bytes")
    out = tmp_path / "z.zip"
    api.archive_create({"sources": [str(src)], "format": "zip", "output_path": str(out)})
    sums = api.archive_checksums({"archive_path": str(out)})
    assert sums["members"][0]["sha256"] == hashlib.sha256(b"zip bytes").hexdigest()
