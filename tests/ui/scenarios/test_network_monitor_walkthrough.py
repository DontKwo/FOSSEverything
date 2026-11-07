import contextlib
from typing import Any
from playwright.sync_api import Page, expect


def calc_clear_overlays(page: Page) -> None:
    # Clear tooltips, toasts, and reset view scroll.
    with contextlib.suppress(Exception):
        page.mouse.move(0, 0)
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


def test_network_monitor_walkthrough(
    page: Page, fixtures: dict[str, str], api: Any
) -> None:
    # Execute network_monitor scenarios in sequence for complete walkthrough.
    scenario_live(page, fixtures, api)
    scenario_history(page, fixtures, api)
    scenario_stats(page, fixtures, api)
    scenario_apps(page, fixtures, api)
