from pathlib import Path
from typing import Any
from playwright.sync_api import Page, expect


def calc_clear_overlays(page: Page) -> None:
    # Clear tooltips, toasts, and reset view scroll.
    try:
        page.mouse.move(0, 0)
    except Exception:
        page.wait_for_timeout(0)
    page.evaluate(
        "if (window.FOSS && window.FOSS.tooltips) window.FOSS.tooltips.hide(); "
        "var t = document.getElementById('tooltip-host'); if (t) t.innerHTML = ''; "
        "var h = document.getElementById('toast-host'); if (h) h.innerHTML = ''; "
        "document.querySelectorAll('.tool-panel-container, #view-root, .workbench, .page, .scroll-main').forEach(function (el) { el.scrollTop = 0; el.scrollLeft = 0; });"
    )


def test_ocr_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    # Run all OCR UI scenarios in sequence directly inside this test.
    fixtures_dir = Path("tests/ui/_fixtures")
    sample1 = str(fixtures_dir / "sample.png")
    sample2 = str(fixtures_dir / "sample2.png") if (fixtures_dir / "sample2.png").exists() else sample1

    # --- Scenario: Document ---
    api._dialog_answers.append(sample1)
    page.evaluate("window.FOSS.router.open('ocr', 'document')")
    page.click("[data-testid='ocr-file-picker-browse']")
    page.wait_for_timeout(200)

    page.click("[data-testid='ocr-extract-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='ocr-char-word-count']")).to_be_visible()
    text_val = page.input_value("[data-testid='ocr-text-result']")
    assert "object Object" not in text_val
    calc_clear_overlays(page)

    # --- Scenario: Searchable PDF ---
    out_pdf = str(tmp_path / "out_searchable.pdf")
    api._dialog_answers.append(sample1)
    api._dialog_answers.append(out_pdf)

    page.evaluate("window.FOSS.router.open('ocr', 'document')")
    page.click("[data-testid='ocr-file-picker-browse']")
    page.wait_for_timeout(200)

    page.click("[data-testid='ocr-make-pdf-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='ocr-result-host']")).to_be_visible()
    assert Path(out_pdf).exists()
    calc_clear_overlays(page)

    # --- Scenario: Batch ---
    folder_path = str(fixtures_dir)
    out_dir = str(tmp_path)
    api._dialog_answers.append([sample1, sample2])
    api._dialog_answers.append(folder_path)

    page.evaluate("window.FOSS.router.open('ocr', 'batch')")
    page.click("[data-testid='ocr-batch-add-btn']")
    page.wait_for_timeout(200)

    expect(page.locator("[data-testid='ocr-batch-add-folder-btn']")).to_be_visible()
    page.click("[data-testid='ocr-batch-add-folder-btn']")
    page.wait_for_timeout(200)

    page.fill("[data-testid='ocr-batch-out-folder']", out_dir)
    page.click("[data-testid='ocr-run-batch-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='ocr-batch-result-card']")).to_be_visible()
    calc_clear_overlays(page)
