from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PIL import Image

from app.web.api import WebApi


def test_converter_case_insensitive_searchable_pdf_and_output_stem(tmp_path: Path) -> None:
    # Verify converter accepts case-insensitive searchable PDF and respects output stem.
    api = WebApi()
    img_path = tmp_path / "scan_doc.png"
    img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    img.save(str(img_path))

    res = api.converter_convert_file({
        "file_path": str(img_path),
        "target_format": "pdf (searchable)",
        "output_stem": "custom_searchable_stem",
    })
    assert res.get("ok") is True
    out_p = res.get("output_path")
    assert out_p and os.path.exists(out_p)
    assert Path(out_p).stem == "custom_searchable_stem"
    assert Path(out_p).suffix.lower() == ".pdf"


def test_converter_batch_recursive_folder_and_preserve_tree(tmp_path: Path) -> None:
    # Verify batch folder scanning and preserve tree subfolder outputs.
    api = WebApi()
    src_dir = tmp_path / "source_tree"
    sub_dir = src_dir / "nested" / "docs"
    sub_dir.mkdir(parents=True)

    f1 = src_dir / "root.txt"
    f1.write_text("Root document content", encoding="utf-8")
    f2 = sub_dir / "inner.txt"
    f2.write_text("Nested document content", encoding="utf-8")

    scan_res = api.converter_scan_inputs({
        "paths": [str(src_dir)],
        "recursive": True,
    })
    assert scan_res.get("ok") is True
    items = scan_res.get("items", [])
    assert len(items) == 2

    out_dir = tmp_path / "batch_out"
    batch_res = api.converter_batch_convert({
        "items": [
            {"path": str(f1), "target_format": "ENEX", "rel_dir": ""},
            {"path": str(f2), "target_format": "ENEX", "rel_dir": str(Path("nested") / "docs")},
        ],
        "output_dir": str(out_dir),
        "preserve_tree": True,
    })
    assert batch_res.get("ok") is True
    assert batch_res.get("succeeded") == 2
    assert (out_dir / "root.enex").exists()
    assert (out_dir / "nested" / "docs" / "inner.enex").exists()


def test_compressor_png_quantization_reduces_size(tmp_path: Path) -> None:
    # Verify PNG palette quantization reduces file size.
    import numpy as np
    api = WebApi()
    png_path = tmp_path / "photo.png"
    arr = (np.random.default_rng(42).random((200, 200, 3)) * 255).astype("uint8")
    img = Image.fromarray(arr)
    img.save(str(png_path), format="PNG")
    orig_size = png_path.stat().st_size

    res = api.compressor_compress_items({
        "items": [{"path": str(png_path), "category": "Image"}],
        "preset": "aggressive",
        "lossy_png": True,
        "png_colors": 32,
    })
    assert res.get("ok") is True
    item_res = res.get("results", [])[0]
    assert item_res.get("ok") is True
    comp_size = item_res.get("compressed_bytes", 0)
    assert comp_size < orig_size


def test_compressor_archive_repack_without_double_zip(tmp_path: Path) -> None:
    # Verify archive compression repacks entries without double .zip.zip nesting.
    import zipfile
    api = WebApi()
    orig_zip = tmp_path / "archive.zip"
    with zipfile.ZipFile(orig_zip, "w") as zf:
        zf.writestr("sample.txt", "Sample text file inside archive")

    res = api.compressor_compress_items({
        "items": [{"path": str(orig_zip), "category": "Archive"}],
    })
    assert res.get("ok") is True
    out_p = res.get("results", [])[0].get("output_path")
    assert out_p and os.path.exists(out_p)
    assert not out_p.endswith(".zip.zip")

    with zipfile.ZipFile(out_p, "r") as zf:
        namelist = zf.namelist()
        assert "sample.txt" in namelist
        assert not any(name.endswith(".zip") for name in namelist)
