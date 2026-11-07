# Playwright UI scenarios for Markdown Studio workspace.
from pathlib import Path
from typing import Any, Callable
from playwright.sync_api import Page, expect


def calc_clear_overlays(page: Page) -> None:
    # Clear toasts, tooltips, and reset view scroll.
    page.evaluate(
        "if (window.FOSS && window.FOSS.tooltips) window.FOSS.tooltips.hide(); "
        "var t = document.getElementById('tooltip-host'); if (t) t.innerHTML = ''; "
        "var h = document.getElementById('toast-host'); if (h) h.innerHTML = ''; "
        "var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;"
    )


def scenario_loaded(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open Markdown Studio, check side-by-side split, and test flavor selection.
    page.evaluate("window.FOSS.router.open('markdown', 'main')")
    in_box = page.locator("[data-testid='markdown-editor-input']")
    in_box.fill("# Markdown Studio\n\n- Root\n  - Sub\n- [ ] Task checkbox")
    page.wait_for_timeout(250)
    expect(page.locator("[data-testid='markdown-split']")).to_be_visible()
    flavor_sel = page.locator("[data-testid='markdown-flavor-select']")
    expect(flavor_sel).to_be_visible()
    flavor_sel.select_option("commonmark")
    page.wait_for_timeout(150)
    flavor_sel.select_option("gfm")
    page.wait_for_timeout(150)
    calc_clear_overlays(page)


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Export markdown document to standalone HTML and verify result card.
    page.evaluate("window.FOSS.router.open('markdown', 'main')")
    in_box = page.locator("[data-testid='markdown-editor-input']")
    in_box.fill("# Export Test\n\nDocument ready for HTML export.")
    out_dir = Path(fixtures.get("sample.pdf", "sample.pdf")).parent
    out_file = str(out_dir / "out_doc.html")
    api._dialog_answers.append(out_file)
    page.click("[data-testid='markdown-export-html']")
    page.wait_for_timeout(250)
    res_card = page.locator("[data-testid='markdown-result']")
    expect(res_card).to_be_visible()
    calc_clear_overlays(page)


def scenario_error(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Attempt HTML export on empty editor to trigger error banner.
    page.evaluate("window.FOSS.router.open('markdown', 'main')")
    in_box = page.locator("[data-testid='markdown-editor-input']")
    in_box.fill("")
    page.click("[data-testid='markdown-export-html']")
    err_banner = page.locator("[data-testid='markdown-error']")
    expect(err_banner).to_be_visible()
    calc_clear_overlays(page)


def scenario_formatting(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Apply heading, list, and task actions to editor content.
    page.evaluate("window.FOSS.router.open('markdown', 'main')")
    in_box = page.locator("[data-testid='markdown-editor-input']")
    in_box.fill("Sample section")
    page.click("[data-testid='markdown-heading']")
    page.wait_for_timeout(100)
    heading_text = in_box.input_value()
    assert "###" in heading_text or "#" in heading_text
    page.click("[data-testid='markdown-tasklist']")
    page.wait_for_timeout(100)
    assert "- [ ]" in in_box.input_value()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("error", scenario_error),
    ("formatting", scenario_formatting),
]
