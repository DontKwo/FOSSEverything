from pathlib import Path
from typing import Any

from playwright.sync_api import Page

from tests.ui.scenarios.resume import SCENARIOS


def test_resume_walkthrough(
    page: Page, api: Any, tmp_path: Path, fixtures: dict[str, str]
) -> None:
    # Run through all scenarios sequentially for the resume tool.
    for _, scenario_func in SCENARIOS:
        scenario_func(page, fixtures, api)
