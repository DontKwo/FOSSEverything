from __future__ import annotations

import csv
from pathlib import Path

import docx
import openpyxl
from PIL import Image

from app.web.api import WebApi


def _make_docx(path: Path) -> None:
    # Write a one paragraph DOCX file.
    document = docx.Document()
    document.add_paragraph("Batch office paragraph")
    document.save(str(path))


def _make_xlsx(path: Path) -> None:
    # Write a two row XLSX workbook.
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(["name", "qty"])
    sheet.append(["apple", 3])
    book.save(str(path))


def test_batch_office_docx_pdf_and_xlsx_csv(tmp_path: Path) -> None:
    # Batch run converts DOCX to PDF and XLSX to CSV through batch_convert_files.
    api = WebApi()
    src = tmp_path / "src"
    src.mkdir()
    _make_docx(src / "memo.docx")
    _make_xlsx(src / "table.xlsx")
    out_dir = tmp_path / "out"

    targets = api.converter_available_targets({"file_path": str(src / "memo.docx")})
    assert "PDF" in targets["targets"]
    targets = api.converter_available_targets({"file_path": str(src / "table.xlsx")})
    assert "CSV" in targets["targets"]

    res = api.converter_batch_convert({
        "items": [
            {"path": str(src / "memo.docx"), "target_format": "PDF"},
            {"path": str(src / "table.xlsx"), "target_format": "CSV"},
        ],
        "output_dir": str(out_dir),
    })
    assert res["ok"] is True
    assert res["succeeded"] == 2
    assert (out_dir / "memo.pdf").read_bytes().startswith(b"%PDF")
    with open(out_dir / "table.csv", newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["name", "qty"]
    assert rows[1][0] == "apple"


def test_batch_reports_failures_in_input_order(tmp_path: Path) -> None:
    # A failing item keeps its slot in the ordered results list.
    api = WebApi()
    img = tmp_path / "pic.png"
    Image.new("RGB", (8, 8), "red").save(str(img))
    res = api.converter_batch_convert({
        "items": [
            {"path": str(tmp_path / "missing.docx"), "target_format": "PDF"},
            {"path": str(img), "target_format": "JPEG"},
        ],
        "output_dir": str(tmp_path / "out"),
    })
    assert [row["ok"] for row in res["results"]] == [False, True]
    assert res["succeeded"] == 1
    assert res["failed"] == 1


def test_single_convert_follows_chosen_output_extension(tmp_path: Path) -> None:
    # Output file lands exactly on the chosen path with the chosen format.
    api = WebApi()
    img = tmp_path / "pic.png"
    Image.new("RGB", (8, 8), "blue").save(str(img))
    target = tmp_path / "result.jpg"
    res = api.converter_convert_file({"file_path": str(img), "output_path": str(target), "target_format": "JPEG", "quality": 40})
    assert res["ok"] is True
    assert target.exists()
    with Image.open(target) as opened:
        assert opened.format == "JPEG"
