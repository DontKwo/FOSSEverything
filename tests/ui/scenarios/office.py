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
    # Open Office tool and verify initial empty state.
    page.evaluate("window.FOSS.router.open('office', 'main')")
    status = page.locator("[data-testid='office-status']")
    expect(status).to_have_text("Ready")
    disp = page.locator("[data-testid='office-file-display']")
    expect(disp).to_have_text("No office document selected")
    calc_clear_overlays(page)


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Load sample docx fixture and convert to PDF.
    docx_file = fixtures.get("sample.docx", "sample.docx")
    api._dialog_answers.append(docx_file)
    page.evaluate("window.FOSS.router.open('office', 'main')")
    page.click("[data-testid='office-choose-file']")
    page.wait_for_timeout(250)

    page.click("[data-testid='office-convert-btn']")
    page.wait_for_timeout(300)
    res = page.locator("[data-testid='office-result']")
    expect(res).to_be_visible()
    calc_clear_overlays(page)


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Click convert without selected document to trigger error banner.
    page.evaluate("window.FOSS.router.open('office', 'main')")
    page.click("[data-testid='office-convert-btn']")
    page.wait_for_timeout(200)
    err = page.locator("[data-testid='office-error-banner']")
    expect(err).to_be_visible()
    expect(err).to_contain_text("choose an Office document")
    calc_clear_overlays(page)


def scenario_extract(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Extract text from sample docx fixture.
    docx_file = fixtures.get("sample.docx", "sample.docx")
    api._dialog_answers.append(docx_file)
    page.evaluate("window.FOSS.router.open('office', 'main')")
    page.click("[data-testid='office-choose-file']")
    page.wait_for_timeout(250)

    page.click("[data-testid='office-extract-btn']")
    page.wait_for_timeout(250)
    out = page.locator("[data-testid='office-text-output']")
    expect(out).not_to_have_value("")
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("extract", scenario_extract),
]
