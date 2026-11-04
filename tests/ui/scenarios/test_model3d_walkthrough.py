from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect


def test_model3d_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    # Walkthrough of complete navigation, interaction, and rendering of model3d tool.
    fixtures_dir = Path("tests/ui/_fixtures")
    cube_stl = str(fixtures_dir / "cube.stl")

    # 1. Inspector
    api._dialog_answers.append(cube_stl)
    page.evaluate("window.FOSS.router.open('model3d', 'inspector')")
    page.click("[data-testid='model3d-open-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='model3d-canvas']")).to_be_visible()
    expect(page.locator("[data-testid='model3d-info-card']")).to_be_visible()
    expect(page.locator("[data-testid='model3d-reset-view-btn']")).to_be_visible()
    expect(page.locator("[data-testid='model3d-tripod']")).to_be_visible()

    # Center Origin
    out_center = str(tmp_path / "out_center.stl")
    api._dialog_answers.append(out_center)
    page.click("[data-testid='model3d-center-origin-btn']")
    page.wait_for_timeout(300)
    assert Path(out_center).exists()

    # Repair
    out_repair = str(tmp_path / "out_repair.stl")
    api._dialog_answers.append(out_repair)
    page.click("[data-testid='model3d-repair-btn']")
    page.wait_for_timeout(300)
    assert Path(out_repair).exists()

    # 2. Scale (Inspector tab)
    out_scaled = str(tmp_path / "out_scaled.stl")
    api._dialog_answers.append(out_scaled)
    page.click("[data-testid='model3d-apply-scale-btn']")
    page.wait_for_timeout(300)
    expect(page.locator("[data-testid='model3d-scale-result']")).to_be_visible()
    assert Path(out_scaled).exists()

    # 3. Measure (Inspector tab)
    page.click("[data-testid='model3d-measure-btn']")
    page.wait_for_timeout(300)
    expect(page.locator("[data-testid='model3d-distance-display']")).to_be_visible()

    # 4. Cut
    out_dir = str(tmp_path)
    api._dialog_answers.append(cube_stl)
    api._dialog_answers.append(out_dir)

    page.evaluate("window.FOSS.router.open('model3d', 'cut')")
    page.click("[data-testid='model3d-open-btn']")
    page.wait_for_timeout(300)

    page.click("[data-testid='model3d-cut-btn']")
    page.wait_for_timeout(300)
    expect(page.locator("[data-testid='model3d-cut-result']")).to_be_visible()

    # 5. Export
    out_stl = str(tmp_path / "out_exported.stl")
    api._dialog_answers.append(cube_stl)
    api._dialog_answers.append(out_stl)

    page.evaluate("window.FOSS.router.open('model3d', 'export')")
    page.click("[data-testid='model3d-open-btn']")
    page.wait_for_timeout(300)

    page.click("[data-testid='model3d-export-btn']")
    page.wait_for_timeout(300)
    expect(page.locator("[data-testid='model3d-canvas']")).to_be_visible()
    assert Path(out_stl).exists()
