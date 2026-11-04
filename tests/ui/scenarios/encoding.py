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
    # Navigate to encoding text tab and input sample text.
    page.evaluate("window.FOSS.router.open('encoding', 'text')")
    textarea = page.locator("[data-testid='encoding-text-editor-input']")
    textarea.fill("Hello World")
    calc_clear_overlays(page)


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Trigger encoding and assert valid Base64 output.
    page.evaluate("window.FOSS.router.open('encoding', 'text')")
    textarea = page.locator("[data-testid='encoding-text-editor-input']")
    textarea.fill("Hello World")
    page.locator("[data-testid='encoding-encode-btn'], [data-testid='encoding-text-encode']").first.click()
    out_box = page.locator("[data-testid='encoding-text-output-input']")
    expect(out_box).to_have_value("SGVsbG8gV29ybGQ=")
    calc_clear_overlays(page)


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Attempt decoding malformed input and verify danger banner.
    page.evaluate("window.FOSS.router.open('encoding', 'text')")
    textarea = page.locator("[data-testid='encoding-text-editor-input']")
    textarea.fill("!!!invalid-base64-payload!!!")
    page.locator("[data-testid='encoding-decode-btn'], [data-testid='encoding-text-decode']").first.click()
    err_banner = page.locator("[data-testid='encoding-text-error']")
    expect(err_banner).to_be_visible()
    calc_clear_overlays(page)


def scenario_file_tab(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Test file tab with fixture selection and encoding.
    sample_file = fixtures.get("sample.txt", "")
    api._dialog_answers.append(sample_file)
    page.evaluate("window.FOSS.router.open('encoding', 'file')")
    page.click("[data-testid='encoding-file-picker-browse']")
    page.click("[data-testid='encoding-file-encode']")
    result_card = page.locator("[data-testid='encoding-file-result']")
    expect(result_card).to_be_visible()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("file_tab", scenario_file_tab),
]
