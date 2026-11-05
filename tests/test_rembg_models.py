import os
from pathlib import Path

import pytest
from PIL import Image

from app.features.image.ops import (
    REMBG_MODEL_CATALOG,
    delete_rembg_model,
    get_rembg_models_dir,
    list_rembg_models_status,
)
from app.web.api.tool_images import ImagesApiMixin


class MockApiServer(ImagesApiMixin):
    # Test harness implementing ImagesApiMixin for RPC contract testing.
    pass


def test_rembg_models_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Verify unified rembg storage directory resolution and environment variable wiring.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    unified_dir = get_rembg_models_dir()
    expected_dir = str(tmp_path / ".u2net")
    assert Path(unified_dir) == Path(expected_dir)
    assert os.environ.get("REMBG_HOME") == unified_dir
    assert os.environ.get("U2NET_HOME") == unified_dir
    assert os.path.isdir(unified_dir)


def test_rembg_model_status_and_delete(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Verify model presence detection and cleanup behavior in unified storage.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    models_dir = get_rembg_models_dir()

    initial_status = list_rembg_models_status()
    u2netp_status = next(item for item in initial_status["models"] if item["id"] == "u2netp")
    assert not u2netp_status["downloaded"]
    assert u2netp_status["status"] == "pending"
    assert u2netp_status["disk_bytes"] == 0

    dummy_onnx = Path(models_dir) / "u2netp.onnx"
    dummy_payload = b"FAKE_ONNX_MODEL_BYTES_FOR_TESTING"
    dummy_onnx.write_bytes(dummy_payload)

    updated_status = list_rembg_models_status()
    u2netp_updated = next(item for item in updated_status["models"] if item["id"] == "u2netp")
    assert u2netp_updated["downloaded"]
    assert u2netp_updated["status"] == "downloaded"
    assert u2netp_updated["disk_bytes"] == len(dummy_payload)

    after_delete = delete_rembg_model("u2netp")
    u2netp_deleted = next(item for item in after_delete["models"] if item["id"] == "u2netp")
    assert not u2netp_deleted["downloaded"]
    assert u2netp_deleted["disk_bytes"] == 0
    assert not dummy_onnx.exists()


def test_rembg_catalog_entries() -> None:
    # Verify completeness and validity of model catalog definitions.
    assert len(REMBG_MODEL_CATALOG) >= 15
    for catalog_entry in REMBG_MODEL_CATALOG:
        assert isinstance(catalog_entry["id"], str)
        assert len(catalog_entry["id"]) > 0
        assert isinstance(catalog_entry["label"], str)
        assert len(catalog_entry["label"]) > 0
        assert catalog_entry["size_mb"] > 0
        assert catalog_entry["expected_bytes"] > 0
        assert isinstance(catalog_entry["filenames"], list)
        assert len(catalog_entry["filenames"]) >= 1


def test_images_flip_vertical(tmp_path: Path) -> None:
    # Verify vertical flipping transforms pixels vertically rather than horizontally.
    test_image = Image.new("RGBA", (10, 20), (0, 0, 0, 255))
    for pixel_x in range(10):
        test_image.putpixel((pixel_x, 0), (255, 0, 0, 255))

    input_path = tmp_path / "top_red.png"
    output_path = tmp_path / "flipped.png"
    test_image.save(input_path)

    api_harness = MockApiServer()
    api_result = api_harness.images_flip({
        "file_path": str(input_path),
        "direction": "vertical",
        "output_path": str(output_path),
    })

    assert api_result["ok"]
    assert output_path.exists()

    flipped_image = Image.open(output_path)
    assert flipped_image.size == (10, 20)
    assert flipped_image.getpixel((0, 0)) == (0, 0, 0, 255)
    assert flipped_image.getpixel((0, 19)) == (255, 0, 0, 255)


def test_images_save_preview_follows_extension(tmp_path: Path) -> None:
    # Verify the preview data URL is saved in the format of the chosen extension.
    import base64
    import io

    source = Image.new("RGBA", (12, 8), (10, 200, 30, 255))
    buffer = io.BytesIO()
    source.save(buffer, format="PNG")
    data_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

    api_harness = MockApiServer()
    for ext, expected in (("webp", "WEBP"), ("jpg", "JPEG"), ("png", "PNG")):
        out_path = tmp_path / f"transformed.{ext}"
        result = api_harness.images_save_preview({"data_url": data_url, "output_path": str(out_path), "quality": 70})
        assert result["ok"]
        with Image.open(out_path) as saved:
            assert saved.format == expected
            assert saved.size == (12, 8)


def test_images_models_status_reports_badges(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Verify every catalog model reports a downloaded or pending status and a size label.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    (tmp_path / ".u2net").mkdir()
    (tmp_path / ".u2net" / "u2net.onnx").write_bytes(b"FAKE")
    result = MockApiServer().images_models_status({})
    assert result["ok"]
    by_id = {item["id"]: item for item in result["models"]}
    assert by_id["u2net"]["status"] == "downloaded"
    assert by_id["u2netp"]["status"] == "pending"
    assert by_id["u2netp"]["download_size"].endswith("MB")
