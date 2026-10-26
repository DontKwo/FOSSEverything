from typing import Any, Callable
from playwright.sync_api import Page, expect


def scenario_loaded(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open text tools and populate input editor.
    page.evaluate("window.FOSS.router.open('text_tools', 'main')")
    in_box = page.locator("[data-testid='text_tools-input-input']")
    in_box.fill("hello world from foss")
    page.evaluate("var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;")


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Apply uppercase transformation and verify output.
    page.evaluate("window.FOSS.router.open('text_tools', 'main')")
    in_box = page.locator("[data-testid='text_tools-input-input']")
    in_box.fill("hello world from foss")
    page.click("[data-testid='text_tools-case-upper']")
    out_box = page.locator("[data-testid='text_tools-output-input']")
    expect(out_box).to_have_value("HELLO WORLD FROM FOSS")
    page.evaluate("var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;")


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Apply empty regex pattern and verify danger error banner.
    page.evaluate("window.FOSS.router.open('text_tools', 'main')")
    in_box = page.locator("[data-testid='text_tools-input-input']")
    in_box.fill("some text")
    page.click("[data-testid='text_tools-regex-apply']")
    err_banner = page.locator("[data-testid='text_tools-error']")
    expect(err_banner).to_be_visible()
    page.evaluate("var h = document.getElementById('toast-host'); if (h) h.innerHTML = '';")
    page.evaluate("var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;")


def scenario_diff(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Compare original and right-side text in diff checker.
    page.evaluate("window.FOSS.router.open('text_tools', 'main')")
    in_box = page.locator("[data-testid='text_tools-input-input']")
    in_box.fill("line one\nline two")
    right_box = page.locator("[data-testid='text_tools-diff-right-input']")
    right_box.fill("line one\nline three")
    page.click("[data-testid='text_tools-diff-compare']")
    out_box = page.locator("[data-testid='text_tools-output-input']")
    expect(out_box).not_to_have_value("")
    page.evaluate("var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;")


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("diff", scenario_diff),
]
