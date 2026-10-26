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


def scenario_convert(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Convert image format and verify result presentation.
    sample = fixtures.get("sample.png", "sample.png")
    out_file = str(Path(sample).parent / "out_converted.jpg")
    api._dialog_answers.append(sample)
    api._dialog_answers.append(out_file)

    page.evaluate("window.FOSS.router.open('images', 'convert')")
    page.click("[data-testid='images-single-picker-browse']")
    page.wait_for_timeout(200)

    page.click("[data-testid='images-convert-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='images-convert-result']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_transform(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Load image into transform workspace and test auto-enhance.
    sample = fixtures.get("sample.png", "sample.png")
    api._dialog_answers.append(sample)

    page.evaluate("window.FOSS.router.open('images', 'transform')")
    page.click("[data-testid='images-transform-picker-browse']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='images-transform-preview']")).to_be_visible()
    page.click("[data-testid='image-auto-enhance-btn']")
    page.wait_for_timeout(300)
    expect(page.locator("[data-testid='images-transform-status']")).to_contain_text("Loaded")
    calc_clear_overlays(page)


def scenario_background(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Verify AI background removal workspace and model selection.
    sample = fixtures.get("sample.png", "sample.png")
    api._dialog_answers.append(sample)

    page.evaluate("window.FOSS.router.open('images', 'background')")
    page.click("[data-testid='images-bg-picker-browse']")
    page.wait_for_timeout(200)

    expect(page.locator("[data-testid='image-bg-model-select']")).to_be_visible()
    expect(page.locator("[data-testid='images-bg-status']")).to_contain_text("Selected: sample.png")
    calc_clear_overlays(page)


def scenario_compress(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Verify image compression configuration tab.
    sample = fixtures.get("sample.png", "sample.png")
    api._dialog_answers.append(sample)

    page.evaluate("window.FOSS.router.open('images', 'compress')")
    page.click("[data-testid='images-compress-picker-browse']")
    page.wait_for_timeout(200)

    expect(page.locator("[data-testid='image-compress-group']")).to_be_visible()
    expect(page.locator("[data-testid='images-compress-status']")).to_contain_text("Selected: sample.png")
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("convert", scenario_convert),
    ("transform", scenario_transform),
    ("background", scenario_background),
    ("compress", scenario_compress),
]

