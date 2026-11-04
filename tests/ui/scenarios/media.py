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
        "var t = document.getElementById('tooltip-host'); if (t) t.innerHTML = ''; "
        "var h = document.getElementById('toast-host'); if (h) h.innerHTML = ''; "
        "document.querySelectorAll('.tool-panel-container, #view-root, .workbench, .page').forEach(function (el) { el.scrollTop = 0; el.scrollLeft = 0; });"
    )


def scenario_loaded(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open Media Studio Trim tab and verify initial loaded state.
    page.evaluate("window.FOSS.router.open('media', 'trim')")
    expect(page.locator("[data-testid='media-open-btn']")).to_be_visible()
    expect(page.locator("[data-testid='media-trim-run-btn']")).to_be_visible()
    expect(page.locator("[data-testid='media-status']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_trim(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Load clip fixture and adjust trim markers.
    clip = fixtures.get("clip.mp4", "clip.mp4")
    api._dialog_answers.append(clip)
    page.evaluate("window.FOSS.router.open('media', 'trim')")
    page.click("[data-testid='media-open-btn']")
    page.wait_for_timeout(300)

    page.fill("[data-testid='media-trim-start']", "0.2")
    page.fill("[data-testid='media-trim-end']", "0.8")
    expect(page.locator("[data-testid='media-trim-start']")).to_have_value("0.2")
    expect(page.locator("[data-testid='media-trim-end']")).to_have_value("0.8")
    calc_clear_overlays(page)


def scenario_audio(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Switch to audio tab and verify audio extraction and subtitle controls.
    page.evaluate("window.FOSS.router.open('media', 'audio')")
    expect(page.locator("[data-testid='media-audio-extract-btn']")).to_be_visible()
    expect(page.locator("[data-testid='media-transcribe-btn']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_effects(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Switch to effects tab and verify frame capture, speed, and GIF controls.
    page.evaluate("window.FOSS.router.open('media', 'effects')")
    expect(page.locator("[data-testid='media-frame-capture-btn']")).to_be_visible()
    expect(page.locator("[data-testid='media-speed-reverse-btn']")).to_be_visible()
    expect(page.locator("[data-testid='media-gif-btn']")).to_be_visible()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("loaded", scenario_loaded),
    ("trim", scenario_trim),
    ("audio", scenario_audio),
    ("effects", scenario_effects),
]

