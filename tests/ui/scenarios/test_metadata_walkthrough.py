from pathlib import Path
from typing import Any

from playwright.sync_api import Page


def test_metadata_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    # Test metadata extraction and stripping tools
    fixtures_dir = Path("tests/ui/_fixtures")
    sample_docx = str(fixtures_dir / "sample.docx")
    meta_out = str(tmp_path / "out_meta.docx")

    api._dialog_answers.extend([sample_docx, meta_out])
    page.evaluate("window.FOSS.router.open('metadata', 'strip')")

    page.click("[data-testid='metadata-choose-file']")
    page.click("[data-testid='metadata-strip-btn']")
    page.wait_for_timeout(200)

    assert Path(meta_out).exists()
