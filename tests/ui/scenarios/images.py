from pathlib import Path
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


def scenario_background(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Verify AI background removal workspace and model selection.
    sample = fixtures.get("sample.png", "sample.png")
    api._dialog_answers.append(sample)

    page.evaluate("window.FOSS.router.open('images', 'background')")
    page.click("[data-testid='images-bg-picker-browse']")
    page.wait_for_timeout(200)

    expect(page.locator("[data-testid='images-bg-model-select']")).to_be_visible()
    expect(page.locator("[data-testid='images-bg-status']")).to_contain_text("Selected: sample.png")
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("background", scenario_background),
]
