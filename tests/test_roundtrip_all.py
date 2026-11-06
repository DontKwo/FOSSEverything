"""Comprehensive tests for format conversions, compressors, media, and features."""
from __future__ import annotations

import os
from pathlib import Path
from PIL import Image

from app.features.converter import ops as conv_ops
from app.features.data import ops as data_ops
from app.features.renamer import ops as rename_ops
from app.web.api.tool_compressor import _compress_image_file


def test_image_roundtrip_conversions(tmp_path: Path) -> None:
    # Test permutations of image format conversions.
    img = Image.new("RGB", (64, 64), color="blue")
    png_p = str(tmp_path / "test.png")
    img.save(png_p, format="PNG")

    targets = ["jpg", "webp", "bmp", "tiff"]
    for tgt in targets:
        out_dir = str(tmp_path / f"out_{tgt}")
        res = conv_ops.convert_file(png_p, out_dir, target_format=tgt)
        assert len(res) > 0
        assert os.path.exists(res[0])
        assert os.path.getsize(res[0]) > 0


def test_structured_data_conversions(tmp_path: Path) -> None:
    # Test JSON to YAML to TOML conversions.
    json_p = str(tmp_path / "sample.json")
    with open(json_p, "w", encoding="utf-8") as f:
        f.write('{"name": "test", "count": 42}')

    out_yaml_dir = str(tmp_path / "out_yaml")
    res_yaml = conv_ops.convert_file(json_p, out_yaml_dir, target_format="yaml")
    assert len(res_yaml) > 0
    assert os.path.exists(res_yaml[0])

    out_toml_dir = str(tmp_path / "out_toml")
    res_toml = conv_ops.convert_file(res_yaml[0], out_toml_dir, target_format="toml")
    assert len(res_toml) > 0
    assert os.path.exists(res_toml[0])


def test_compressor_custom_options(tmp_path: Path) -> None:
    # Test compressor with custom PNG quantization and JPEG quality.
    img = Image.new("RGB", (100, 100), color="red")
    png_p = str(tmp_path / "orig.png")
    img.save(png_p, format="PNG")

    out_png = str(tmp_path / "compressed.png")
    _compress_image_file(png_p, out_png, lossy_png=True, png_colors=32)
    assert os.path.exists(out_png)

    out_jpg = str(tmp_path / "compressed.jpg")
    _compress_image_file(png_p, out_jpg, preset="balanced", quality=50)
    assert os.path.exists(out_jpg)


def test_renamer_new_operations(tmp_path: Path) -> None:
    # Test new renamer step types: insert_text and regex_replace.
    f1 = str(tmp_path / "document_report.txt")
    with open(f1, "w") as f:
        f.write("test")

    steps = [
        {"type": "insert_text", "enabled": True, "text": "2026_", "index": 0},
        {"type": "regex_replace", "enabled": True, "pattern": "report", "replacement": "final"},
    ]
    plans = rename_ops.preview_step_pipeline([f1], steps)
    assert len(plans) == 1
    assert plans[0].new_name == "2026_document_final.txt"


def test_grammar_check_with_spelling_issues() -> None:
    # Test that grammar check flags spelling errors and reduces score.
    res = data_ops.grammar_check_text("This has completely asdfghjk qwertyuiop invalid words.")
    assert res["valid"] is False
    assert res["score"] < 100
    assert any(issue.get("type") == "spelling" for issue in res["issues"])
