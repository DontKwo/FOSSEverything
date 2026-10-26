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
    # Open Data Studio editor tab and format sample JSON.
    page.evaluate("window.FOSS.router.open('data', 'editor')")
    in_box = page.locator("[data-testid='data-editor-input-input']")
    in_box.fill('{"tools": ["pdf", "image"], "status": "active"}')
    page.click("[data-testid='data-editor-format']")
    page.wait_for_timeout(100)
    calc_clear_overlays(page)


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Switch to query tab and evaluate JSONPath expression.
    page.evaluate("window.FOSS.router.open('data', 'query')")
    data_box = page.locator("[data-testid='data-query-data-input-input']")
    data_box.fill('{"tools": [{"name": "pdf", "rating": 5}, {"name": "ocr", "rating": 4}]}')
    path_input = page.locator("[data-testid='data-query-path-input']")
    path_input.fill("$.tools[*].name")
    page.click("[data-testid='data-query-evaluate']")
    page.wait_for_timeout(100)
    out_box = page.locator("[data-testid='data-query-output-input']")
    expect(out_box).not_to_have_value("")
    calc_clear_overlays(page)


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Validate malformed syntax and assert error banner is visible.
    page.evaluate("window.FOSS.router.open('data', 'editor')")
    in_box = page.locator("[data-testid='data-editor-input-input']")
    in_box.fill('{"unclosed": "brace"')
    page.click("[data-testid='data-editor-validate']")
    page.wait_for_timeout(100)
    err_banner = page.locator("[data-testid='data-editor-error']")
    expect(err_banner).to_be_visible()
    calc_clear_overlays(page)


def scenario_tables(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Clean and normalize markdown table padding on tables tab.
    page.evaluate("window.FOSS.router.open('data', 'tables')")
    in_box = page.locator("[data-testid='data-tables-input-input']")
    in_box.fill("| Col1 | Col2 |\n|---|---|\n| val1 | val2 |")
    page.click("[data-testid='data-tables-clean']")
    page.wait_for_timeout(100)
    status_el = page.locator("[data-testid='data-tables-status']")
    expect(status_el).not_to_have_text("Ready")
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("tables", scenario_tables),
]
