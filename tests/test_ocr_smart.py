from pathlib import Path
import pytest
import pymupdf
from app.features.ocr.ops import (
    parse_page_selection,
    create_searchable_pdf,
    expand_ocr_inputs,
)
from app.web.api.tool_ocr import OcrApiMixin


class MockWebApi(OcrApiMixin):
    def __init__(self) -> None:
        self.active_jobs: dict[str, dict[str, object]] = {}


def test_parse_page_selection() -> None:
    # Test valid page selections.
    assert parse_page_selection(None, 10) == list(range(1, 11))
    assert parse_page_selection("", 10) == list(range(1, 11))
    assert parse_page_selection("all", 5) == [1, 2, 3, 4, 5]
    assert parse_page_selection("*", 3) == [1, 2, 3]
    assert parse_page_selection("3", 10) == [3]
    assert parse_page_selection("2-4", 10) == [2, 3, 4]
    assert parse_page_selection("1-2, 5, 7-8", 10) == [1, 2, 5, 7, 8]
    assert parse_page_selection(" 1 - 3 , 2 - 4 ", 10) == [1, 2, 3, 4]

    # Test invalid page selections.
    with pytest.raises(ValueError):
        parse_page_selection("abc", 10)
    with pytest.raises(ValueError):
        parse_page_selection("5-2", 10)
    with pytest.raises(ValueError):
        parse_page_selection("0", 10)
    with pytest.raises(ValueError):
        parse_page_selection("11", 10)
    with pytest.raises(ValueError):
        parse_page_selection("2-15", 10)


def test_create_searchable_pdf_smart_preservation(tmp_path: Path) -> None:
    # Build 3-page test PDF: p1 text, p2 raster image, p3 text.
    src_pdf = tmp_path / "three_page.pdf"
    doc = pymupdf.open()

    page1 = doc.new_page(width=300, height=300)
    page1.insert_text((50, 50), "Alpha vector text line")

    page2 = doc.new_page(width=300, height=300)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 120, 120), 1)
    pix.clear_with(255)
    page2.insert_image(pymupdf.Rect(40, 40, 160, 160), pixmap=pix)

    page3 = doc.new_page(width=300, height=300)
    page3.insert_text((50, 50), "Gamma vector text line")

    doc.save(str(src_pdf))
    doc.close()

    out_pdf = tmp_path / "searchable_out.pdf"
    create_searchable_pdf(
        str(src_pdf),
        str(out_pdf),
        pages=[2],
        force_overwrite=False,
    )

    out_doc = pymupdf.open(str(out_pdf))
    try:
        assert len(out_doc) == 3
        # Page 1 and 3 should retain exact vector text.
        text_p1 = out_doc[0].get_text("text").strip()
        text_p3 = out_doc[2].get_text("text").strip()
        assert "Alpha vector text line" in text_p1
        assert "Gamma vector text line" in text_p3
    finally:
        out_doc.close()


def test_ocr_recognize_file_returns_str(tmp_path: Path) -> None:
    # Verify ocr_recognize_file returns string in text field.
    src_pdf = tmp_path / "single.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=300)
    page.insert_text((50, 50), "Searchable sample contents")
    doc.save(str(src_pdf))
    doc.close()

    api = MockWebApi()
    res = api.ocr_recognize_file({"file_path": str(src_pdf), "force_overwrite": False})
    assert res.get("ok") is True
    assert isinstance(res.get("text"), str)
    assert not isinstance(res.get("text"), dict)
    assert "Searchable sample contents" in str(res.get("text"))


def test_ocr_batch_folder_support(tmp_path: Path) -> None:
    # Verify folder expansion and default output path fallback.
    folder = tmp_path / "batch_input"
    folder.mkdir()
    sample_pdf = folder / "item1.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=300)
    page.insert_text((50, 50), "Batch item text")
    doc.save(str(sample_pdf))
    doc.close()

    expanded = expand_ocr_inputs([str(folder)], recursive=True)
    assert str(sample_pdf) in expanded

    api = MockWebApi()
    res = api.ocr_batch({
        "file_paths": [str(folder)],
        "format": "txt",
        "output_dir": "",
    })
    assert res.get("ok") is True
    out_txt = folder / "item1_ocr.txt"
    assert out_txt.exists()
    assert "Batch item text" in out_txt.read_text(encoding="utf-8")

