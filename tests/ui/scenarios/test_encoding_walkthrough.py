from typing import Any
from playwright.sync_api import Page
from tests.ui.scenarios.encoding import SCENARIOS


def test_encoding_walkthrough(page: Page, api: Any, fixtures: dict[str, str]) -> None:
    # Walkthrough for encoding studio scenarios
    for name, scenario_fn in SCENARIOS:
        if hasattr(api, "_dialog_answers"):
            api._dialog_answers.clear()
        page.evaluate("window.FOSS.router.open('encoding', 'text')")
        scenario_fn(page, fixtures, api)
