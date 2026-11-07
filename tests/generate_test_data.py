#!/usr/bin/env python
"""Generate deterministic sample assets for tests and GUI walkthroughs into tests/test_data/."""
import argparse
import csv
import io
import json
import math
import random
import re
import shutil
import struct
import subprocess
import sys
import wave
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path

import docx
import h5py
import imageio_ffmpeg
import numpy as np
import pymupdf
import trimesh
import yaml
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Point, Polygon

DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "test_data"
FIXED_TIME = datetime(2024, 1, 15, 12, 0, 0)
ZIP_FIXED_DATE = (2024, 1, 15, 12, 0, 0)
SEED = 20240115

SCAN_LINES = [
    "Guidance, Navigation, and Control",
    "Scanned document text for optical character recognition testing.",
    "The quick brown fox jumps over the lazy dog 0123456789.",
    "Vehicle mass 1250.5 kg, thrust 4800 N, burn time 42 s.",
]


def make_sample_txt(out: Path) -> None:
    paragraphs = [
        "Guidance, Navigation, and Control systems test dataset.",
        "This plain text file holds several paragraphs with ordinary punctuation: commas, semicolons; "
        "colons: and \"quoted\" phrases. It is used to check encoding, word counts, and diffing.",
        "Second paragraph. It contains short sentences. Each one ends with a period! Some end with a question mark?",
        "Final paragraph with numbers (1, 2, 3), a hyphenated-word, and an apostrophe in don't.",
    ]
    (out / "sample.txt").write_text("\n\n".join(paragraphs) + "\n", encoding="utf-8", newline="\n")


