from pathlib import Path
from typing import Any, Callable
from playwright.sync_api import Page, expect


def calc_clear_overlays(page: Page) -> None:
    # Clear tooltips, toasts, and reset view scroll.
    page.evaluate(
        "if (window.FOSS && window.FOSS.tooltips) window.FOSS.tooltips.hide(); "
        "var t = document.getElementById('tooltip-host'); if (t) t.innerHTML = ''; "
        "var h = document.getElementById('toast-host'); if (h) h.innerHTML = ''; "
        "var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;"
    )


def scenario_merge(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Merge multiple PDF documents and verify result card.
    sample1 = fixtures.get("sample.pdf", "sample.pdf")
    sample2 = fixtures.get("scan.pdf", sample1)
    out_file = str(Path(sample1).parent / "out_merged.pdf")
    api._dialog_answers.append([sample1, sample2])
    api._dialog_answers.append(out_file)

    page.evaluate("window.FOSS.router.open('pdf', 'merge')")
    page.click("[data-testid='pdf-add-files-btn']")
    page.wait_for_timeout(200)

    page.click("[data-testid='pdf-merge-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='pdf-merge-result']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_organize(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Load PDF, rotate page, and stamp page numbers.
    sample = fixtures.get("sample.pdf", "sample.pdf")
    out_file = str(Path(sample).parent / "out_numbered.pdf")
    api._dialog_answers.append(sample)
    api._dialog_answers.append(out_file)

    page.evaluate("window.FOSS.router.open('pdf', 'organize')")
    page.click("[data-testid='pdf-organize-picker-browse']")
    page.wait_for_timeout(300)

    page.click("[data-testid='pdf-rotate-cw-btn']")
    page.wait_for_timeout(100)

    page.click("[data-testid='pdf-add-numbers-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='pdf-organize-result']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_split(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Split PDF into pages and verify completion.
    sample = fixtures.get("sample.pdf", "sample.pdf")
    out_dir = str(Path(sample).parent / "split_dir")
    api._dialog_answers.append(sample)
    api._dialog_answers.append(out_dir)

    page.evaluate("window.FOSS.router.open('pdf', 'split')")
    page.click("[data-testid='pdf-split-picker-browse']")
    page.wait_for_timeout(200)

    page.click("[data-testid='pdf-split-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='pdf-split-result']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_security(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Password protect PDF and verify security result presentation.
    sample = fixtures.get("sample.pdf", "sample.pdf")
    out_file = str(Path(sample).parent / "out_protected.pdf")
    api._dialog_answers.append(sample)
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


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("merge", scenario_merge),
    ("organize", scenario_organize),
    ("split", scenario_split),
    ("security", scenario_security),
]

