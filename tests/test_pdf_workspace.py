import os
from pathlib import Path
import pytest
import pymupdf
from app.features.pdf.ops import (
    assemble_pdf_workspace,
    export_pdf_groups,
    is_pdf_encrypted,
    parse_split_ranges,
)
from app.web.api.tool_pdf import PdfApiMixin


class MockWebApi(PdfApiMixin):
    def __init__(self) -> None:
        self.active_jobs: dict[str, dict[str, object]] = {}


def create_sample_pdf(path: Path, num_pages: int, prefix: str) -> str:
    # Helper to generate test PDF document with specific page counts.
    doc = pymupdf.open()
    for idx in range(num_pages):
        page = doc.new_page(width=300, height=300)
        page.insert_text((50, 50), f"{prefix} page {idx + 1}")
    doc.save(str(path))
    doc.close()
    return str(path)


def test_parse_split_ranges() -> None:
    # Test range parsing for splitting.
    assert parse_split_ranges("1", 5) == [(1, 1)]
    assert parse_split_ranges("3", 5) == [(3, 3)]
    assert parse_split_ranges("1-3, 5", 5) == [(1, 3), (5, 5)]
    assert parse_split_ranges("all", 3) == [(1, 1), (2, 2), (3, 3)]
    assert parse_split_ranges("every", 2) == [(1, 1), (2, 2)]

    with pytest.raises(ValueError):
        parse_split_ranges("abc", 5)
    with pytest.raises(ValueError):
        parse_split_ranges("5-2", 5)
    with pytest.raises(ValueError):
        parse_split_ranges("9", 5)


def test_assemble_pdf_workspace_interleaving_and_rotation(tmp_path: Path) -> None:
    # Verify multi-doc interleaving, page rotation, and duplicate page handling.
    doc_a_path = create_sample_pdf(tmp_path / "doc_a.pdf", 3, "DocA")
    doc_b_path = create_sample_pdf(tmp_path / "doc_b.pdf", 2, "DocB")

    sources = {
        "src_a": doc_a_path,
        "src_b": doc_b_path,
    }

    # Interleaved spec: DocA p1 (90 rot), DocB p2 (180 rot), DocA p1 (duplicate, 0 rot)
    pages_spec = [
        {"source_id": "src_a", "page": 1, "rotation": 90},
        {"source_id": "src_b", "page": 2, "rotation": 180},
        {"source_id": "src_a", "page": 1, "rotation": 0},
    ]

    out_path = str(tmp_path / "assembled.pdf")
    page_numbers = {
        "enabled": True,
        "format": "Page {n} of {total}",
        "position": "bottom_center",
        "start_num": 1,
    }

    result_path = assemble_pdf_workspace(sources, pages_spec, out_path, page_numbers=page_numbers)
    assert os.path.exists(result_path)

    doc = pymupdf.open(result_path)
    try:
        assert len(doc) == 3
        # Page 1: rotation 90, contains DocA page 1
        assert doc[0].rotation == 90
        assert "DocA page 1" in doc[0].get_text()
        # Page 2: rotation 180, contains DocB page 2
        assert doc[1].rotation == 180
        assert "DocB page 2" in doc[1].get_text()
        # Page 3: rotation 0, contains DocA page 1
        assert doc[2].rotation == 0
        assert "DocA page 1" in doc[2].get_text()
        # Verify page number stamp
        assert "Page 1 of 3" in doc[0].get_text()
        assert "Page 2 of 3" in doc[1].get_text()
        assert "Page 3 of 3" in doc[2].get_text()
    finally:
        doc.close()


def test_export_pdf_groups(tmp_path: Path) -> None:
    # Verify export_pdf_groups outputs individual PDFs per named group.
    doc_path = create_sample_pdf(tmp_path / "multi.pdf", 4, "Item")
    sources = {"src_1": doc_path}

    groups = [
        {
            "name": "Cover & Intro",
            "pages": [
                {"source_id": "src_1", "page": 1, "rotation": 0},
                {"source_id": "src_1", "page": 2, "rotation": 0},
            ],
        },
        {
            "name": "Appendix",
            "pages": [
                {"source_id": "src_1", "page": 3, "rotation": 0},
                {"source_id": "src_1", "page": 4, "rotation": 90},
            ],
        },
    ]

    out_dir = str(tmp_path / "exported_groups")
    exported = export_pdf_groups(sources, groups, out_dir)
    assert len(exported) == 2
    assert (tmp_path / "exported_groups" / "Cover___Intro.pdf").exists()
    assert (tmp_path / "exported_groups" / "Appendix.pdf").exists()


def test_pdf_protect_and_unlock_arguments(tmp_path: Path) -> None:
    # Verify pdf_protect and pdf_unlock write to expected file path with correct password.
    src_path = create_sample_pdf(tmp_path / "to_protect.pdf", 2, "Secure")
    protected_path = str(tmp_path / "protected.pdf")
    unlocked_path = str(tmp_path / "unlocked.pdf")
    password = "secret_password"

    api = MockWebApi()
    protect_res = api.pdf_protect({
        "file_path": src_path,
        "output_path": protected_path,
        "password": password,
    })
    assert protect_res.get("ok") is True
    assert protect_res.get("output_path") == protected_path
    assert os.path.exists(protected_path)
    # Ensure no file named with the password string was accidentally created
    assert not os.path.exists(password)
    assert is_pdf_encrypted(protected_path)

    unlock_res = api.pdf_unlock({
        "file_path": protected_path,
        "output_path": unlocked_path,
        "password": password,
    })
    assert unlock_res.get("ok") is True
    assert unlock_res.get("output_path") == unlocked_path
    assert os.path.exists(unlocked_path)
    assert not is_pdf_encrypted(unlocked_path)

