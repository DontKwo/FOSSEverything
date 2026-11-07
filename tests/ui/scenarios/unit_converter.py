from typing import Any, Callable
from playwright.sync_api import Page, expect


def calc_clear_overlays(page: Page) -> None:
    # Clear tooltips, toasts, and reset view scroll.
    try:
        page.mouse.move(0, 0)
    except Exception:
        return
    page.evaluate(
        "if (window.FOSS && window.FOSS.tooltips) window.FOSS.tooltips.hide(); "
        "var t = document.getElementById('tooltip-host'); if (t) t.innerHTML = ''; "
        "var h = document.getElementById('toast-host'); if (h) h.innerHTML = ''; "
        "var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;"
    )


def scenario_loaded(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open Unit Converter standard tab and assert workbench is visible.
    page.evaluate("window.FOSS.router.open('unit_converter', 'standard')")
    cat_select = page.locator("[data-testid='unit_converter-category-select']")
    expect(cat_select).to_be_visible()
    table = page.locator("[data-testid='unit_converter-table']")
    expect(table).to_be_visible()
    calc_clear_overlays(page)


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Verify standard conversion and unit swapping.
    page.evaluate("window.FOSS.router.open('unit_converter', 'standard')")
    val_in = page.locator("[data-testid='unit_converter-input-value']")
    val_in.fill("50")
    swap_btn = page.locator("[data-testid='unit_converter-swap-btn']")
    swap_btn.click()
    page.wait_for_timeout(100)
    hero_res = page.locator("[data-testid='unit_converter-hero-result']")
    expect(hero_res).to_be_visible()
    calc_clear_overlays(page)


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Test dimensional mismatch error in expression tab.
    page.evaluate("window.FOSS.router.open('unit_converter', 'expression')")
    expr_in = page.locator("[data-testid='unit_converter-expr-input']")
    expr_in.fill("10 meters")
    target_in = page.locator("[data-testid='unit_converter-expr-target']")
    target_in.fill("seconds")
    eval_btn = page.locator("[data-testid='unit_converter-expr-btn']")
    eval_btn.click()
    page.wait_for_timeout(150)
    err = page.locator("[data-testid='unit_converter-expr-error']")
    expect(err).to_be_visible()
    calc_clear_overlays(page)


def scenario_expression(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Evaluate compound physical expression.
    page.evaluate("window.FOSS.router.open('unit_converter', 'expression')")
    expr_in = page.locator("[data-testid='unit_converter-expr-input']")
    expr_in.fill("100 km/h")
    target_in = page.locator("[data-testid='unit_converter-expr-target']")
    target_in.fill("mph")
    eval_btn = page.locator("[data-testid='unit_converter-expr-btn']")
    eval_btn.click()
    page.wait_for_timeout(150)
    res = page.locator("[data-testid='unit_converter-expr-result']")
    expect(res).to_be_visible()
    expect(res).to_contain_text("mile / hour")
    calc_clear_overlays(page)


def scenario_clipboard_regression(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Verify copy buttons trigger bridge copy_to_clipboard safely.
    page.evaluate("window.FOSS.router.open('unit_converter', 'standard')")
    val_in = page.locator("[data-testid='unit_converter-input-value']")
    val_in.fill("75")
    page.click("[data-testid='unit_converter-copy-val-btn']")
    page.click("[data-testid='unit_converter-copy-eq-btn']")
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("expression", scenario_expression),
    ("clipboard_regression", scenario_clipboard_regression),
]
