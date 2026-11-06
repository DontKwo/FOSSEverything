from typing import Any

from playwright.sync_api import Page, expect

ALL_TOOLS = [
    "archive",
    "collage",
    "compressor",
    "converter",
    "data",
    "encoding",
    "images",
    "markdown",
    "media",
    "metadata",
    "model3d",
    "network_monitor",
    "ocr",
    "palette",
    "pdf",
    "playlist",
    "qr",
    "renamer",
    "resume",
    "text_tools",
    "unit_converter",
]


def test_all_tools_register_configurable_defaults(page: Page, api: Any) -> None:
    # Verify every registered tool defines at least two default fields.
    page.evaluate("window.FOSS.router.open('home')")
    for tool_id in ALL_TOOLS:
        fields_count = page.evaluate(f"window.FOSS.toolDefaults.getFields('{tool_id}').length")
        assert fields_count >= 2, f"Tool '{tool_id}' should register at least 2 default settings"


def test_settings_per_app_defaults_tab(page: Page, api: Any) -> None:
    # Settings per-app defaults tab displays tool selector and persists configured defaults.
    page.evaluate("window.FOSS.router.open('settings')")
    page.click("[data-testid='settings-nav-defaults']")
    expect(page.locator("[data-testid='settings-defaults-tool-select']")).to_be_visible()

    for tool_id in ("archive", "compressor", "qr", "renamer", "resume"):
        page.select_option("[data-testid='settings-defaults-tool-select']", tool_id)
        expect(page.locator(f"[data-testid='{tool_id}-defaults-form']")).to_be_visible()


def test_tool_defaults_save_and_apply(page: Page, api: Any) -> None:
    # Saved defaults persist across tool re-opens and update application controls.
    page.evaluate("window.FOSS.toolDefaults.save('compressor', {profile: 'aggressive', png_quantize: false})")
    page.evaluate("window.FOSS.router.open('compressor', 'main')")
    assert page.locator("[data-testid='compressor-preset-select']").input_value() == "aggressive"
    assert page.locator("[data-testid='compressor-png-quantize']").is_checked() is False

    page.evaluate("window.FOSS.toolDefaults.save('qr', {default_type: 'wifi', barcode_symbology: 'ean13', barcode_show_label: false})")
    page.evaluate("window.FOSS.router.open('qr', 'barcode')")
    assert page.locator("[data-testid='qr-barcode-symbology']").input_value() == "ean13"
    assert page.locator("[data-testid='qr-barcode-toggle']").is_checked() is False

    page.evaluate("window.FOSS.toolDefaults.save('renamer', {sort_order: 'date_desc', auto_resolve: false, recursive: true})")
    page.evaluate("window.FOSS.router.open('renamer', 'rules')")
    assert page.locator("[data-testid='renamer-sort-select']").input_value() == "date_desc"
    assert page.locator("[data-testid='renamer-auto-resolve-conflicts']").is_checked() is False
    assert page.locator("[data-testid='renamer-recursive']").is_checked() is True

    # Restore defaults
    page.evaluate("window.FOSS.toolDefaults.save('compressor', {profile: 'balanced', png_quantize: true})")
    page.evaluate("window.FOSS.toolDefaults.save('qr', {default_type: 'url', barcode_symbology: 'code128', barcode_show_label: true})")
    page.evaluate("window.FOSS.toolDefaults.save('renamer', {sort_order: 'name_asc', auto_resolve: true, recursive: false})")
