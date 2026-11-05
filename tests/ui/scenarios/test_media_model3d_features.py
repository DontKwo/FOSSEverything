from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect

FIXTURES_DIR = Path("tests/ui/_fixtures")


def test_media_empty_state_and_action_cards(page: Page, api: Any) -> None:
    # Empty media tab shows the dropzone and four action cards; a card routes to its tab after picking a file.
    api._dialog_answers.clear()
    page.evaluate("window.FOSS.router.open('media', 'trim')")
    expect(page.locator("[data-testid='media-dropzone']")).to_be_visible()
    for testid in ("media-action-trim", "media-action-audio", "media-action-subtitles", "media-action-gif"):
        expect(page.locator(f"[data-testid='{testid}']")).to_be_visible()
    expect(page.locator("[data-testid='media-video-player']")).to_be_hidden()

    api._dialog_answers.append(str(FIXTURES_DIR / "clip.mp4"))
    page.click("[data-testid='media-action-gif']")
    expect(page.locator("[data-testid='media-gif-btn']")).to_be_visible()
    expect(page.locator("[data-testid='media-empty-state']")).to_be_hidden()
    expect(page.locator("[data-testid='media-file-badge']")).to_have_text("clip.mp4")
    api._dialog_answers.clear()


def test_media_video_streams_over_http(page: Page, api: Any) -> None:
    # Loaded clip is served from the loopback HTTP server and the player reads its duration.
    api._dialog_answers.clear()
    api._dialog_answers.append(str(FIXTURES_DIR / "clip.mp4"))
    page.evaluate("window.FOSS.router.open('media', 'trim')")
    page.click("[data-testid='media-open-btn']")
    page.wait_for_function(
        "() => { const v = document.querySelector(\"[data-testid='media-video-player']\"); return v && v.src.startsWith('http://127.0.0.1:') && v.readyState >= 1; }",
        timeout=8000,
    )
    assert page.evaluate("document.querySelector(\"[data-testid='media-video-player']\").duration") > 0
    api._dialog_answers.clear()


def test_media_defaults_button_and_values(page: Page, api: Any) -> None:
    # Media defaults persist and drive the audio format, bitrate, and fast-copy controls.
    page.evaluate("window.FOSS.router.open('media', 'audio')")
    expect(page.locator("[data-testid='media-defaults-btn']")).to_be_visible()
    page.evaluate("window.FOSS.toolDefaults.save('media', {audio_format: 'wav', bitrate: '256k', fast_copy: false})")
    page.evaluate("window.FOSS.router.open('media', 'trim')")
    assert page.locator("[data-testid='media-trim-fast-copy-input']").is_checked() is False
    page.evaluate("window.FOSS.router.open('media', 'audio')")
    assert page.locator("[data-testid='media-audio-format-select']").input_value() == "wav"
    assert page.locator("[data-testid='media-audio-bitrate-select']").input_value() == "256k"
    page.evaluate("window.FOSS.toolDefaults.save('media', {audio_format: 'mp3', bitrate: '192k', fast_copy: true})")


def test_model3d_divider_resizes_right_pane(page: Page, api: Any) -> None:
    # Dragging the divider changes --split-right and the sidebar width, within the 18rem minimum.
    page.evaluate("window.FOSS.router.open('model3d', 'inspector')")
    workbench = page.locator("[data-testid='model3d-workbench']")
    sidebar = page.locator("[data-testid='model3d-sidebar']")
    divider = workbench.locator(".split-divider")
    expect(divider).to_be_visible()
    before = sidebar.bounding_box()["width"]
    box = divider.bounding_box()
    start_x = box["x"] + box["width"] / 2
    start_y = box["y"] + box["height"] / 2
    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.mouse.move(start_x - 80, start_y, steps=5)
    page.mouse.up()
    after = sidebar.bounding_box()["width"]
    assert after > before + 40
    split_right = page.evaluate(
        "document.querySelector(\"[data-testid='model3d-workbench']\").style.getPropertyValue('--split-right')"
    )
    assert split_right.endswith("rem")
    assert after >= 18 * 16 - 1


def test_model3d_defaults_apply_render_mode_and_unit(page: Page, api: Any) -> None:
    # Saved model3d defaults update the render mode select and the unit select.
    page.evaluate("window.FOSS.router.open('model3d', 'inspector')")
    expect(page.locator("[data-testid='model3d-defaults-btn']")).to_be_visible()
    page.evaluate("window.FOSS.toolDefaults.save('model3d', {render_mode: 'wireframe', unit: 'inch', show_grid: false})")
    assert page.locator("[data-testid='model3d-render-mode']").input_value() == "wireframe"
    assert page.locator("[data-testid='model3d-unit-select']").input_value() == "inch"
    assert page.locator("[data-testid='model3d-view-scales']").is_checked() is False
    page.evaluate("window.FOSS.toolDefaults.save('model3d', {render_mode: 'shaded', unit: 'mm', show_grid: true})")


def test_playlist_track_table_scrolls_horizontally(page: Page, api: Any) -> None:
    # Track table sits inside a horizontal scroll wrapper and shows track durations.
    page.evaluate("window.FOSS.router.open('playlist', 'paste')")
    page.fill("[data-testid='playlist-paste-input']", "Queen - Bohemian Rhapsody\nThe Beatles - Hey Jude\n")
    page.click("[data-testid='playlist-parse-btn']")
    expect(page.locator("[data-testid='playlist-tracks-table']")).to_be_visible()
    overflow_x = page.evaluate(
        "getComputedStyle(document.querySelector(\"[data-testid='playlist-table-scroll']\")).overflowX"
    )
    assert overflow_x in ("auto", "scroll")
    for fmt in ("csv", "m3u8", "json"):
        expect(page.locator(f"[data-testid='playlist-export-{fmt}-btn']")).to_be_visible()


def test_playlist_json_export_follows_path_extension(page: Page, api: Any, tmp_path: Path) -> None:
    # Export CSV button writes JSON when the chosen path has a .json extension.
    page.evaluate("window.FOSS.router.open('playlist', 'paste')")
    page.fill("[data-testid='playlist-paste-input']", "Queen - Bohemian Rhapsody\n")
    page.click("[data-testid='playlist-parse-btn']")
    expect(page.locator("[data-testid='playlist-tracks-table']")).to_be_visible()
    out_json = tmp_path / "out_pl.json"
    api._dialog_answers.clear()
    api._dialog_answers.append(str(out_json))
    page.click("[data-testid='playlist-export-csv-btn']")
    page.wait_for_timeout(400)
    assert out_json.exists()
    assert out_json.read_text(encoding="utf-8").lstrip().startswith("{")


def test_playlist_fetch_failure_shows_reason_toast(page: Page, api: Any) -> None:
    # A rejected URL surfaces its reason in an error toast and the banner.
    page.evaluate("window.FOSS.router.open('playlist', 'import')")
    page.fill("[data-testid='playlist-url-input']", "https://example.com/not-a-playlist")
    page.click("[data-testid='playlist-fetch-btn']")
    expect(page.locator("[data-testid='toast-item']").first).to_contain_text("not recognized")
    expect(page.locator("[data-testid='playlist-error-banner']")).to_be_visible()
