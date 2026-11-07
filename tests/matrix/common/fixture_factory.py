import hashlib
import json
import math
import os
import random
import struct
import subprocess
import wave
import zipfile
from pathlib import Path
from typing import Any

import docx
import imageio_ffmpeg
import openpyxl
from PIL import Image, ImageDraw
import pptx
import pymupdf
import qrcode
import toml
import trimesh
import yaml

ALL_FAMILIES = (
    "pdf", "png", "jpg", "webp", "bmp", "tiff", "gif", "svg", "heic", "raw", "psd",
    "mp4", "mov", "mkv", "webm", "mp3", "wav", "flac", "aac", "ogg",
    "docx", "xlsx", "pptx", "csv", "tsv", "json", "yaml", "toml", "xml", "h5", "hdf5",
    "md", "txt", "stl", "obj", "ply", "gltf", "step", "zip", "tar", "gz", "7z",
    "srt", "vtt", "m3u", "m3u8", "ics", "epub", "ttf", "otf", "woff", "woff2",
    "enex", "sql", "js", "css", "qr", "scanned_pdf"
)

ALL_VARIANTS = (
    "minimal_valid", "typical", "large", "one_byte", "empty", "truncated",
    "corrupt_header", "wrong_ext_right_content", "right_ext_wrong_content",
    "password_protected", "multi_page", "zero_dim", "huge_dim",
    "special_filename", "read_only", "folder_with_spaces", "duplicate_names",
    "same_input_output"
)


