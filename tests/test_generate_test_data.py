"""Tests for tests/generate_test_data.py: every sample asset exists and opens with its library."""
import csv
import hashlib
import importlib.util
import json
import struct
import subprocess
import sys
import wave
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import docx
import h5py
import pymupdf
import pytest
import trimesh
import yaml
from PIL import Image

GENERATOR = Path(__file__).resolve().parent / "generate_test_data.py"
REQUIRED_FILES = [
    "sample.docx", "sample.pdf", "sample_scanned.pdf", "sample.txt", "sample.md", "sample.json",
    "sample.yaml", "sample.csv", "sample.xml", "sample.png", "sample.jpg", "sample.webp",
    "sample.stl", "sample_binary.stl", "sample.wav", "sample.m3u8",
]
OPTIONAL_FILES = ["sample.mp4", "sample.h5", "sample.hdf5"]


def run_generator(out_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GENERATOR), "--out", str(out_dir)],
        capture_output=True, text=True, timeout=300,
    )


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out_dir = tmp_path_factory.mktemp("test_data")
    result = run_generator(out_dir)
    assert result.returncode == 0, result.stdout + result.stderr
    return out_dir


def test_required_files_exist_and_non_empty(data_dir: Path) -> None:
    for name in REQUIRED_FILES:
        path = data_dir / name
        assert path.is_file(), name
        assert path.stat().st_size > 0, name


def test_optional_files_non_empty_when_present(data_dir: Path) -> None:
    for name in OPTIONAL_FILES:
        path = data_dir / name
        if path.exists():
            assert path.stat().st_size > 0, name


def test_docx_opens_with_structure(data_dir: Path) -> None:
    document = docx.Document(str(data_dir / "sample.docx"))
    styles = [paragraph.style.name for paragraph in document.paragraphs]
    assert "Heading 1" in styles
    assert "Heading 2" in styles
    assert "List Bullet" in styles
    bold_runs = [run.text for paragraph in document.paragraphs for run in paragraph.runs if run.bold]
    assert bold_runs
    assert document.core_properties.author == "Telemetry Team"
    assert document.core_properties.title == "Orbital Telemetry Report"


def test_pdf_is_multi_page_with_text(data_dir: Path) -> None:
    pdf = pymupdf.open(str(data_dir / "sample.pdf"))
    assert len(pdf) == 3
    for page in pdf:
        assert "Autonomous Flight Guidance" in page.get_text()
    assert pdf[0].search_for("telemetry")
    pdf.close()


def test_scanned_pdf_has_no_text_layer(data_dir: Path) -> None:
    pdf = pymupdf.open(str(data_dir / "sample_scanned.pdf"))
    assert len(pdf) >= 1
    for page in pdf:
        assert page.get_text().strip() == ""
        assert len(page.get_images()) >= 1
    pdf.close()


def test_text_formats_parse(data_dir: Path) -> None:
    assert "\n\n" in (data_dir / "sample.txt").read_text(encoding="utf-8")
    markdown = (data_dir / "sample.md").read_text(encoding="utf-8")
    assert "- [x]" in markdown and "- [ ]" in markdown
    assert "```" in markdown
    assert "|---" in markdown
    data = json.loads((data_dir / "sample.json").read_text(encoding="utf-8"))
    assert isinstance(data["crew"], list)
    assert isinstance(data["stages"]["first"], dict)
    config = yaml.safe_load((data_dir / "sample.yaml").read_text(encoding="utf-8"))
    assert config["mission"] == "Apollo"
    with open(data_dir / "sample.csv", newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0][0] == "id"
    assert len(rows) > 5
    root = ET.parse(data_dir / "sample.xml").getroot()
    assert root.tag == "mission"
    assert root.attrib["id"]
    assert root.find("crew/member") is not None


def test_hdf5_files(data_dir: Path) -> None:
    for name in ("sample.h5", "sample.hdf5"):
        with h5py.File(data_dir / name, "r") as handle:
            groups = [key for key in handle.keys() if isinstance(handle[key], h5py.Group)]
            assert len(groups) >= 2
            assert handle["telemetry"].attrs["system"]
            assert handle["telemetry/timestamps"].shape == (100,)
            assert handle["telemetry/accelerometer"].shape == (100, 3)


def test_png_has_alpha(data_dir: Path) -> None:
    with Image.open(data_dir / "sample.png") as image:
        assert image.mode == "RGBA"
        low, high = image.getchannel("A").getextrema()
        assert low == 0
        assert high > 200


def test_jpg_has_exif_model_and_orientation(data_dir: Path) -> None:
    with Image.open(data_dir / "sample.jpg") as image:
        exif = image.getexif()
        assert exif[0x0110] == "FOSS-CAM 100"
        assert exif[0x0112] == 6


def test_webp_opens(data_dir: Path) -> None:
    with Image.open(data_dir / "sample.webp") as image:
        assert image.format == "WEBP"
        assert image.size == (320, 240)


def test_stl_ascii_and_binary_parse(data_dir: Path) -> None:
    ascii_text = (data_dir / "sample.stl").read_text(encoding="ascii")
    assert ascii_text.startswith("solid bracket")
    assert ascii_text.count("facet normal") > 100
    binary = (data_dir / "sample_binary.stl").read_bytes()
    count = struct.unpack("<I", binary[80:84])[0]
    assert len(binary) == 84 + 50 * count
    ascii_mesh = trimesh.load(str(data_dir / "sample.stl"))
    binary_mesh = trimesh.load(str(data_dir / "sample_binary.stl"))
    assert len(ascii_mesh.faces) == count
    assert len(binary_mesh.faces) == count
    assert abs(ascii_mesh.bounds[1][0] - 60.0) < 1e-6


def test_wav_header(data_dir: Path) -> None:
    raw = (data_dir / "sample.wav").read_bytes()
    assert raw[:4] == b"RIFF" and raw[8:12] == b"WAVE"
    with wave.open(str(data_dir / "sample.wav"), "rb") as handle:
        assert handle.getsampwidth() == 2
        assert handle.getnchannels() == 1
        assert handle.getnframes() > 0


def test_m3u8_header(data_dir: Path) -> None:
    text = (data_dir / "sample.m3u8").read_text(encoding="utf-8")
    assert text.startswith("#EXTM3U")
    assert "sample.wav" in text


def test_mp4_has_video_and_aac_when_present(data_dir: Path) -> None:
    path = data_dir / "sample.mp4"
    if not path.exists():
        pytest.skip("sample.mp4 is optional and ffmpeg was unavailable")
    spec = importlib.util.spec_from_file_location("generate_test_data", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ffmpeg = module.find_ffmpeg()
    assert ffmpeg is not None
    probe = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    assert "Video:" in probe.stderr
    assert "Audio: aac" in probe.stderr


def test_docx_is_valid_zip(data_dir: Path) -> None:
    with zipfile.ZipFile(data_dir / "sample.docx") as archive:
        assert archive.testzip() is None
        assert "word/document.xml" in archive.namelist()


def test_generation_is_deterministic(data_dir: Path, tmp_path: Path) -> None:
    second = tmp_path / "second"
    result = run_generator(second)
    assert result.returncode == 0
    for name in REQUIRED_FILES:
        first_hash = hashlib.sha256((data_dir / name).read_bytes()).hexdigest()
        second_hash = hashlib.sha256((second / name).read_bytes()).hexdigest()
        assert first_hash == second_hash, name
