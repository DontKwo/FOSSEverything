from pathlib import Path
from typing import Any
from playwright.sync_api import Page

def test_media_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    fixtures_dir: Path = Path("tests/ui/_fixtures")
    clip_mp4: str = str(fixtures_dir / "clip.mp4")

    # 1. Open Media Studio Audio tab and select file
    page.evaluate("window.FOSS.router.open('media', 'audio')")
    out_audio: str = str(tmp_path / "out_audio.mp3")

    api._dialog_answers.clear()
    api._dialog_answers.extend([clip_mp4, out_audio])
    page.click("[data-testid='media-choose-file']")
    page.wait_for_timeout(300)
    page.click("[data-testid='media-extract-audio-btn']")
    page.wait_for_timeout(1000)
    assert Path(out_audio).exists()

    # 2. Trim Media
    page.evaluate("window.FOSS.router.open('media', 'trim')")
    out_trim: str = str(tmp_path / "out_trim.mp4")

    api._dialog_answers.clear()
    api._dialog_answers.extend([clip_mp4, out_trim])
    page.click("[data-testid='media-open-btn']")
    page.wait_for_timeout(300)

    page.fill("[data-testid='media-trim-start']", "0.2")
    page.fill("[data-testid='media-trim-end']", "0.8")
    page.evaluate("window.FOSS.api('media_trim', {input_path: '%s', output_path: '%s', start_time: 0.2, end_time: 0.8, fast_copy: false})" % (clip_mp4.replace('\\', '/'), out_trim.replace('\\', '/')))
    page.wait_for_timeout(1500)
    assert Path(out_trim).exists()

    # 3. Effects (Reverse)
    page.evaluate("window.FOSS.router.open('media', 'effects')")
    out_effect: str = str(tmp_path / "out_effect.mp4")

    api._dialog_answers.clear()
    api._dialog_answers.extend([clip_mp4, out_effect])
    page.click("[data-testid='media-choose-file']")
    page.wait_for_timeout(300)

    page.evaluate("window.FOSS.api('media_speed_reverse', {input_path: '%s', output_path: '%s', speed_factor: 1.0, reverse: true})" % (clip_mp4.replace('\\', '/'), out_effect.replace('\\', '/')))
    page.wait_for_timeout(1500)
    assert Path(out_effect).exists()
