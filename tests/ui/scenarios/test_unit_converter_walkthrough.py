from pathlib import Path
from typing import Any
from playwright.sync_api import Page, expect


def test_unit_converter_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    # Walkthrough of the Unit Converter tool.
    page.evaluate("window.FOSS.router.open('unit_converter', 'standard')")

    cat_select = page.locator("[data-testid='unit_converter-category-select']")
    expect(cat_select).to_be_visible()

    val_in = page.locator("[data-testid='unit_converter-input-value']")
    val_in.fill("50")

    swap_btn = page.locator("[data-testid='unit_converter-swap-btn']")
    swap_btn.click()
    page.wait_for_timeout(100)

    hero_res = page.locator("[data-testid='unit_converter-hero-result']")
    expect(hero_res).to_be_visible()

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

    expr_in.fill("100 km/h")
    target_in.fill("mph")
    eval_btn.click()
    page.wait_for_timeout(150)

    res = page.locator("[data-testid='unit_converter-expr-result']")
    expect(res).to_be_visible()
    expect(res).to_contain_text("mile / hour")
