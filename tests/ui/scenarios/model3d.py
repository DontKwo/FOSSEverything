from pathlib import Path
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


def scenario_inspector(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Load STL model and inspect bounding box, vertex counts, and canvas.
    sample = fixtures.get("cube.stl", "cube.stl")
    api._dialog_answers.append(sample)

    page.evaluate("window.FOSS.router.open('model3d', 'inspector')")
    page.click("[data-testid='model3d-picker-browse']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='model3d-canvas']")).to_be_visible()
    expect(page.locator("[data-testid='model3d-info-card']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_cut(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Slice 3D model across plane and verify cut pieces result card.
    sample = fixtures.get("cube.stl", "cube.stl")
    out_dir = str(Path(sample).parent)
    api._dialog_answers.append(sample)
    api._dialog_answers.append(out_dir)

    page.evaluate("window.FOSS.router.open('model3d', 'cut')")
    page.click("[data-testid='model3d-cut-picker-browse']")
    page.wait_for_timeout(200)

    page.click("[data-testid='model3d-cut-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='model3d-cut-result']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_scale(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Rescale model dimensions and export scaled geometry.
    sample = fixtures.get("cube.stl", "cube.stl")
    out_stl = str(Path(sample).parent / "out_scaled.stl")
    api._dialog_answers.append(sample)
    api._dialog_answers.append(out_stl)

    page.evaluate("window.FOSS.router.open('model3d', 'scale')")
    page.click("[data-testid='model3d-scale-picker-browse']")
    page.wait_for_timeout(200)

    page.click("[data-testid='model3d-apply-scale-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='model3d-scale-result']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_measure(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Measure Euclidean distance between two selected 3D coordinates.
    page.evaluate("window.FOSS.router.open('model3d', 'measure')")
    page.wait_for_timeout(200)

    page.click("[data-testid='model3d-calc-distance-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='model3d-distance-display']")).to_be_visible()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("inspector", scenario_inspector),
    ("cut", scenario_cut),
    ("scale", scenario_scale),
    ("measure", scenario_measure),
]