def make_sample_md(out: Path) -> None:
    lines = [
        "# Mission Specification",
        "",
        "A *GitHub Flavored Markdown* sample with **bold**, ~~strikethrough~~, and a [link](https://example.com).",
        "",
        "## Checklist",
        "",
        "- [x] Pre-launch check",
        "- [x] Fuel loading",
        "- [ ] Ignition",
        "- [ ] Liftoff",
        "",
        "## Code",
        "",
        "```python",
        "def calc_dv(isp: float, m0: float, mf: float, g0: float = 9.80665) -> float:",
        "    return isp * g0 * math.log(m0 / mf)",
        "```",
        "",
        "## Stage Table",
        "",
        "| Stage | Velocity (m/s) | Status  |",
        "|-------|---------------:|:--------|",
        "| 1     |         1250.5 | nominal |",
        "| 2     |         4800.0 | nominal |",
        "| 3     |         7800.0 | pending |",
        "",
        "> Note: all values are illustrative.",
        "",
    ]
    (out / "sample.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def make_sample_json(out: Path) -> None:
    data = {
        "mission": "Apollo",
        "active": True,
        "count": 42,
        "ratio": 0.618,
        "notes": None,
        "crew": [
            {"name": "Armstrong", "role": "commander", "flights": 2},
            {"name": "Collins", "role": "pilot", "flights": 2},
            {"name": "Aldrin", "role": "lander pilot", "flights": 2},
        ],
        "stages": {
            "first": {"engines": 5, "thrust_kn": [7600.0, 7600.0, 7600.0, 7600.0, 7600.0], "tags": ["booster"]},
            "second": {"engines": 5, "thrust_kn": [1000.0] * 5, "tags": ["upper", "cryogenic"]},
        },
        "matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
    }
    (out / "sample.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def make_sample_yaml(out: Path) -> None:
    config = {
        "mission": "Apollo",
        "active": True,
        "count": 42,
        "launch": {"site": "LC-39A", "window_utc": "2024-01-15T12:00:00Z", "azimuth_deg": 72.5},
        "stages": [
            {"name": "S-IC", "engines": 5, "fuel": "RP-1"},
            {"name": "S-II", "engines": 5, "fuel": "LH2"},
        ],
        "limits": {"max_q_pa": 33000, "max_accel_g": 4.0},
        "tags": ["test", "sample"],
    }
    text = yaml.safe_dump(config, sort_keys=False, default_flow_style=False)
    (out / "sample.yaml").write_text(text, encoding="utf-8", newline="\n")


def make_sample_csv(out: Path) -> None:
    rng = random.Random(SEED)
    statuses = ["nominal", "nominal", "nominal", "degraded", "offline"]
    names = ["Stage1", "Stage2", "Fairing", "Capsule", "Tower"]
    with open(out / "sample.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["id", "name", "velocity_mps", "altitude_km", "status"])
        for row_id in range(1, 21):
            name = names[(row_id - 1) % len(names)]
            velocity = round(rng.uniform(100.0, 7800.0), 1)
            altitude = round(rng.uniform(0.0, 400.0), 2)
            writer.writerow([row_id, name, velocity, altitude, rng.choice(statuses)])


def make_sample_xml(out: Path) -> None:
    root = ET.Element("mission", {"id": "apollo-11", "year": "1969"})
    crew = ET.SubElement(root, "crew")
    members = [("Armstrong", "commander"), ("Collins", "pilot"), ("Aldrin", "lander pilot")]
    for index, (name, role) in enumerate(members, start=1):
        member = ET.SubElement(crew, "member", {"seat": str(index), "role": role})
        member.text = name
    stages = ET.SubElement(root, "stages")
    for number, thrust in ((1, "7600"), (2, "1000"), (3, "200")):
        stage = ET.SubElement(stages, "stage", {"number": str(number)})
        ET.SubElement(stage, "thrust", {"unit": "kN"}).text = thrust
    ET.SubElement(root, "notes").text = "Illustrative data & <test> markup."
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    (out / "sample.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n", encoding="utf-8", newline="\n")


def rewrite_zip_fixed_dates(path: Path) -> None:
    # Rewrite a zip with a constant timestamp on every entry for reproducible bytes.
    buffer = io.BytesIO()
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as dest:
        for info in source.infolist():
            new_info = zipfile.ZipInfo(info.filename, ZIP_FIXED_DATE)
            new_info.compress_type = zipfile.ZIP_DEFLATED
            new_info.external_attr = info.external_attr
            dest.writestr(new_info, source.read(info.filename))
    path.write_bytes(buffer.getvalue())


def make_sample_docx(out: Path) -> None:
    doc = docx.Document()
    doc.add_heading("Orbital Telemetry Report", level=1)
    doc.add_paragraph("Spacecraft trajectory verification dataset.")
    doc.add_heading("Summary", level=2)
    para = doc.add_paragraph("This report contains ")
    para.add_run("bold findings").bold = True
    para.add_run(" and ")
    para.add_run("italic remarks").italic = True
    para.add_run(" about the flight.")
    doc.add_heading("Key Points", level=2)
    for item in ("Inertial navigation nominal", "Guidance loop closed at 50 Hz", "Control margins above 6 dB"):
        doc.add_paragraph(item, style="List Bullet")
    doc.add_heading("Procedure", level=2)
    for item in ("Initialize sensors", "Align platform", "Begin ascent"):
        doc.add_paragraph(item, style="List Number")
    table = doc.add_table(rows=3, cols=3)
    table.style = "Table Grid"
    rows = [("Stage", "Velocity (m/s)", "Status"), ("1", "1250.5", "nominal"), ("2", "4800.0", "nominal")]
    for row_index, row_values in enumerate(rows):
        for col_index, value in enumerate(row_values):
            table.cell(row_index, col_index).text = value
    props = doc.core_properties
    props.title = "Orbital Telemetry Report"
    props.author = "Telemetry Team"
    props.last_modified_by = "Telemetry Team"
    props.subject = "Trajectory verification"
    props.keywords = "telemetry, guidance, sample"
    props.comments = "Generated test document"
    props.category = "Test Data"
    props.revision = 1
    props.created = FIXED_TIME
    props.modified = FIXED_TIME
    path = out / "sample.docx"
    doc.save(str(path))
    rewrite_zip_fixed_dates(path)


def fix_pdf_trailer_id(path: Path) -> None:
    # Replace the random trailer /ID hex strings with fixed same-length values.
    data = path.read_bytes()
    fixed = b"/ID[<" + b"0" * 32 + b"><" + b"0" * 32 + b">]"
    path.write_bytes(re.sub(rb"/ID\[<[0-9A-Fa-f]{32}><[0-9A-Fa-f]{32}>\]", fixed, data))


def make_sample_pdf(out: Path) -> None:
    doc = pymupdf.open()
    for number in range(1, 4):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 80), f"Autonomous Flight Guidance - Page {number}", fontsize=20)
        page.draw_line((72, 90), (540, 90), width=1.0)
        body = (
            f"Body text for page {number}. The guidance document describes autonomous flight "
            "control, navigation filters, and trajectory optimization for test purposes. "
            "Searchable keyword: telemetry. Searchable number: 1250.5 meters per second."
        )
        page.insert_textbox(pymupdf.Rect(72, 110, 540, 260), body, fontsize=11)
        page.draw_rect(pymupdf.Rect(72, 300, 300, 420), color=(0.1, 0.2, 0.6), fill=(0.85, 0.9, 1.0), width=1.5)
        page.draw_circle((420, 360), 50, color=(0.6, 0.1, 0.1), width=1.5)
        page.insert_text((80, 330), f"Figure {number}: vector shapes", fontsize=10)
        page.insert_text((72, 760), f"Page {number} of 3", fontsize=9)
    doc.set_metadata({
        "title": "Autonomous Flight Guidance",
        "author": "Telemetry Team",
        "subject": "Sample searchable PDF",
        "keywords": "guidance, telemetry",
        "creator": "generate_test_data.py",
        "producer": "PyMuPDF",
        "creationDate": "",
        "modDate": "",
    })
    doc.save(str(out / "sample.pdf"), deflate=True, garbage=3)
    doc.close()
    fix_pdf_trailer_id(out / "sample.pdf")


def render_scan_page(lines: list[str], size: tuple[int, int], seed: int) -> bytes:
    # Rasterize text lines with mild noise to mimic a scan; returns JPEG bytes.
    image = Image.new("L", size, color=250)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=34)
    y_px = 120
    for line in lines:
        draw.text((100, y_px), line, fill=15, font=font)
        y_px += 90
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, 4.0, (size[1], size[0]))
    array = np.clip(np.asarray(image, dtype=np.float64) + noise, 0, 255).astype(np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(array, mode="L").save(buffer, format="JPEG", quality=60)
    return buffer.getvalue()


def make_sample_scanned_pdf(out: Path) -> None:
    doc = pymupdf.open()
    size = (1275, 1650)
    for page_index in range(2):
        scan_bytes = render_scan_page(SCAN_LINES, size, SEED + page_index)
        page = doc.new_page(width=612, height=792)
        page.insert_image(page.rect, stream=scan_bytes)
    doc.set_metadata({"title": "Scanned Document", "creationDate": "", "modDate": ""})
    doc.save(str(out / "sample_scanned.pdf"), deflate=True, garbage=3)
    doc.close()
    fix_pdf_trailer_id(out / "sample_scanned.pdf")


def make_sample_h5(out: Path) -> bool:
    # Writes sample.h5 and sample.hdf5 and returns True.
    rng = np.random.default_rng(SEED)
    path = out / "sample.h5"
    with h5py.File(path, "w") as handle:
        handle.attrs["title"] = "Flight test container"
        handle.attrs["version"] = 1
        telemetry = handle.create_group("telemetry")
        telemetry.attrs["system"] = "Inertial Measurement Unit"
        telemetry.attrs["sample_rate_hz"] = 10.0
        stamps = telemetry.create_dataset("timestamps", data=np.linspace(0.0, 10.0, 100), track_times=False)
        stamps.attrs["units"] = "s"
        accel = telemetry.create_dataset("accelerometer", data=rng.normal(9.81, 0.05, (100, 3)), track_times=False)
        accel.attrs["units"] = "m/s^2"
        accel.attrs["axes"] = "x,y,z"
        nav = handle.create_group("navigation")
        nav.attrs["frame"] = "ECEF"
        nav.create_dataset("position_m", data=rng.normal(0.0, 100.0, (50, 3)), track_times=False)
        nav.create_dataset("fix_count", data=np.arange(50, dtype=np.int32), track_times=False)
        config = handle.create_group("config")
        sub = config.create_group("limits")
        sub.attrs["description"] = "Operational limits"
        sub.create_dataset("max_accel_g", data=np.array([4.0], dtype=np.float64), track_times=False)
    shutil.copyfile(path, out / "sample.hdf5")
    return True


def make_sample_png(out: Path) -> None:
    size = 256
    grid_y, grid_x = np.mgrid[0:size, 0:size]
    red = (grid_x * 255 // (size - 1)).astype(np.uint8)
    green = (grid_y * 255 // (size - 1)).astype(np.uint8)
    blue = np.full((size, size), 160, dtype=np.uint8)
    dist = np.sqrt((grid_x - size / 2.0) ** 2 + (grid_y - size / 2.0) ** 2)
    alpha = np.clip(255.0 * (1.0 - dist / (size / 2.0)), 0, 255).astype(np.uint8)
    rgba = np.stack([red, green, blue, alpha], axis=-1)
    Image.fromarray(rgba, mode="RGBA").save(out / "sample.png", format="PNG")


def build_rgb_scene(size: tuple[int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, color=(30, 60, 110))
    draw = ImageDraw.Draw(image)
    for row in range(height):
        shade = int(60 + 140 * row / height)
        draw.line([(0, row), (width, row)], fill=(shade // 2, shade, 255 - shade // 2))
    draw.ellipse([width // 2 - 60, height // 2 - 60, width // 2 + 60, height // 2 + 60], fill=(240, 200, 40))
    draw.rectangle([20, height - 80, 140, height - 20], fill=(200, 60, 40), outline=(255, 255, 255), width=3)
    return image


def make_sample_jpg(out: Path) -> None:
    image = build_rgb_scene((320, 240))
    exif = Image.Exif()
    exif[0x010F] = "FOSS Optics"
    exif[0x0110] = "FOSS-CAM 100"
    exif[0x0112] = 6
    exif[0x0131] = "generate_test_data.py"
    exif[0x0132] = "2024:01:15 12:00:00"
    image.save(out / "sample.jpg", format="JPEG", quality=90, exif=exif.tobytes())


def make_sample_webp(out: Path) -> None:
    build_rgb_scene((320, 240)).save(out / "sample.webp", format="WEBP", lossless=True)


def build_bracket_mesh() -> trimesh.Trimesh:
    # L-bracket in mm: base plate with two holes, upright wall, two triangular gussets.
    plate_outline = Polygon([(0, 0), (60, 0), (60, 40), (0, 40)])
    holes = [Point(12, 25).buffer(4.0, quad_segs=16), Point(48, 25).buffer(4.0, quad_segs=16)]
    plate_poly = Polygon(plate_outline.exterior.coords, [list(hole.exterior.coords) for hole in holes])
    plate = trimesh.creation.extrude_polygon(plate_poly, 5.0)
    wall = trimesh.creation.box(extents=(60.0, 5.0, 35.0))
    wall.apply_translation((30.0, 2.5, 5.0 + 17.5))
    parts = [plate, wall]
    for x_start in (10.0, 47.0):
        profile = Polygon([(5, 5), (30, 5), (5, 30)])
        gusset = trimesh.creation.extrude_polygon(profile, 3.0)
        verts = np.asarray(gusset.vertices)
        permuted = np.stack([verts[:, 2], verts[:, 0], verts[:, 1]], axis=1)
        permuted[:, 0] += x_start
        parts.append(trimesh.Trimesh(vertices=permuted, faces=gusset.faces, process=False))
    mesh = trimesh.util.concatenate(parts)
    return mesh


def write_stl_ascii(mesh: trimesh.Trimesh, path: Path, name: str) -> None:
    lines = [f"solid {name}"]
    for face_index, face in enumerate(mesh.faces):
        normal = mesh.face_normals[face_index]
        lines.append(f"  facet normal {normal[0]:.6e} {normal[1]:.6e} {normal[2]:.6e}")
        lines.append("    outer loop")
        for vertex_index in face:
            vert = mesh.vertices[vertex_index]
            lines.append(f"      vertex {vert[0]:.6e} {vert[1]:.6e} {vert[2]:.6e}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {name}")
    path.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


def write_stl_binary(mesh: trimesh.Trimesh, path: Path, name: str) -> None:
    header = f"binary STL {name}".encode("ascii").ljust(80, b"\x00")[:80]
    chunks = [header, struct.pack("<I", len(mesh.faces))]
    for face_index, face in enumerate(mesh.faces):
        normal = mesh.face_normals[face_index]
        chunks.append(struct.pack("<3f", float(normal[0]), float(normal[1]), float(normal[2])))
        for vertex_index in face:
            vert = mesh.vertices[vertex_index]
            chunks.append(struct.pack("<3f", float(vert[0]), float(vert[1]), float(vert[2])))
        chunks.append(struct.pack("<H", 0))
    path.write_bytes(b"".join(chunks))


def make_sample_stl(out: Path) -> None:
    mesh = build_bracket_mesh()
    write_stl_ascii(mesh, out / "sample.stl", "bracket")
    write_stl_binary(mesh, out / "sample_binary.stl", "bracket")


def make_sample_wav(out: Path) -> float:
    rate = 22050
    seconds = 2.0
    frames = int(rate * seconds)
    samples = bytearray()
    for index in range(frames):
        t_sec = index / rate
        envelope = min(1.0, t_sec / 0.05, (seconds - t_sec) / 0.05)
        value = 0.5 * math.sin(2.0 * math.pi * 440.0 * t_sec) + 0.25 * math.sin(2.0 * math.pi * 880.0 * t_sec)
        samples += struct.pack("<h", int(round(32767 * 0.8 * envelope * value)))
    with wave.open(str(out / "sample.wav"), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(samples))
    return seconds


def find_ffmpeg() -> str | None:
    # Same order as app.features.media.ops.get_ffmpeg_path: imageio-ffmpeg, then PATH.
    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return str(exe)
    except Exception as exc:
        print(f"imageio-ffmpeg lookup failed: {exc}")
    return shutil.which("ffmpeg")


def make_sample_mp4(out: Path) -> bool:
    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        print("SKIP sample.mp4: no ffmpeg found (imageio-ffmpeg or PATH)")
        return False
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=15:duration=2",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p", "-threads", "1",
        "-c:a", "aac", "-b:a", "96k", "-ac", "1",
        "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact",
        "-movflags", "+faststart", "-shortest", str(out / "sample.mp4"),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"SKIP sample.mp4: ffmpeg failed to run: {exc}")
        return False
    if result.returncode != 0:
        print(f"SKIP sample.mp4: ffmpeg exited {result.returncode}: {result.stderr.strip()[:300]}")
        return False
    return True


def make_sample_m3u8(out: Path, wav_seconds: float, mp4_made: bool) -> None:
    lines = ["#EXTM3U", "#PLAYLIST:Sample Tracks"]
    lines.append(f"#EXTINF:{int(round(wav_seconds))},FOSS Everything - Sample Tone")
    lines.append("sample.wav")
    if mp4_made:
        lines.append("#EXTINF:2,FOSS Everything - Sample Clip")
        lines.append("sample.mp4")
    (out / "sample.m3u8").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def generate_all_test_assets(target_dir: str | Path = DEFAULT_OUT_DIR) -> list[str]:
    # Writes all sample assets; returns names of optional files that were skipped.
    out = Path(target_dir)
    out.mkdir(parents=True, exist_ok=True)
    skipped: list[str] = []
    make_sample_txt(out)
    make_sample_md(out)
    make_sample_json(out)
    make_sample_yaml(out)
    make_sample_csv(out)
    make_sample_xml(out)
    make_sample_docx(out)
    make_sample_pdf(out)
    make_sample_scanned_pdf(out)
    make_sample_h5(out)
    make_sample_png(out)
    make_sample_jpg(out)
    make_sample_webp(out)
    make_sample_stl(out)
    wav_seconds = make_sample_wav(out)
    mp4_made = make_sample_mp4(out)
    if not mp4_made:
        skipped.append("sample.mp4")
    make_sample_m3u8(out, wav_seconds, mp4_made)
    return skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate sample test assets.")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="output directory")
    args = parser.parse_args(argv)
    skipped = generate_all_test_assets(args.out)
    print(f"Wrote test assets to {args.out}")
    if skipped:
        print("Skipped optional files: " + ", ".join(skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
