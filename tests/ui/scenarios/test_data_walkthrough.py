from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect

def test_data_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    # Walkthrough of Data Studio features.

    # 1. Format / Minify / Convert Tab
    data_out = str(tmp_path / "out_data.yaml")
    api._dialog_answers.append(data_out)
    page.evaluate("window.FOSS.router.open('data', 'format')")

    # Test formatting
    format_in = page.locator("[data-testid='data-editor-input-input']")
    format_in.fill('{"name": "test"}')
    page.click("[data-testid='data-format-btn']")
    page.wait_for_timeout(100)
    expect(page.locator("[data-testid='data-editor-status']")).not_to_have_text("Ready")

    # Test convert YAML
    page.click("[data-testid='data-convert-yaml-btn']")
    page.wait_for_timeout(100)

    # Test save
    page.click("[data-testid='data-save-btn']")
    page.wait_for_timeout(200)
    assert Path(data_out).exists()

    # 2. Structure Tab
    page.evaluate("window.FOSS.router.open('data', 'structure')")
    page.click("[data-testid='data-structure-toggle-text-btn']")
    struct_in = page.locator("[data-testid='data-structure-text-input-input']")
    struct_in.fill('{"tools": [{"name": "pdf", "rating": 5}, {"name": "ocr", "rating": 4}]}')
    page.click("[data-testid='data-structure-inspect-btn']")
    page.wait_for_timeout(100)
    expect(page.locator("[data-testid='data-structure-tree']")).to_be_visible()

    # 3. Tables Tab
    page.evaluate("window.FOSS.router.open('data', 'tables')")
    table_in = page.locator("[data-testid='data-tables-input-input']")
    table_in.fill("Col1,Col2\nval1,val2")
    page.click("[data-testid='data-tables-clean']")
    page.wait_for_timeout(100)
    expect(page.locator("[data-testid='data-tables-status']")).not_to_have_text("Ready")

    # 4. Utilities Tab
    page.evaluate("window.FOSS.router.open('data', 'utilities')")
    page.click("[data-testid='data-utilities-random-generate']")
    page.wait_for_timeout(100)
    rand_out = page.locator("[data-testid='data-utilities-random-output']")
    expect(rand_out).not_to_have_text("-")
