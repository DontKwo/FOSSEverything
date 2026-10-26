from pathlib import Path
from typing import Any, Callable
from playwright.sync_api import Page, expect


def calc_clear_overlays(page: Page) -> None:
    # Clear tooltips, toasts, and reset view scroll.
    try:
        page.mouse.move(0, 0)
    except Exception:
        pass
    page.evaluate(
        "if (window.FOSS && window.FOSS.tooltips) window.FOSS.tooltips.hide(); "
        "var t = document.getElementById('tooltip-host'); if (t) t.innerHTML = ''; "
        "var h = document.getElementById('toast-host'); if (h) h.innerHTML = ''; "
        "var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;"
    )


def scenario_document(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Extract OCR text from sample image and verify output area.
    sample = fixtures.get("sample.png", "sample.png")
    api._dialog_answers.append(sample)

    page.evaluate("window.FOSS.router.open('ocr', 'document')")
    page.click("[data-testid='ocr-file-picker-browse']")
    page.wait_for_timeout(200)

    page.click("[data-testid='ocr-extract-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='ocr-char-word-count']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_searchable_pdf(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Generate searchable PDF with embedded OCR layer.
    sample = fixtures.get("sample.png", "sample.png")
    out_pdf = str(Path(sample).parent / "out_searchable.pdf")
    api._dialog_answers.append(sample)
    api._dialog_answers.append(out_pdf)

    page.evaluate("window.FOSS.router.open('ocr', 'document')")
    page.click("[data-testid='ocr-file-picker-browse']")
    page.wait_for_timeout(200)

    page.click("[data-testid='ocr-make-pdf-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='ocr-result-host']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_batch(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Queue batch OCR items and run processing.
    sample1 = fixtures.get("sample.png", "sample.png")
    sample2 = fixtures.get("sample2.png", sample1)
    out_dir = str(Path(sample1).parent)
    api._dialog_answers.append([sample1, sample2])

    page.evaluate("window.FOSS.router.open('ocr', 'batch')")
    page.click("[data-testid='ocr-batch-add-btn']")
    page.wait_for_timeout(200)

    page.fill("[data-testid='ocr-batch-out-folder']", out_dir)
    page.click("[data-testid='ocr-run-batch-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='ocr-batch-result']")).to_be_visible()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("document", scenario_document),
    ("searchable_pdf", scenario_searchable_pdf),
    ("batch", scenario_batch),
]