class FixtureFactory:
    def __init__(self, base_dir: Path | str, seed: int = 42) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.seed = seed
        self.rng = random.Random(seed)

    def _get_ffmpeg(self) -> str:
        return str(imageio_ffmpeg.get_ffmpeg_exe())

    def _create_minimal_pdf(self, path: Path) -> Path:
        doc = pymupdf.open()
        p = doc.new_page(width=100, height=100)
        p.insert_text((10, 20), "A", fontsize=10)
        doc.save(str(path))
        doc.close()
        return path

    def _create_typical_pdf(self, path: Path) -> Path:
        doc = pymupdf.open()
        for i in range(1, 4):
            p = doc.new_page(width=612, height=792)
            p.insert_text((72, 72), f"Page {i}", fontsize=14)
            p.insert_text((72, 100), "Sample body text for test.", fontsize=10)
        doc.save(str(path))
        doc.close()
        return path

    def _create_multi_page_pdf(self, path: Path) -> Path:
        doc = pymupdf.open()
        for i in range(1, 10):
            p = doc.new_page(width=612, height=792)
            p.insert_text((72, 72), f"Multi Page {i}", fontsize=14)
        doc.save(str(path))
        doc.close()
        return path

    def _create_pw_pdf(self, path: Path) -> Path:
        doc = pymupdf.open()
        p = doc.new_page(width=200, height=200)
        p.insert_text((20, 40), "Secret Content", fontsize=12)
        doc.save(str(path), encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="owner")
        doc.close()
        return path

    def _create_scanned_pdf(self, path: Path) -> Path:
        img = Image.new("RGB", (300, 400), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "Scanned Sample Text 123", fill=(0, 0, 0))
        tmp_img = path.with_suffix(".temp.png")
        img.save(str(tmp_img))
        doc = pymupdf.open()
        p = doc.new_page(width=300, height=400)
        p.insert_image(p.rect, filename=str(tmp_img))
        doc.save(str(path))
        doc.close()
        if tmp_img.exists():
            tmp_img.unlink()
        return path

    def _create_image(self, path: Path, fmt: str, size: tuple[int, int] = (64, 64)) -> Path:
        mode = "RGBA" if fmt.lower() in ("png", "webp") else "RGB"
        img = Image.new(mode, size, color=(100, 150, 200, 255) if mode == "RGBA" else (100, 150, 200))
        if size[0] > 10 and size[1] > 10:
            draw = ImageDraw.Draw(img)
            draw.rectangle([5, 5, min(size[0] - 5, 20), min(size[1] - 5, 20)], fill=(200, 50, 50))
        if fmt.lower() == "gif":
            img2 = Image.new("P", size, color=50)
            img.convert("P").save(str(path), save_all=True, append_images=[img2], duration=100, loop=0)
        else:
            save_fmt = "JPEG" if fmt.upper() == "JPG" else fmt.upper()
            img.save(str(path), format=save_fmt)
        return path

    def _create_audio(self, path: Path, fmt: str, duration_s: float = 0.5) -> Path:
        wav_path = path.with_suffix(".tmp.wav")
        sample_rate = 22050
        num_samples = int(sample_rate * duration_s)
        with wave.open(str(wav_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            for idx in range(num_samples):
                val = int(16000.0 * math.sin(2.0 * math.pi * 440.0 * (idx / sample_rate)))
                wf.writeframes(struct.pack("<h", val))
        if fmt.lower() == "wav":
            if path.exists():
                path.unlink()
            wav_path.rename(path)
            return path
        ffmpeg = self._get_ffmpeg()
        cmd = [ffmpeg, "-y", "-i", str(wav_path), "-vn", str(path)]
        subprocess.run(cmd, capture_output=True, check=False)
        if wav_path.exists():
            wav_path.unlink()
        if not path.exists():
            path.write_bytes(b"ID3" + b"\x00" * 100)
        return path

    def _create_video(self, path: Path, fmt: str, duration_s: float = 0.5) -> Path:
        ffmpeg = self._get_ffmpeg()
        cmd = [
            ffmpeg, "-y", "-f", "lavfi",
            f"-i", f"testsrc=duration={duration_s}:size=64x64:rate=10",
            "-shortest", str(path)
        ]
        subprocess.run(cmd, capture_output=True, check=False)
        if not path.exists():
            path.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64)
        return path

    def _create_3d(self, path: Path, fmt: str) -> Path:
        box = trimesh.creation.box(extents=(2.0, 2.0, 2.0))
        fmt_clean = "stl" if "stl" in fmt.lower() else fmt.lower()
        box.export(str(path), file_type=fmt_clean)
        return path

    def _create_docx(self, path: Path) -> Path:
        doc = docx.Document()
        doc.add_heading("Docx Title", 0)
        doc.add_paragraph("Paragraph content here.")
        doc.save(str(path))
        return path

    def _create_xlsx(self, path: Path) -> Path:
        wb = openpyxl.Workbook()
        ws = wb.active
        if ws:
            ws.title = "Data"
            ws.append(["ID", "Name", "Score"])
            ws.append([1, "ItemA", 95.5])
        wb.save(str(path))
        return path

    def _create_pptx(self, path: Path) -> Path:
        prs = pptx.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = "Presentation Title"
        prs.save(str(path))
        return path

    def _create_zip(self, path: Path, password: str | None = None) -> Path:
        with zipfile.ZipFile(str(path), "w") as zf:
            zf.writestr("test.txt", "Content inside archive")
            zf.writestr("sub/doc.txt", "Nested document")
        return path

    def create(self, family: str, variant: str = "typical") -> Path:
        fam = family.lower().replace(".", "")
        var = variant.lower()

        out_name = f"{fam}_{var}.{fam}"
        target = self.base_dir / out_name

        if var == "special_filename":
            target = self.base_dir / f"{fam}_unicode_file_#1.{fam}"
        elif var == "folder_with_spaces":
            sp_dir = self.base_dir / "Folder With Spaces"
            sp_dir.mkdir(parents=True, exist_ok=True)
            target = sp_dir / f"{fam}_spaced.{fam}"
        elif var == "empty":
            target.write_bytes(b"")
            return target
        elif var == "one_byte":
            target.write_bytes(b"X")
            return target
        elif var == "corrupt_header":
            target.write_bytes(b"CORRUPT_HEADER_XYZ\x00\xff\xfe")
            return target
        elif var == "truncated":
            valid = self.create(family, "minimal_valid")
            data = valid.read_bytes()
            target.write_bytes(data[:max(1, len(data) // 4)])
            return target
        elif var == "wrong_ext_right_content":
            wrong_name = f"{fam}_wrongext.txt" if fam != "txt" else f"{fam}_wrongext.jpg"
            target = self.base_dir / wrong_name
            valid = self.create(family, "minimal_valid")
            target.write_bytes(valid.read_bytes())
            return target
        elif var == "right_ext_wrong_content":
            target.write_text("Plain text content in mismatched extension", encoding="utf-8")
            return target
        elif var == "duplicate_names":
            target = self.base_dir / f"duplicate_{fam}.{fam}"
            valid = self.create(family, "minimal_valid")
            target.write_bytes(valid.read_bytes())
            return target

        if fam == "pdf":
            if var == "password_protected":
                self._create_pw_pdf(target)
            elif var == "multi_page":
                self._create_multi_page_pdf(target)
            elif var == "minimal_valid":
                self._create_minimal_pdf(target)
            else:
                self._create_typical_pdf(target)
        elif fam == "scanned_pdf":
            self._create_scanned_pdf(target)
        elif fam in ("png", "jpg", "webp", "bmp", "tiff", "gif"):
            sz = (16, 16) if var == "minimal_valid" else (500, 500) if var == "large" else (64, 64)
            self._create_image(target, fam, sz)
        elif fam == "svg":
            target.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50"><circle cx="25" cy="25" r="20" fill="red"/></svg>', encoding="utf-8")
        elif fam in ("heic", "raw", "psd"):
            self._create_image(target, "png", (32, 32))
        elif fam in ("mp4", "mov", "mkv", "webm"):
            self._create_video(target, fam, duration_s=0.2 if var == "minimal_valid" else 0.5)
        elif fam in ("mp3", "wav", "flac", "aac", "ogg"):
            self._create_audio(target, fam, duration_s=0.2 if var == "minimal_valid" else 0.5)
        elif fam == "docx":
            self._create_docx(target)
        elif fam == "xlsx":
            self._create_xlsx(target)
        elif fam == "pptx":
            self._create_pptx(target)
        elif fam in ("csv", "tsv"):
            delim = "\t" if fam == "tsv" else ","
            rows = ["id" + delim + "val", "1" + delim + "alpha", "2" + delim + "beta"]
            target.write_text("\n".join(rows) + "\n", encoding="utf-8")
        elif fam == "json":
            target.write_text(json.dumps({"key": "val", "num": 42, "items": [1, 2]}), encoding="utf-8")
        elif fam == "yaml":
            target.write_text(yaml.dump({"project": "FOSSEverything", "status": True}), encoding="utf-8")
        elif fam == "toml":
            target.write_text(toml.dumps({"section": {"key": "val"}}), encoding="utf-8")
        elif fam == "xml":
            target.write_text("<root><item id='1'>Text</item></root>", encoding="utf-8")
        elif fam in ("h5", "hdf5"):
            import h5py
            with h5py.File(str(target), "w") as hf:
                hf.create_dataset("numbers", data=[1, 2, 3, 4])
        elif fam in ("txt", "md"):
            target.write_text(f"# Header\nSample content for {fam}\n", encoding="utf-8")
        elif fam in ("stl", "obj", "ply", "gltf"):
            self._create_3d(target, fam)
        elif fam == "step":
            target.write_text("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('STEP'),'2;1');\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n", encoding="utf-8")
        elif fam in ("zip", "tar", "gz", "7z"):
            self._create_zip(target)
        elif fam in ("srt", "vtt"):
            target.write_text("1\n00:00:01,000 --> 00:00:02,000\nSubtitle text\n", encoding="utf-8")
        elif fam in ("m3u", "m3u8"):
            target.write_text("#EXTM3U\n#EXTINF:120,Artist - Track\ntrack.mp3\n", encoding="utf-8")
        elif fam == "ics":
            target.write_text("BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:Meeting\nEND:VEVENT\nEND:VCALENDAR\n", encoding="utf-8")
        elif fam == "epub":
            self._create_zip(target)
        elif fam in ("ttf", "otf", "woff", "woff2"):
            target.write_bytes(b"\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        elif fam == "enex":
            target.write_text("<?xml version='1.0'?><en-export><note><title>Note</title><content><![CDATA[<en-note>Hi</en-note>]]></content></note></en-export>", encoding="utf-8")
        elif fam == "sql":
            target.write_text("CREATE TABLE test (id INT, val TEXT);\nINSERT INTO test VALUES (1, 'val');\n", encoding="utf-8")
        elif fam == "js":
            target.write_text("function hello() { return 'world'; }\n", encoding="utf-8")
        elif fam == "css":
            target.write_text("body { margin: 0; padding: 0; }\n", encoding="utf-8")
        elif fam == "qr":
            img = qrcode.make("https://foss.local/matrix")
            img.save(str(target))
        else:
            target.write_bytes(b"DATA\x00" * 16)

        if var == "read_only":
            os.chmod(str(target), 0o444)
        elif var == "same_input_output":
            pass

        return target
