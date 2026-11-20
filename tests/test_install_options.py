"""Tests for installer-applied first-run preferences."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.system.install_options import INSTALL_THEMES, apply_install_options, parse_install_options


@pytest.fixture
def settings_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("FOSS_SETTINGS_DIR", str(tmp_path))
    return tmp_path


def read_settings(directory: Path) -> dict[str, object]:
    path = directory / "settings.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


@pytest.mark.parametrize("theme", INSTALL_THEMES)
def test_every_theme_is_accepted(settings_dir: Path, theme: str) -> None:
    ok, _ = apply_install_options([f"--theme={theme}"])
    assert ok
    assert read_settings(settings_dir)["theme"] == theme


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1.0", 1.0), ("1.25", 1.25), ("0.9", 0.9), ("0.1", 0.5), ("9", 2.5), ("1.234", 1.23)],
)
def test_scale_is_clamped_and_rounded(settings_dir: Path, raw: str, expected: float) -> None:
    ok, _ = apply_install_options([f"--ui-scale={raw}"])
    assert ok
    assert read_settings(settings_dir)["ui_scale"] == expected


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--configure"],
        ["--theme=neon"],
        ["--theme="],
        ["--ui-scale=big"],
        ["--ui-scale=nan"],
        ["--ui-scale=inf"],
        ["--theme=dark", "--ui-scale=abc"],
    ],
)
def test_invalid_input_writes_nothing(settings_dir: Path, argv: list[str]) -> None:
    ok, message = apply_install_options(argv)
    assert not ok
    assert message
    assert read_settings(settings_dir) == {}


def test_existing_unrelated_settings_survive(settings_dir: Path) -> None:
    (settings_dir / "settings.json").write_text(json.dumps({"favorites": ["pdf"]}), encoding="utf-8")
    ok, _ = apply_install_options(["--configure", "--theme=light", "--ui-scale=1.5"])
    assert ok
    assert read_settings(settings_dir) == {"favorites": ["pdf"], "theme": "light", "ui_scale": 1.5}


def test_parse_ignores_unrelated_arguments() -> None:
    assert parse_install_options(["--configure", "file.pdf", "--theme=dark"]) == {"theme": "dark"}
