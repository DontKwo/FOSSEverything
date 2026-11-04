from pathlib import Path
from typing import Any
from playwright.sync_api import Page, expect


def test_collage_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    # Walkthrough for full collage tool functionality.
    fixtures_dir = Path("tests/ui/_fixtures")
    sample_png = str(fixtures_dir / "sample.png")
    sample_png2 = str(fixtures_dir / "sample2.png")
    if not Path(sample_png2).exists():
        sample_png2 = sample_png

    col_out = str(tmp_path / "out_collage.png")
    layers_out = str(tmp_path / "out_layers.psd")

    api._dialog_answers.extend(
        [[sample_png, sample_png2], col_out, [sample_png, sample_png2], layers_out]
    )

    page.evaluate("window.FOSS.router.open('collage', 'main')")
    expect(page.locator("[data-testid='collage-status']")).to_have_text("Ready")

    page.evaluate(
        "document.querySelector(\"[data-testid='collage-add-images']\").click();"
    )
    page.wait_for_timeout(300)
    expect(page.locator("[data-testid='collage-preview-display'] img")).to_be_visible()

    page.evaluate(
        "document.querySelector(\"[data-testid='collage-captions-check']\").click();"
    )
    page.wait_for_timeout(300)

    page.evaluate(
        "document.querySelector(\"[data-testid='collage-save-btn']\").click();"
    )
    page.wait_for_timeout(300)
    expect(page.locator("[data-testid='collage-result']")).to_be_visible()
    assert Path(col_out).exists()

    page.evaluate(
        'document.querySelector("[data-testid=\'collage-mode-toggle\']").querySelectorAll("button").forEach(b => { if(b.textContent.includes("Freeform")) b.click(); });'
    )
    page.wait_for_timeout(200)
    expect(page.locator("[data-testid='collage-freeform-canvas']")).to_be_visible()

    page.evaluate(
        "document.querySelector(\"[data-testid='collage-add-images']\").click();"
    )
    page.wait_for_timeout(300)
    expect(page.locator("[data-testid='collage-layers-list']")).to_contain_text(
        "sample"
    )

    page.evaluate(
        "document.querySelector(\"[data-testid='collage-export-kind-layered']\").click();"
    )
    page.wait_for_timeout(200)
    page.evaluate(
        "document.querySelector(\"[data-testid='collage-export-layers-btn']\").click();"
    )
    page.wait_for_timeout(300)
    expect(page.locator("[data-testid='collage-result']")).to_be_visible()
    assert Path(layers_out).exists()
