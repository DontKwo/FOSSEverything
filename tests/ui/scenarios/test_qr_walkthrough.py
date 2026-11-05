from typing import Any, Callable

import pytest
from playwright.sync_api import Page

from tests.ui.scenarios.qr import SCENARIOS


@pytest.mark.parametrize("name, scenario_func", SCENARIOS)
def test_qr_walkthrough(
    name: str,
    scenario_func: Callable[[Page, dict[str, str], Any], None],
    page: Page,
    fixtures: dict[str, str],
    api: Any,
) -> None:
    # Execute parametrized QR scenario.
    scenario_func(page, fixtures, api)
