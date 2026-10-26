from pathlib import Path
from typing import Any, Callable
from playwright.sync_api import Page, expect


def calc_clear_overlays(page: Page) -> None:
    # Clear tooltips, toasts, and reset view scroll.
    try:
        page.mouse.move(0, 0)
    except Exception:
        pass
    page.evaluate(
        "if (window.FOSS && window.FOSS.tooltips) window.FOSS.tooltips.hide(); "
        "var t = document.getElementById('tooltip-host'); if (t) t.innerHTML = ''; "
        "var h = document.getElementById('toast-host'); if (h) h.innerHTML = ''; "
        "var el = document.getElementById('view-root'); if (el) el.scrollTop = 0;"
    )


def scenario_trim(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Trim video clip and verify output result card.
    sample = fixtures.get("clip.mp4", "clip.mp4")
    out_file = str(Path(sample).parent / "out_trimmed.mp4")
    api._dialog_answers.append(sample)
    api._dialog_answers.append(out_file)

    page.evaluate("window.FOSS.router.open('media', 'trim')")
    page.click("[data-testid='media-file-picker-browse']")
    page.wait_for_timeout(200)

    page.fill("[data-testid='media-start-time']", "0.1")
    page.fill("[data-testid='media-end-time']", "0.5")

    page.click("[data-testid='media-trim-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='media-trim-result']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_convert(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Transcode video to another format.
    sample = fixtures.get("clip.mp4", "clip.mp4")
    out_file = str(Path(sample).parent / "out_converted.mkv")
    api._dialog_answers.append(sample)
    api._dialog_answers.append(out_file)

    page.evaluate("window.FOSS.router.open('media', 'convert')")
    page.click("[data-testid='media-convert-picker-browse']")
    page.wait_for_timeout(200)

    page.click("[data-testid='media-convert-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='media-convert-result']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_compress(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Compress video for target size limit.
    sample = fixtures.get("clip.mp4", "clip.mp4")
    out_file = str(Path(sample).parent / "out_compressed.mp4")
    api._dialog_answers.append(sample)
    api._dialog_answers.append(out_file)

    page.evaluate("window.FOSS.router.open('media', 'compress')")
    page.click("[data-testid='media-compress-picker-browse']")
    page.wait_for_timeout(200)

    page.click("[data-testid='media-compress-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='media-compress-result']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_audio(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Extract audio stream from video file.
    sample = fixtures.get("clip.mp4", "clip.mp4")
    out_file = str(Path(sample).parent / "out_audio.mp3")
    api._dialog_answers.append(sample)
    api._dialog_answers.append(out_file)

    page.evaluate("window.FOSS.router.open('media', 'audio')")
    page.click("[data-testid='media-audio-picker-browse']")
    page.wait_for_timeout(200)

    page.click("[data-testid='media-extract-audio-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='media-audio-result']")).to_be_visible()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("trim", scenario_trim),
    ("convert", scenario_convert),
    ("compress", scenario_compress),
    ("audio", scenario_audio),
]

