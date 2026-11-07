from pathlib import Path
from typing import Any
from playwright.sync_api import Page, expect


def calc_clear_overlays(page: Page) -> None:
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


def test_pdf_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    fixtures_dir = Path("tests/ui/_fixtures")
    sample_pdf = str(fixtures_dir / "sample.pdf")
    scan_pdf = str(fixtures_dir / "scan.pdf")

    # scenario_merge
    out_file = str(tmp_path / "out_merged.pdf")
    api._dialog_answers.append([sample_pdf, scan_pdf])
    api._dialog_answers.append(out_file)

    page.evaluate("window.FOSS.router.open('pdf', 'merge')")
    page.locator(
        "[data-testid='pdf-merge-add-btn'], [data-testid='pdf-add-files-btn']"
    ).first.click()
    page.wait_for_timeout(200)

    page.locator(
        "[data-testid='pdf-merge-save-btn'], [data-testid='pdf-merge-btn']"
    ).first.click()
    page.wait_for_timeout(300)

    expect(
        page.locator("[data-testid='pdf-merge-result'], .toast-message").first
    ).to_be_visible()
    calc_clear_overlays(page)

    # scenario_organize
    out_file = str(tmp_path / "out_numbered.pdf")
    api._dialog_answers.append([sample_pdf])
    api._dialog_answers.append(out_file)

    page.evaluate("window.FOSS.router.open('pdf', 'merge')")
    page.locator(
        "[data-testid='pdf-merge-add-btn'], [data-testid='pdf-add-files-btn']"
    ).first.click()
    page.wait_for_timeout(300)

    page.click("[data-testid='pdf-select-all-btn']")
    page.wait_for_timeout(100)

    page.click("[data-testid='pdf-rotate-cw-btn']")
    page.wait_for_timeout(100)

    page.click("[data-testid='pdf-stamp-numbers-check']")
    page.wait_for_timeout(100)

    page.locator(
        "[data-testid='pdf-merge-save-btn'], [data-testid='pdf-merge-btn']"
    ).first.click()
    page.wait_for_timeout(300)

    expect(
        page.locator("[data-testid='pdf-merge-result'], .toast-message").first
    ).to_be_visible()
    calc_clear_overlays(page)

    # scenario_split
    out_dir = str(tmp_path / "split_dir")
    api._dialog_answers.append(sample_pdf)
    api._dialog_answers.append(out_dir)

    page.evaluate("window.FOSS.router.open('pdf', 'split')")
    page.click("[data-testid='pdf-split-picker-browse']")
    page.wait_for_timeout(200)

    page.click("[data-testid='pdf-split-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='pdf-split-result']")).to_be_visible()
    calc_clear_overlays(page)

    # scenario_security
    out_file = str(tmp_path / "out_protected.pdf")
    api._dialog_answers.append(sample_pdf)
    api._dialog_answers.append(out_file)

    page.evaluate("window.FOSS.router.open('pdf', 'security')")
    page.click("[data-testid='pdf-security-picker-browse']")
    page.wait_for_timeout(200)

    page.fill("[data-testid='pdf-protect-password']", "pass123")
    page.fill("[data-testid='pdf-repeat-password']", "pass123")

    page.click("[data-testid='pdf-protect-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='pdf-security-result']")).to_be_visible()
    calc_clear_overlays(page)
