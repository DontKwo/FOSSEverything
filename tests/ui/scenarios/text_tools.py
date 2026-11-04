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
        "var el = document.getElementById('view-root'); if (el) el.scrollTop = 0; "
        "document.querySelectorAll('*').forEach(function(el) { if (el.scrollTop > 0) el.scrollTop = 0; });"
    )


def scenario_loaded(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open text tools and populate input editor.
    page.evaluate("window.FOSS.router.open('text_tools', 'main')")
    in_box = page.locator("[data-testid='text_tools-input-input']")
    in_box.fill("hello world from foss")
    calc_clear_overlays(page)


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Apply uppercase transformation and verify output.
    page.evaluate("window.FOSS.router.open('text_tools', 'main')")
    in_box = page.locator("[data-testid='text_tools-input-input']")
    in_box.fill("hello world from foss")
    page.click("[data-testid='text_tools-case-upper']")
    out_box = page.locator("[data-testid='text_tools-output-input']")
    expect(out_box).to_have_value("HELLO WORLD FROM FOSS")
    calc_clear_overlays(page)


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Apply empty regex pattern and verify danger error banner.
    page.evaluate("window.FOSS.router.open('text_tools', 'main')")
    in_box = page.locator("[data-testid='text_tools-input-input']")
    in_box.fill("some text")
    page.click("[data-testid='text_tools-regex-apply']")
    err_banner = page.locator("[data-testid='text_tools-error']")
    expect(err_banner).to_be_visible()
    calc_clear_overlays(page)


def scenario_diff(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Compare original and right-side text in diff checker.
    page.evaluate("window.FOSS.router.open('text_tools', 'diff')")
    in_box = page.locator("[data-testid='text_tools-diff-left-input']")
    in_box.fill("line one\nline two")
    right_box = page.locator("[data-testid='text_tools-diff-right-input']")
    right_box.fill("line one\nline three")
    page.click("[data-testid='text_tools-diff-compare']")
    out_box = page.locator("[data-testid='text_tools-diff-output-input']")
    expect(out_box).not_to_have_value("")
    calc_clear_overlays(page)


def scenario_counter(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open word counter tab and verify live metrics on document text.
    page.evaluate("window.FOSS.router.open('text_tools', 'counter')")
    in_box = page.locator("[data-testid='text_tools-counter-input-input']")
    in_box.fill("Antigravity open source software suite provides private offline tools.")
    page.wait_for_timeout(350)
    words_el = page.locator("[data-testid='text_tools-stat-words']")
    expect(words_el).to_have_text("9")
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("diff", scenario_diff),
    ("counter", scenario_counter),
]
