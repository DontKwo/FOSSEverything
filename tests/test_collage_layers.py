"""Unit tests for collage freeform multi-layer compositor and multi-format exporters."""
from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path
from PIL import Image
import pytest
from psd_tools import PSDImage

from app.features.collage.ops import (
    CollageLayer,
    export_collage_layers,
    render_freeform_composite,
    transform_layer_bitmap,
)


@pytest.fixture
def sample_layers(tmp_path: Path) -> tuple[str, str]:
    # Create two solid color sample png images.
    red_path = str(tmp_path / "red.png")
    green_path = str(tmp_path / "green.png")

    img_red = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    img_red.save(red_path)

    img_green = Image.new("RGBA", (100, 100), (0, 255, 0, 255))
    img_green.save(green_path)

    return red_path, green_path


def test_transform_layer_bitmap(sample_layers: tuple[str, str]) -> None:
    # Test layer resizing and opacity scaling.
    red_path, _ = sample_layers
    layer = CollageLayer(
        layer_id="l1",
        name="Red",
        source_path=red_path,
        x=10.0,
        y=20.0,
        width=50.0,
        height=50.0,
        rotation_deg=0.0,
        opacity=0.5,
    )
    bmp, tx, ty = transform_layer_bitmap(layer)
    assert bmp.size == (50, 50)
    assert tx == 10
    assert ty == 20
    # Alpha should be around 127
    pixel = bmp.getpixel((25, 25))
    assert pixel[0] == 255
    assert 120 <= pixel[3] <= 130


def test_z_order_compositing(sample_layers: tuple[str, str]) -> None:
    # Overlapping layers: top layer pixel colors dominate bottom layer.
    red_path, green_path = sample_layers
    l_red = CollageLayer("l1", "Red", red_path, 0, 0, 100, 100)
    l_green = CollageLayer("l2", "Green", green_path, 50, 50, 100, 100)

    # Red under Green: overlap at (75, 75) should be green
    comp1 = render_freeform_composite(200, 200, [l_red, l_green])
    px1 = comp1.getpixel((75, 75))
    assert px1[0] == 0 and px1[1] == 255

    # Green under Red: overlap at (75, 75) should be red
    comp2 = render_freeform_composite(200, 200, [l_green, l_red])
    px2 = comp2.getpixel((75, 75))
    assert px2[0] == 255 and px2[1] == 0


def test_export_psd(sample_layers: tuple[str, str], tmp_path: Path) -> None:
    # Export layered Photoshop PSD file and verify layer count and bboxes.
    red_path, green_path = sample_layers
    out_file = str(tmp_path / "test.psd")
    layers = [
        CollageLayer("l1", "RedLayer", red_path, 10, 15, 80, 80),
        CollageLayer("l2", "GreenLayer", green_path, 50, 60, 90, 90),
    ]

    res = export_collage_layers(300, 300, layers, out_file, export_format="psd")
    assert res["layer_count"] == 2
    assert os.path.exists(out_file)

    psd = PSDImage.open(out_file)
    assert psd.width == 300
    assert psd.height == 300
    assert len(psd) == 2
    names = [lyr.name for lyr in psd]
    assert "RedLayer" in names
    assert "GreenLayer" in names


def test_export_ora(sample_layers: tuple[str, str], tmp_path: Path) -> None:
    # Export OpenRaster ORA archive and verify mimetype and stack.xml.
    red_path, green_path = sample_layers
    out_file = str(tmp_path / "test.ora")
    layers = [
        CollageLayer("l1", "RedLayer", red_path, 10, 10, 100, 100),
        CollageLayer("l2", "GreenLayer", green_path, 40, 40, 100, 100),
    ]

    res = export_collage_layers(250, 250, layers, out_file, export_format="ora")
    assert res["format"] == "ora"

    with zipfile.ZipFile(out_file, "r") as zf:
        # First entry must be mimetype uncompressed
        first_info = zf.infolist()[0]
        assert first_info.filename == "mimetype"
        assert zf.read("mimetype") == b"image/openraster"
        stack_xml = zf.read("stack.xml").decode("utf-8")
        assert "RedLayer" in stack_xml
        assert "GreenLayer" in stack_xml


def test_export_zip(sample_layers: tuple[str, str], tmp_path: Path) -> None:
    # Export transparent PNG layers ZIP with layers.json manifest.
    red_path, green_path = sample_layers
    out_file = str(tmp_path / "layers.zip")
    layers = [
        CollageLayer("l1", "RedLayer", red_path, 10, 10, 50, 50),
        CollageLayer("l2", "GreenLayer", green_path, 20, 20, 60, 60),
    ]

    res = export_collage_layers(200, 200, layers, out_file, export_format="zip")
    assert res["layer_count"] == 2

    with zipfile.ZipFile(out_file, "r") as zf:
        manifest_data = json.loads(zf.read("layers.json").decode("utf-8"))
        assert manifest_data["canvas_width"] == 200
        assert len(manifest_data["layers"]) == 2
        # Check that PNGs exist and have full canvas size
        assert "01_RedLayer.png" in zf.namelist()
        with zf.open("01_RedLayer.png") as png_f:
            img = Image.open(png_f)
            assert img.size == (200, 200)


def test_export_tiff(sample_layers: tuple[str, str], tmp_path: Path) -> None:
    # Export multi-frame TIFF and verify frame count.
    red_path, green_path = sample_layers
    out_file = str(tmp_path / "layers.tiff")
    layers = [
        CollageLayer("l1", "RedLayer", red_path, 10, 10, 50, 50),
        CollageLayer("l2", "GreenLayer", green_path, 20, 20, 60, 60),
    ]

    res = export_collage_layers(200, 200, layers, out_file, export_format="tiff")
    assert res["format"] == "tiff"

    with Image.open(out_file) as tiff_img:
        frames = 0
        while True:
            try:
                frames += 1
                tiff_img.seek(frames)
            except EOFError:
                break
        assert frames == 2

