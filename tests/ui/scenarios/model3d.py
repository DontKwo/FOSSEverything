from pathlib import Path
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
        "var tooltip = document.getElementById('tooltip-host'); if (tooltip) tooltip.innerHTML = ''; "
        "var toast = document.getElementById('toast-host'); if (toast) toast.innerHTML = ''; "
        "document.querySelectorAll('.tool-panel-container, #view-root, .workbench, .page').forEach(function (el) { el.scrollTop = 0; el.scrollLeft = 0; });"
    )


def scenario_inspector(page: Page, fixtures: dict[str, str], api_server: Any) -> None:
    # Load STL model and inspect bounding box, vertex counts, and WebGL canvas.
    sample = fixtures.get("cube.stl", "cube.stl")
    api_server._dialog_answers.append(sample)

    page.evaluate("window.FOSS.router.open('model3d', 'inspector')")
    page.click("[data-testid='model3d-open-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='model3d-canvas']")).to_be_visible()
    expect(page.locator("[data-testid='model3d-info-card']")).to_be_visible()
    expect(page.locator("[data-testid='model3d-reset-view-btn']")).to_be_visible()
    expect(page.locator("[data-testid='model3d-tripod']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_cut(page: Page, fixtures: dict[str, str], api_server: Any) -> None:
    # Slice 3D model across plane and verify cut pieces result card and pieces list.
    sample = fixtures.get("cube.stl", "cube.stl")
    out_dir = str(Path(sample).parent)
    api_server._dialog_answers.append(sample)
    api_server._dialog_answers.append(out_dir)

    page.evaluate("window.FOSS.router.open('model3d', 'cut')")
    page.click("[data-testid='model3d-open-btn']")
    page.wait_for_timeout(200)

    page.click("[data-testid='model3d-cut-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='model3d-cut-result']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_export(page: Page, fixtures: dict[str, str], api_server: Any) -> None:
    # Convert and export 3D model format.
    sample = fixtures.get("cube.stl", "cube.stl")
    out_stl = str(Path(sample).parent / "out_exported.stl")
    api_server._dialog_answers.append(sample)
    api_server._dialog_answers.append(out_stl)

    page.evaluate("window.FOSS.router.open('model3d', 'export')")
    page.click("[data-testid='model3d-open-btn']")
    page.wait_for_timeout(200)

    page.click("[data-testid='model3d-export-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='model3d-canvas']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_scale(page: Page, fixtures: dict[str, str], api_server: Any) -> None:
    # Rescale model dimensions and export scaled geometry.
    sample = fixtures.get("cube.stl", "cube.stl")
    out_stl = str(Path(sample).parent / "out_scaled.stl")
    api_server._dialog_answers.append(sample)
    api_server._dialog_answers.append(out_stl)

    page.evaluate("window.FOSS.router.open('model3d', 'inspector')")
    page.click("[data-testid='model3d-open-btn']")
    page.wait_for_timeout(200)

    page.click("[data-testid='model3d-apply-scale-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='model3d-scale-result']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_measure(page: Page, fixtures: dict[str, str], api_server: Any) -> None:
    # Measure Euclidean distance between two selected 3D coordinates.
    sample = fixtures.get("cube.stl", "cube.stl")
    api_server._dialog_answers.append(sample)

    page.evaluate("window.FOSS.router.open('model3d', 'inspector')")
    page.click("[data-testid='model3d-open-btn']")
    page.wait_for_timeout(200)

    page.click("[data-testid='model3d-measure-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='model3d-distance-display']")).to_be_visible()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("inspector", scenario_inspector),
    ("cut", scenario_cut),
    ("export", scenario_export),
    ("scale", scenario_scale),
    ("measure", scenario_measure),
]
