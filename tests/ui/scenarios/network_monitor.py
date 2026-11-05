from typing import Any, Callable
from playwright.sync_api import Page, expect


def calc_clear_overlays(page: Page) -> None:
    # Clear tooltips, toasts, and reset view scroll.
    try:
        page.mouse.move(0, 0)
    except Exception:  # noqa: 10
        pass
    page.evaluate(
        "if (window.FOSS && window.FOSS.tooltips) window.FOSS.tooltips.hide(); "
        "var t = document.getElementById('tooltip-host'); if (t) t.innerHTML = ''; "
        "var h = document.getElementById('toast-host'); if (h) h.innerHTML = ''; "
        "var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;"
    )


def scenario_live(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Query live connections and verify refresh and table host.
    page.evaluate("window.FOSS.router.open('network_monitor', 'live')")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='network_monitor-live-filter']")).to_be_visible()
    expect(page.locator("[data-testid='network_monitor-live-table-host']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_history(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Search connection event history from SQLite database.
    page.evaluate("window.FOSS.router.open('network_monitor', 'history')")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='network_monitor-history-proc-input']")).to_be_visible()
    expect(page.locator("[data-testid='network_monitor-history-table-host']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_stats(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Query aggregated stats for top domains and processes.
    page.evaluate("window.FOSS.router.open('network_monitor', 'stats')")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='network_monitor-refresh-stats-btn']")).to_be_visible()
    expect(page.locator("[data-testid='network_monitor-stats-grid']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_apps(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Inspect per-app connection summary table.
    page.evaluate("window.FOSS.router.open('network_monitor', 'apps')")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='network_monitor-apps-refresh-btn']")).to_be_visible()
    expect(page.locator("[data-testid='network_monitor-apps-table-host']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_live_sort_and_mark(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Toggle column sort direction and verify mark known/unknown toolbar buttons.
    page.evaluate("window.FOSS.router.open('network_monitor', 'live')")
    page.wait_for_timeout(500)

    expect(page.locator("[data-testid='network_monitor-mark-known-btn']")).to_be_visible()
    expect(page.locator("[data-testid='network_monitor-mark-unknown-btn']")).to_be_visible()
    header = page.locator("[data-testid='network_monitor-sort-pid']")
    if header.count() == 0:
        calc_clear_overlays(page)
        return
    header.click()
    expect(page.locator("[data-testid='network_monitor-sort-pid']")).to_have_attribute("aria-sort", "ascending")
    page.locator("[data-testid='network_monitor-sort-pid']").click()
    expect(page.locator("[data-testid='network_monitor-sort-pid']")).to_have_attribute("aria-sort", "descending")

    rows = page.locator("[data-testid='network_monitor-live-row']").filter(
        has=page.locator("[data-testid='network_monitor-dest-badge']")
    )
    if rows.count() > 0:
        rows.first.click()
        expect(page.locator("[data-testid='network_monitor-live-row'].nm-row-selected").first).to_be_visible()
        page.evaluate("document.querySelectorAll('#view-root, #view-root *').forEach(function (e) { e.scrollTop = 0; })")
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("live", scenario_live),
    ("live_sort_and_mark", scenario_live_sort_and_mark),
    ("history", scenario_history),
    ("stats", scenario_stats),
    ("apps", scenario_apps),
]

