from pathlib import Path
from typing import Any
from playwright.sync_api import Page
from tests.ui.scenarios.markdown import SCENARIOS


def test_markdown_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    fixtures: dict[str, str] = {"sample.pdf": str(tmp_path / "sample.pdf")}
    for name, func in SCENARIOS:
        func(page, fixtures, api)
