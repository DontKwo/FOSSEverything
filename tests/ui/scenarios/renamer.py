import os
import tempfile
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
    # Open Renamer tool and verify loaded empty state.
    page.evaluate("window.FOSS.router.open('renamer', 'main')")
    status = page.locator("[data-testid='renamer-status']")
    expect(status).to_have_text("Ready")
    tbl = page.locator("[data-testid='renamer-preview-table']")
    expect(tbl).to_contain_text("No files loaded")
    calc_clear_overlays(page)


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Load temporary files, preview rename plan, and apply batch rename.
    tmp_dir = tempfile.mkdtemp()
    f1 = os.path.join(tmp_dir, "batch_test_01.txt")
    f2 = os.path.join(tmp_dir, "batch_test_02.txt")
    with open(f1, "w", encoding="utf-8") as h:
        h.write("file 1")
    with open(f2, "w", encoding="utf-8") as h:
        h.write("file 2")

    api._dialog_answers.append([f1, f2])
    page.evaluate("window.FOSS.router.open('renamer', 'main')")
    page.click("[data-testid='renamer-choose-files']")
    page.wait_for_timeout(250)

    tbl = page.locator("[data-testid='renamer-preview-table'] table")
    expect(tbl).to_be_visible()

    page.click("[data-testid='renamer-apply-btn']")
    page.wait_for_timeout(300)
    res_card = page.locator("[data-testid='renamer-result']")
    expect(res_card).to_be_visible()
    calc_clear_overlays(page)


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Click apply rename without loaded files to trigger error banner.
    page.evaluate("window.FOSS.router.open('renamer', 'main')")
    page.click("[data-testid='renamer-apply-btn']")
    page.wait_for_timeout(200)
    err = page.locator("[data-testid='renamer-error-banner']")
    expect(err).to_be_visible()
    expect(err).to_contain_text("No files loaded")
    calc_clear_overlays(page)


def scenario_timeline(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Test timeline ordering toggle with multiple files.
    tmp_dir = tempfile.mkdtemp()
    f1 = os.path.join(tmp_dir, "alpha_timeline.txt")
    f2 = os.path.join(tmp_dir, "beta_timeline.txt")
    with open(f1, "w", encoding="utf-8") as h:
        h.write("timeline 1")
    with open(f2, "w", encoding="utf-8") as h:
        h.write("timeline 2")

    api._dialog_answers.append([f1, f2])
    page.evaluate("window.FOSS.router.open('renamer', 'main')")
    page.click("[data-testid='renamer-choose-files']")
    page.wait_for_timeout(250)
    page.click("[data-testid='renamer-timeline-check']")
    page.wait_for_timeout(250)

    tbl = page.locator("[data-testid='renamer-preview-table'] table")
    expect(tbl).to_be_visible()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("timeline", scenario_timeline),
]
