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
    # Open Metadata tool and verify empty initial state and warning banner.
    page.evaluate("window.FOSS.router.open('metadata', 'main')")
    disp = page.locator("[data-testid='metadata-file-display']")
    expect(disp).to_have_text("No file selected")
    banner = page.locator("[data-testid='metadata-warning-banner']")
    expect(banner).to_be_visible()
    calc_clear_overlays(page)


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Load sample image fixture and verify metadata table population.
    sample_file = fixtures.get("sample.png", "sample.png")
    api._dialog_answers.append(sample_file)
    page.evaluate("window.FOSS.router.open('metadata', 'main')")
    page.click("[data-testid='metadata-choose-file']")
    page.wait_for_timeout(250)
    diff_table = page.locator("[data-testid='metadata-diff-table']")
    expect(diff_table).not_to_have_text("")
    calc_clear_overlays(page)


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Attempt saving edits without loaded file to assert no error crash.
    page.evaluate("window.FOSS.router.open('metadata', 'main')")
    page.click("[data-testid='metadata-save-btn']")
    status = page.locator("[data-testid='metadata-status']")
    expect(status).to_have_text("Ready")
    calc_clear_overlays(page)


def scenario_strip(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Strip metadata from sample image and verify result card.
    sample_file = fixtures.get("sample.png", "sample.png")
    api._dialog_answers.append(sample_file)
    page.evaluate("window.FOSS.router.open('metadata', 'main')")
    page.click("[data-testid='metadata-choose-file']")
    page.wait_for_timeout(250)
    page.click("[data-testid='metadata-strip-btn']")
    page.wait_for_timeout(250)
    res_card = page.locator("[data-testid='metadata-result']")
    expect(res_card).to_be_visible()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("strip", scenario_strip),
]
