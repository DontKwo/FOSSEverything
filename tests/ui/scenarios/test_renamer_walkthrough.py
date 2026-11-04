from typing import Any

from playwright.sync_api import Page

from tests.ui.scenarios.renamer import SCENARIOS


def test_renamer_walkthrough(page: Page, api: Any, fixtures: dict[str, str]) -> None:
    # Execute all renamer scenarios sequentially for walkthrough coverage.
    for name, scenario_fn in SCENARIOS:
        api._dialog_answers.clear()

        try:
            page.evaluate("window.FOSS.router.open('renamer', 'main')")
            page.wait_for_timeout(100)
            clear_btn = page.locator("button", has_text="Clear")
            if clear_btn.count() > 0 and clear_btn.first.is_visible():
                clear_btn.first.click()
                page.wait_for_timeout(100)
        except Exception:
            pass

        scenario_fn(page, fixtures, api)
