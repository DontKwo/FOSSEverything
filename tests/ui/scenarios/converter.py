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


def scenario_loaded(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open File Converter tool single tab and verify loaded state.
    page.evaluate("window.FOSS.router.open('converter', 'single')")
    status = page.locator("[data-testid='converter-status']")
    expect(status).to_have_text("Ready")
    disp = page.locator("[data-testid='converter-source-display']")
    expect(disp).to_have_text("No file selected")
    calc_clear_overlays(page)


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Load sample png fixture and convert to jpeg.
    sample = fixtures.get("sample.png", "sample.png")
    api._dialog_answers.append(sample)
    page.evaluate("window.FOSS.router.open('converter', 'single')")
    page.click("[data-testid='converter-choose-file']")
    page.wait_for_timeout(250)

    page.click("[data-testid='converter-convert-btn']")
    page.wait_for_timeout(300)
    res = page.locator("[data-testid='converter-result']")
    expect(res).to_be_visible()
    calc_clear_overlays(page)


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Click convert without selected file to verify error banner.
    page.evaluate("window.FOSS.router.open('converter', 'single')")
    page.click("[data-testid='converter-convert-btn']")
    page.wait_for_timeout(200)
    err = page.locator("[data-testid='converter-error-banner']")
    expect(err).to_be_visible()
    expect(err).to_contain_text("select a file")
    calc_clear_overlays(page)


def scenario_queue(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Add files to batch queue and execute sequential conversion.
    s1 = fixtures.get("sample.png", "sample.png")
    s2 = fixtures.get("sample2.png", "sample2.png")
    api._dialog_answers.append([s1, s2])
    page.evaluate("window.FOSS.router.open('converter', 'queue')")
    page.click("[data-testid='converter-queue-add-btn']")
    page.wait_for_timeout(250)

    tbl = page.locator("[data-testid='converter-queue-table'] table")
    expect(tbl).to_be_visible()

    page.click("[data-testid='converter-batch-start-btn']")
    page.wait_for_timeout(300)
    status = page.locator("[data-testid='converter-queue-status']")
    expect(status).to_contain_text("Batch complete")
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("queue", scenario_queue),
]
