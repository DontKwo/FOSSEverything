from typing import Any, Callable
from playwright.sync_api import Page, expect


def calc_clear_overlays(page: Page) -> None:
    # Clear tooltips, toasts, and reset view scroll.
    try:
        page.mouse.move(0, 0)
    except Exception:
        pass
    page.evaluate(
        "if (window.FOSS && window.FOSS.tooltips) window.FOSS.tooltips.hide(); "
        "var t = document.getElementById('tooltip-host'); if (t) t.innerHTML = ''; "
        "var h = document.getElementById('toast-host'); if (h) h.innerHTML = ''; "
        "var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;"
    )


def scenario_suite(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open ArtCraft Hub suite tab and verify creative application cards.
    page.evaluate("window.FOSS.router.open('artcraft', 'suite')")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='artcraft-grid']")).to_be_visible()
    expect(page.locator("[data-testid='artcraft-card-photocraft']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_install(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open ArtCraft installation guide and verify instructions.
    page.evaluate("window.FOSS.router.open('artcraft', 'install')")
    page.wait_for_timeout(200)

    expect(page.locator("text=System PATH Integration")).to_be_visible()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("suite", scenario_suite),
    ("install", scenario_install),
]

