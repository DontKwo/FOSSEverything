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
    # Open Collage Builder tool and verify loaded empty state.
    page.evaluate("window.FOSS.router.open('collage', 'main')")
    status = page.locator("[data-testid='collage-status']")
    expect(status).to_have_text("Ready")
    lst = page.locator("[data-testid='collage-images-list']")
    expect(lst).to_contain_text("No images added")
    calc_clear_overlays(page)


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Add multiple image fixtures, generate preview, and save collage.
    s1 = fixtures.get("sample.png", "sample.png")
    s2 = fixtures.get("sample2.png", "sample2.png")
    api._dialog_answers.append([s1, s2])
    page.evaluate("window.FOSS.router.open('collage', 'main')")
    page.click("[data-testid='collage-add-images']")
    page.wait_for_timeout(300)

    img = page.locator("[data-testid='collage-preview-display'] img")
    expect(img).to_be_visible()

    page.click("[data-testid='collage-save-btn']")
    page.wait_for_timeout(300)
    res = page.locator("[data-testid='collage-result']")
    expect(res).to_be_visible()
    calc_clear_overlays(page)


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Click save collage without added images to trigger error banner.
    page.evaluate("window.FOSS.router.open('collage', 'main')")
    page.click("[data-testid='collage-save-btn']")
    page.wait_for_timeout(200)
    err = page.locator("[data-testid='collage-error-banner']")
    expect(err).to_be_visible()
    expect(err).to_contain_text("add images")
    calc_clear_overlays(page)


def scenario_captions(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Toggle captions on image collage.
    s1 = fixtures.get("sample.png", "sample.png")
    s2 = fixtures.get("sample2.png", "sample2.png")
    api._dialog_answers.append([s1, s2])
    page.evaluate("window.FOSS.router.open('collage', 'main')")
    page.click("[data-testid='collage-add-images']")
    page.wait_for_timeout(300)

    page.click("[data-testid='collage-captions-check']")
    page.wait_for_timeout(300)
    img = page.locator("[data-testid='collage-preview-display'] img")
    expect(img).to_be_visible()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("captions", scenario_captions),
]
