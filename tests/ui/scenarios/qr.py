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
    # Open QR Generator and verify loaded preview and controls.
    page.evaluate("window.FOSS.router.open('qr', 'main')")
    expect(page.locator("[data-testid='qr-preview-img']")).to_be_visible()
    expect(page.locator("[data-testid='qr-status']")).to_have_text("Ready")
    calc_clear_overlays(page)


def scenario_barcode(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Switch payload type to Barcode and verify symbology options.
    page.evaluate("window.FOSS.router.open('qr', 'main')")
    page.select_option("[data-testid='qr-payload-type']", "barcode")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='qr-barcode-symbology']")).to_be_visible()
    expect(page.locator("[data-testid='qr-preview-img']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_scan(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open Scan tab and decode QR code fixture image.
    qr_file = fixtures.get("qr.png", "qr.png")
    api._dialog_answers.append(qr_file)

    page.evaluate("window.FOSS.router.open('qr', 'main')")
    page.click("[data-testid='qr-tab-scan']")
    page.wait_for_timeout(200)

    page.click("[data-testid='qr-scan-file-picker-browse']")
    page.wait_for_timeout(400)

    results = page.locator("[data-testid='qr-scan-results']")
    expect(results).to_be_visible()
    calc_clear_overlays(page)


def scenario_export(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Export generated QR code to vector SVG file.
    sample = fixtures.get("sample.png", "sample.png")
    out_svg = str(Path(sample).parent / "test_code.svg")
    api._dialog_answers.append(out_svg)

    page.evaluate("window.FOSS.router.open('qr', 'main')")
    page.click("[data-testid='qr-export-svg-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='qr-result']")).to_be_visible()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("barcode", scenario_barcode),
    ("scan", scenario_scan),
    ("export", scenario_export),
]
