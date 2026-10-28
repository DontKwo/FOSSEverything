from typing import Any, Callable
from playwright.sync_api import Page, expect


def calc_clear_overlays(page: Page) -> None:
    # Clear tooltips, toasts, and reset view scroll.
    try:
        page.mouse.move(0, 0)
    except Exception:
        # Cursor reset ignored during headless page shutdown.
        return
    page.evaluate(
        "if (window.FOSS && window.FOSS.tooltips) window.FOSS.tooltips.hide(); "
        "var t = document.getElementById('tooltip-host'); if (t) t.innerHTML = ''; "
        "var h = document.getElementById('toast-host'); if (h) h.innerHTML = ''; "
        "var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;"
    )


def scenario_loaded(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open Data Studio structure tab and assert tree viewer is visible.
    page.evaluate("window.FOSS.router.open('data', 'structure')")
    tree_box = page.locator("[data-testid='data-structure-tree']")
    expect(tree_box).to_be_visible()
    page.wait_for_timeout(100)
    calc_clear_overlays(page)


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Toggle text input drawer and inspect custom JSON payload structure.
    page.evaluate("window.FOSS.router.open('data', 'structure')")
    page.click("[data-testid='data-structure-toggle-text-btn']")
    in_box = page.locator("[data-testid='data-structure-text-input-input']")
    in_box.fill('{"tools": [{"name": "pdf", "rating": 5}, {"name": "ocr", "rating": 4}]}')
    page.click("[data-testid='data-structure-inspect-btn']")
    page.wait_for_timeout(100)
    status_el = page.locator("[data-testid='data-structure-status']")
    expect(status_el).not_to_have_text("Ready")
    calc_clear_overlays(page)


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open units tab and verify unit swap functionality.
    page.evaluate("window.FOSS.router.open('data', 'units')")
    swap_btn = page.locator("[data-testid='data-units-swap-btn']")
    expect(swap_btn).to_be_visible()
    swap_btn.click()
    page.wait_for_timeout(100)
    unit_out = page.locator("[data-testid='data-units-output']")
    expect(unit_out).not_to_have_text("")
    calc_clear_overlays(page)


def scenario_tables(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Clean and convert delimited text on tables tab.
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
