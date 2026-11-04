from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect


def test_compressor_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    # Test complete navigation, interaction, and rendering of the File Compressor tool.
    fixtures_dir = Path("tests/ui/_fixtures")
    sample_png = str(fixtures_dir / "sample.png")

    comp_out = str(tmp_path / "out_comp.png")
    api._dialog_answers.extend([[sample_png], comp_out])

    # 1. Open File Compressor tool and verify ready state.
    page.evaluate("window.FOSS.router.open('compressor', 'single')")
    status = page.locator("[data-testid='compressor-status']")
    expect(status).to_have_text("Ready")
    btn = page.locator("[data-testid='compressor-run-btn']")
    expect(btn).to_be_disabled()

    # 2. Queue file fixture and execute compression run.
    page.click("[data-testid='compressor-choose-file']")
    page.wait_for_timeout(250)

    tbl = page.locator("[data-testid='compressor-queue-table'] table")
    expect(tbl).to_be_visible()

    page.click("[data-testid='compressor-run-btn']")
    page.wait_for_timeout(350)
    status = page.locator("[data-testid='compressor-status']")
    expect(status).to_contain_text("Compression complete")

    # 3. Clear queue
    page.click("[data-testid='compressor-clear-btn']")
    page.wait_for_timeout(200)
    btn = page.locator("[data-testid='compressor-run-btn']")
    expect(btn).to_be_disabled()
