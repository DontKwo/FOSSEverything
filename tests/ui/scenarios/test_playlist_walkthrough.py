from pathlib import Path
from typing import Any
from playwright.sync_api import Page, expect


def test_playlist_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    # Walkthrough of all playlist tools and tabs.
    fixtures_dir = Path("tests/ui/_fixtures")
    playlist_m3u8 = str(fixtures_dir / "playlist.m3u8")

    # Fetch Tab
    page.evaluate("window.FOSS.router.open('playlist', 'fetch')")
    page.wait_for_timeout(200)

    expect(page.locator("[data-testid='playlist-url-input']")).to_be_visible()
    expect(page.locator("[data-testid='playlist-fetch-btn']")).to_be_visible()

    # Import
    page.evaluate("window.FOSS.router.open('playlist', 'import')")
    page.wait_for_timeout(200)

    pl_out = str(tmp_path / "out_pl.csv")
    api._dialog_answers.extend([playlist_m3u8, pl_out])

    page.click("[data-testid='playlist-choose-file']")
    page.wait_for_timeout(200)

    page.evaluate("window.FOSS.router.open('playlist', 'output')")
    page.wait_for_timeout(200)

    expect(page.locator("[data-testid='playlist-tracks-table']")).to_be_visible()
    page.click("[data-testid='playlist-export-csv-btn']")
    page.wait_for_timeout(200)
    assert Path(pl_out).exists()

    # Paste
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

    page.evaluate("window.FOSS.router.open('playlist', 'output')")
    page.wait_for_timeout(200)

    pl_m3u8_out = str(tmp_path / "out_pl.m3u8")
    api._dialog_answers.append(pl_m3u8_out)

    page.click("[data-testid='playlist-export-m3u8-btn']")
    page.wait_for_timeout(200)
    assert Path(pl_m3u8_out).exists()

    page.click("[data-testid='playlist-copy-links-btn']")
    page.wait_for_timeout(200)
