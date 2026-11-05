from __future__ import annotations

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
    # Open File Compressor tool and verify ready state.
    page.evaluate("window.FOSS.router.open('compressor', 'main')")
    status = page.locator("[data-testid='compressor-status']")
    expect(status).to_have_text("Ready")
    btn = page.locator("[data-testid='compressor-run-btn']")
    expect(btn).to_be_disabled()
    calc_clear_overlays(page)


def scenario_result(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Queue image fixture and execute compression run.
    sample = fixtures.get("sample.png", "sample.png")
    api._dialog_answers.append([sample])
    api._dialog_answers.append(str(Path(sample).parent / "out_compressed.png"))
    page.evaluate("window.FOSS.router.open('compressor', 'main')")
    page.click("[data-testid='compressor-choose-file']")
    page.wait_for_timeout(250)

    tbl = page.locator("[data-testid='compressor-queue-table'] table")
    expect(tbl).to_be_visible()
    expect(page.locator("[data-testid='compressor-estimate-readout']")).to_contain_text("Estimated savings")

    page.click("[data-testid='compressor-run-btn']")
    page.wait_for_timeout(350)
    status = page.locator("[data-testid='compressor-status']")
    expect(status).to_contain_text("Compression complete")
    calc_clear_overlays(page)


def scenario_clear(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Queue image fixture and clear queue.
    sample = fixtures.get("sample.png", "sample.png")
    api._dialog_answers.append([sample])
    page.evaluate("window.FOSS.router.open('compressor', 'main')")
    page.click("[data-testid='compressor-choose-file']")
    page.wait_for_timeout(250)

    tbl = page.locator("[data-testid='compressor-queue-table'] table")
    expect(tbl).to_be_visible()

    page.click("[data-testid='compressor-clear-btn']")
    page.wait_for_timeout(200)
    btn = page.locator("[data-testid='compressor-run-btn']")
    expect(btn).to_be_disabled()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("result", scenario_result),
    ("clear", scenario_clear),
]

