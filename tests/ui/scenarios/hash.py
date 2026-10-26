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
    # Open Hash tool file tab and compute file hashes.
    sample_file = fixtures.get("sample.txt", "sample.txt")
    page.evaluate("window.FOSS.router.open('hash', 'file')")
    in_box = page.locator("[data-testid='hash-file-path']")
    in_box.fill(sample_file)
    page.click("[data-testid='hash-file-compute']")
    page.wait_for_timeout(100)
    res_table = page.locator("[data-testid='hash-file-results']")
    expect(res_table).not_to_have_text("")
    calc_clear_overlays(page)


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Switch to text hash tab and verify real-time digest computation.
    page.evaluate("window.FOSS.router.open('hash', 'text')")
    in_box = page.locator("[data-testid='hash-text-input-input']")
    in_box.fill("The quick brown fox jumps over the lazy dog")
    page.wait_for_timeout(100)
    digest_val = page.locator("[data-testid='hash-text-digest-val']")
    expect(digest_val).not_to_have_text("")
    calc_clear_overlays(page)


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Attempt to compute hash with empty file path to trigger error status.
    page.evaluate("window.FOSS.router.open('hash', 'file')")
    in_box = page.locator("[data-testid='hash-file-path']")
    in_box.fill("")
    page.click("[data-testid='hash-file-compute']")
    page.wait_for_timeout(100)
    status_el = page.locator("[data-testid='hash-file-status']")
    expect(status_el).not_to_have_text("Ready")
    calc_clear_overlays(page)


def scenario_compare(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Compare identical files on compare files tab.
    sample_file = fixtures.get("sample.txt", "sample.txt")
    page.evaluate("window.FOSS.router.open('hash', 'compare')")
    f1 = page.locator("[data-testid='hash-compare-file1']")
    f2 = page.locator("[data-testid='hash-compare-file2']")
    f1.fill(sample_file)
    f2.fill(sample_file)
    page.click("[data-testid='hash-compare-btn']")
    page.wait_for_timeout(100)
    res_box = page.locator("[data-testid='hash-compare-result']")
    expect(res_box).not_to_have_text("waiting for two files to compare.")
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("compare", scenario_compare),
]
