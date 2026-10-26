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


def scenario_capture_full(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Capture full screen screenshot and verify preview image presentation.
    page.evaluate("window.FOSS.router.open('screenshot', 'capture')")
    page.click("[data-testid='screenshot-capture-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='screenshot-preview-img']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_capture_region(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Select interactive region snip mode and execute capture.
    page.evaluate("window.FOSS.router.open('screenshot', 'capture')")
    page.click("[data-testid='screenshot-mode-region']")
    page.wait_for_timeout(100)

    page.click("[data-testid='screenshot-capture-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='screenshot-result']")).to_be_visible()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("capture_full", scenario_capture_full),
    ("capture_region", scenario_capture_region),
]

