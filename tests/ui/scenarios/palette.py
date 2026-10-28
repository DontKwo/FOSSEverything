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


def scenario_loaded(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open Palette Extractor and verify initial loaded state.
    page.evaluate("window.FOSS.router.open('palette', 'main')")
    expect(page.locator("[data-testid='tool-page-palette']")).to_be_visible()
    expect(page.locator("[data-testid='palette-status']")).to_contain_text("Open an image to extract palettes")
    expect(page.locator("[data-testid='palette-swatch-list']")).to_contain_text("No palette extracted yet")
    calc_clear_overlays(page)


def scenario_extract(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Load sample image and extract dominant color swatches.
    sample = fixtures.get("sample.png", "sample.png")
    api._dialog_answers.append(sample)
    page.evaluate("window.FOSS.router.open('palette', 'main')")
    page.click("[data-testid='palette-file-picker-browse']")
    page.wait_for_timeout(200)
    page.click("[data-testid='palette-extract-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='palette-swatch-list'] .font-mono").first).to_be_visible()
    expect(page.locator("[data-testid='palette-status']")).to_contain_text("Extracted")
    calc_clear_overlays(page)


def scenario_samples(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Sample pixel color from image canvas and verify eyedropper samples tab.
    sample = fixtures.get("sample.png", "sample.png")
    api._dialog_answers.append(sample)
    page.evaluate("window.FOSS.router.open('palette', 'main')")
    page.click("[data-testid='palette-file-picker-browse']")
    page.wait_for_timeout(200)
    page.click("[data-testid='palette-extract-btn']")
    page.wait_for_timeout(400)

    canvas = page.locator("[data-testid='palette-preview-canvas']")
    expect(canvas).to_be_visible()
    canvas.click(position={"x": 50, "y": 50})
    page.wait_for_timeout(200)

    page.click("[data-testid='palette-tab-samples']")
    page.wait_for_timeout(200)
    expect(page.locator("[data-testid='palette-samples-list'] .font-mono").first).to_be_visible()
    calc_clear_overlays(page)


def scenario_export(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Extract palette and export visual strip image.
    sample = fixtures.get("sample.png", "sample.png")
    out_strip = str(Path(sample).parent / "out_palette_strip.png")
    api._dialog_answers.append(sample)
    api._dialog_answers.append(out_strip)

    page.evaluate("window.FOSS.router.open('palette', 'main')")
    page.click("[data-testid='palette-file-picker-browse']")
    page.wait_for_timeout(200)
    page.click("[data-testid='palette-extract-btn']")
    page.wait_for_timeout(300)

    page.click("[data-testid='palette-export-strip-btn']")
    page.wait_for_timeout(300)
    expect(page.locator("[data-testid='palette-result']")).to_be_visible()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("extract", scenario_extract),
    ("samples", scenario_samples),
    ("export", scenario_export),
]
