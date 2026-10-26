from typing import Any, Callable
from playwright.sync_api import Page, expect


def scenario_loaded(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open word counter and input initial text block.
    page.evaluate("window.FOSS.router.open('word_counter', 'main')")
    in_box = page.locator("[data-testid='word_counter-editor-input']")
    in_box.fill("The quick brown fox jumps over the lazy dog.")
    page.evaluate("var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;")


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Input paragraph and verify debounced metrics computation.
    page.evaluate("window.FOSS.router.open('word_counter', 'main')")
    in_box = page.locator("[data-testid='word_counter-editor-input']")
    in_box.fill("First sentence of analysis. Second sentence provides metrics and depth. Third sentence.")
    page.wait_for_timeout(250)
    words_val = page.locator("[data-testid='word_counter-stat-words-val']")
    expect(words_val).not_to_have_text("0")
    page.evaluate("var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;")


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Clear text and verify metrics reset to zero baseline.
    page.evaluate("window.FOSS.router.open('word_counter', 'main')")
    in_box = page.locator("[data-testid='word_counter-editor-input']")
    in_box.fill("Temporary text that will be cleared.")
    page.click("[data-testid='word_counter-clear']")
    page.wait_for_timeout(250)
    words_val = page.locator("[data-testid='word_counter-stat-words-val']")
    expect(words_val).to_have_text("0")
    page.evaluate("var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;")


def scenario_file_load(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Load document fixture through file open action.
    sample_txt = fixtures.get("sample.txt", "")
    api._dialog_answers.append(sample_txt)
    page.evaluate("window.FOSS.router.open('word_counter', 'main')")
    page.click("[data-testid='word_counter-open-file']")
    page.wait_for_timeout(250)
    words_val = page.locator("[data-testid='word_counter-stat-words-val']")
    expect(words_val).not_to_have_text("0")
    page.evaluate("var h = document.getElementById('toast-host'); if (h) h.innerHTML = '';")
    page.evaluate("var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;")


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("file_load", scenario_file_load),
]
