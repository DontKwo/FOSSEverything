from pathlib import Path
from typing import Any, Callable
from playwright.sync_api import Page, expect


def calc_clear_overlays(page: Page) -> None:
    # Clear tooltips, toasts, and reset view scroll.
    try:
        page.mouse.move(0, 0)
    except Exception:  # noqa: BLE001
        pass
    page.evaluate(
        "if (window.FOSS && window.FOSS.tooltips) window.FOSS.tooltips.hide(); "
        "var t = document.getElementById('tooltip-host'); if (t) t.innerHTML = ''; "
        "var h = document.getElementById('toast-host'); if (h) h.innerHTML = ''; "
        "var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;"
    )


def scenario_fetch(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open fetch tab and verify URL input and credentials groups.
    page.evaluate("window.FOSS.router.open('playlist', 'fetch')")
    page.wait_for_timeout(200)

    expect(page.locator("[data-testid='playlist-url-input']")).to_be_visible()
    expect(page.locator("[data-testid='playlist-fetch-btn']")).to_be_visible()
    expect(page.locator("[data-testid='playlist-spotify-client-id']")).to_be_visible()
    expect(page.locator("[data-testid='playlist-yt-client-id']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_paste(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Paste raw tracklist text lines and parse into structured tracks.
    page.evaluate("window.FOSS.router.open('playlist', 'paste')")
    page.wait_for_timeout(200)

    sample_text = (
        "Queen - Bohemian Rhapsody\n"
        "The Beatles - Hey Jude\n"
        "Pink Floyd - Comfortably Numb\n"
    )
    page.fill("[data-testid='playlist-paste-input']", sample_text)
    page.click("[data-testid='playlist-parse-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='playlist-tracks-table']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_output(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Export parsed track list to CSV spreadsheet file.
    sample = fixtures.get("sample.txt", "sample.txt")
    out_csv = str(Path(sample).parent / "out_playlist.csv")
    api._dialog_answers.append(out_csv)

    page.evaluate("window.FOSS.router.open('playlist', 'paste')")
    page.fill("[data-testid='playlist-paste-input']", "Artist - Song Title\n")
    page.click("[data-testid='playlist-parse-btn']")
    page.wait_for_timeout(300)

    page.click("[data-testid='playlist-export-csv-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='playlist-output-result']")).to_be_visible()
    calc_clear_overlays(page)



def scenario_import(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Import a playlist file and verify output parsing.
    m3u8 = fixtures.get("playlist.m3u8", "playlist.m3u8")
    api._dialog_answers.append(m3u8)

    page.evaluate("window.FOSS.router.open('playlist', 'import')")
    page.wait_for_timeout(200)

    page.click("[data-testid='playlist-choose-file']")
    page.wait_for_timeout(300)

    page.evaluate("window.FOSS.router.open('playlist', 'output')")
    page.wait_for_timeout(200)

    expect(page.locator("[data-testid='playlist-tracks-table']")).to_be_visible()
    calc_clear_overlays(page)

SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("fetch", scenario_fetch),
    ("import", scenario_import),
    ("paste", scenario_paste),
    ("output", scenario_output),
]

