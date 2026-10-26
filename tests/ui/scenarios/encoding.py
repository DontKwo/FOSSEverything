from typing import Any, Callable
from playwright.sync_api import Page, expect


def scenario_loaded(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Navigate to encoding text tab and input sample text.
    page.evaluate("window.FOSS.router.open('encoding', 'text')")
    textarea = page.locator("[data-testid='encoding-text-editor-input']")
    textarea.fill("Hello World")


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Trigger encoding and assert valid Base64 output.
    page.evaluate("window.FOSS.router.open('encoding', 'text')")
    textarea = page.locator("[data-testid='encoding-text-editor-input']")
    textarea.fill("Hello World")
    page.click("[data-testid='encoding-text-encode']")
    expect(textarea).to_have_value("SGVsbG8gV29ybGQ=")


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Attempt decoding malformed input and verify danger banner.
    page.evaluate("window.FOSS.router.open('encoding', 'text')")
    textarea = page.locator("[data-testid='encoding-text-editor-input']")
    textarea.fill("!!!invalid-base64-payload!!!")
    page.click("[data-testid='encoding-text-decode']")
    err_banner = page.locator("[data-testid='encoding-text-error']")
    expect(err_banner).to_be_visible()
    page.evaluate("var h = document.getElementById('toast-host'); if (h) h.innerHTML = '';")


def scenario_file_tab(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Test file tab with fixture selection and encoding.
    sample_file = fixtures.get("sample.txt", "")
    api._dialog_answers.append(sample_file)
    page.evaluate("window.FOSS.router.open('encoding', 'file')")
    page.click("[data-testid='encoding-file-picker-browse']")
    page.click("[data-testid='encoding-file-encode']")
    result_card = page.locator("[data-testid='encoding-file-result']")
    expect(result_card).to_be_visible()


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("file_tab", scenario_file_tab),
]
