import os
from pathlib import Path
import docx
import pymupdf
from app.features.resume.ops import (
    create_sample_master_resume,
    export_docx,
    export_pdf,
    render_resume_preview_pages,
)
from app.web.api.tool_resume import ResumeApiMixin


class MockWebApi(ResumeApiMixin):
    def __init__(self) -> None:
        self.active_jobs: dict[str, dict[str, object]] = {}


def test_resume_export_pdf_gnc_geometry(tmp_path: Path) -> None:
    # Verify export_pdf produces US Letter geometry with exact GNC elements.
    sample = create_sample_master_resume()
    out_pdf = str(tmp_path / "resume_test.pdf")
    res_path = export_pdf(sample, out_pdf)
    assert os.path.exists(res_path)

    doc = pymupdf.open(res_path)
    try:
        assert len(doc) >= 1
        page = doc[0]
        # US Letter dimensions: 612 x 792 pt
        assert page.rect.width == 612.0
        assert page.rect.height == 792.0

        # Check candidate name in uppercase
        text = page.get_text().replace("\xa0", " ")
        assert "ALEX MORGAN" in text

        # Check section titles and entries
        assert "EDUCATION" in text
        assert "WORK EXPERIENCE" in text
        assert "Space Exploration Technologies (SpaceX)" in text
        assert "December 2026" in text
        assert "3.94 / 4.00" in text

        # Check drawings for 2.0 pt horizontal rules
        drawings = page.get_drawings()
        rule_lines = [
            d for d in drawings
            if d.get("width") == 2.0 and d.get("type") in ("s", "fs")
        ]
        # Verify horizontal rules span from margin_left=54 to margin_right=558
        matching_rules = []
        for d in drawings:
            if d.get("width") == 2.0:
                for item in d.get("items", []):
                    if item[0] == "l":
                        p1, p2 = item[1], item[2]
                        if abs(p1.x - 54.0) < 1.0 and abs(p2.x - 558.0) < 1.0:
                            matching_rules.append(item)
        assert len(matching_rules) >= 1

        # Check words and right-aligned date position
        words = page.get_text("words")
        date_words = [w for w in words if "December" in w[4] or "2026" in w[4]]
        assert len(date_words) > 0
        max_date_x1 = max(w[2] for w in date_words)
        # Verify right-aligned date is flush to right margin (558.0 +- 1.5)
        assert abs(max_date_x1 - 558.0) < 2.0
    finally:
        doc.close()


def test_resume_export_docx_formatting(tmp_path: Path) -> None:
    # Verify export_docx produces valid Word document with all sections.
    sample = create_sample_master_resume()
    out_docx = str(tmp_path / "resume_test.docx")
    res_path = export_docx(sample, out_docx)
    assert os.path.exists(res_path)

    doc = docx.Document(res_path)
    full_text = "\n".join([p.text for p in doc.paragraphs])
    assert "ALEX MORGAN" in full_text
    assert "EDUCATION" in full_text
    assert "WORK EXPERIENCE" in full_text
    assert "Space Exploration Technologies (SpaceX)" in full_text
    assert "3.94 / 4.00" in full_text
    assert "Simulation & Analysis" in full_text


def test_resume_render_preview_api() -> None:
    # Verify render_resume_preview_pages and API endpoint return PNG pages.
    sample = create_sample_master_resume()
    preview_data = render_resume_preview_pages(sample, dpi=120)
    assert preview_data.get("page_count", 0) >= 1
    pages = preview_data.get("pages", [])
    assert len(pages) >= 1
    assert pages[0].startswith("data:image/png;base64,")

    api = MockWebApi()
    res = api.resume_render_preview({"resume": sample, "dpi": 100})
    assert res.get("ok") is True
    assert res.get("page_count", 0) >= 1
    assert len(res.get("pages", [])) >= 1

