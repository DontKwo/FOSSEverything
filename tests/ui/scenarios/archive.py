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
    # Open Archive tool create tab and verify loaded state.
    page.evaluate("window.FOSS.router.open('archive', 'create')")
    status = page.locator("[data-testid='archive-create-status']")
    expect(status).to_have_text("Ready")
    src = page.locator("[data-testid='archive-source-display']")
    expect(src).to_have_text("No sources selected")
    calc_clear_overlays(page)


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Package sample file fixture into ZIP archive.
    sample = fixtures.get("sample.txt", "sample.txt")
    api._dialog_answers.append([sample])
    page.evaluate("window.FOSS.router.open('archive', 'create')")
    page.click("[data-testid='archive-choose-source']")
    page.wait_for_timeout(250)

    page.click("[data-testid='archive-create-btn']")
    page.wait_for_timeout(300)
    res = page.locator("[data-testid='archive-create-result']")
    expect(res).to_be_visible()
    calc_clear_overlays(page)


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Click create archive without selected sources to verify error banner.
    page.evaluate("window.FOSS.router.open('archive', 'create')")
    page.click("[data-testid='archive-create-btn']")
    page.wait_for_timeout(200)
    err = page.locator("[data-testid='archive-create-error']")
    expect(err).to_be_visible()
    expect(err).to_contain_text("select at least one file")
    calc_clear_overlays(page)


def scenario_inspect(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Inspect sample zip archive and test integrity.
    zip_path = fixtures.get("sample.zip", "sample.zip")
    api._dialog_answers.append(zip_path)
    page.evaluate("window.FOSS.router.open('archive', 'inspect')")
    page.click("[data-testid='archive-inspect-choose']")
    page.wait_for_timeout(250)

    tbl = page.locator("[data-testid='archive-member-table'] table")
    expect(tbl).to_be_visible()

    page.click("[data-testid='archive-test-integrity-btn']")
    page.wait_for_timeout(250)
    status = page.locator("[data-testid='archive-inspect-status']")
    expect(status).to_contain_text("Integrity check passed")
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("inspect", scenario_inspect),
]
