from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect


def test_archive_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    # Walkthrough of complete navigation, interaction, and rendering of archive tool.
    fixtures_dir = Path("tests/ui/_fixtures")
    sample_txt = str(fixtures_dir / "sample.txt")
    sample_zip = str(fixtures_dir / "sample.zip")

    # 1. Create Archive
    out_arc = str(tmp_path / "out_arc.zip")
    api._dialog_answers.append([sample_txt])
    api._dialog_answers.append(out_arc)
    page.evaluate("window.FOSS.router.open('archive', 'create')")

    page.click("[data-testid='archive-add-files-btn']")
    page.wait_for_timeout(300)
    page.click("[data-testid='archive-create-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='archive-create-result']")).to_be_visible()
    assert Path(out_arc).exists()

    # 2. Extract Archive
    out_dir = str(tmp_path / "extracted")
    Path(out_dir).mkdir(exist_ok=True)
    api._dialog_answers.append(sample_zip)
    api._dialog_answers.append(out_dir)
    page.evaluate("window.FOSS.router.open('archive', 'extract')")

    page.click("[data-testid='archive-extract-choose']")
    page.wait_for_timeout(300)
    page.click("[data-testid='archive-extract-browse']")
    page.wait_for_timeout(300)
    page.click("[data-testid='archive-extract-run-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='archive-extract-result']")).to_be_visible()
    assert (Path(out_dir) / "inner.txt").exists()

    # 3. Inspect Archive
    api._dialog_answers.append(sample_zip)
    page.evaluate("window.FOSS.router.open('archive', 'inspect')")

    page.click("[data-testid='archive-inspect-choose']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='archive-member-table'] table")).to_be_visible()

    page.click("[data-testid='archive-test-integrity-btn']")
    page.wait_for_timeout(300)
    expect(page.locator("[data-testid='archive-inspect-status']")).to_contain_text(
        "Integrity check passed"
    )
    expect(page.locator("[data-testid='archive-sha256-readout']")).not_to_contain_text("not computed")
