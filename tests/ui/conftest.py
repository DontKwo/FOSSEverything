import os
import shutil
import time
from pathlib import Path
from typing import Any, Generator

from playwright.sync_api import Browser, Page, sync_playwright
import pytest

from app.web.api import WebApi
from tests.fixtures import make_fixtures
from tests.ui.harness import VIEWPORTS, launch_browser, make_page, write_report


def pytest_addoption(parser: pytest.Parser) -> None:
    # Register pytest flag to update perceptual baselines.
    parser.addoption("--update-baselines", action="store_true", default=False)


@pytest.fixture(scope="session")
def run_dir() -> Path:
    # Return unique run output directory for UI test artifacts.
    run_id = time.strftime("%Y%m%d-%H%M%S")
    d = Path("tests/ui/_out") / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture(scope="session")
def records() -> list[dict[str, Any]]:
    # Session-wide list collecting audit and capture records.
    return []


@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    # Session fixture launching Chromium/Edge headless browser.
    with sync_playwright() as p:
        b = launch_browser(p)
        yield b
        b.close()


@pytest.fixture
def page(browser: Browser, api: Any) -> Generator[Page, None, None]:
    # Per-test page fixture for walkthrough and scenario execution.
    if hasattr(api, "_dialog_answers"):
        api._dialog_answers.clear()
    session = make_page(browser, api, VIEWPORTS[0], theme="dark", ui_scale=1.0)
    p = session["page"]
    try:
        yield p
    finally:
        if hasattr(api, "_dialog_answers"):
            api._dialog_answers.clear()
        p.close()


@pytest.fixture(scope="session")
def api(tmp_path_factory: pytest.TempPathFactory) -> Any:
    # Session fixture providing WebApi instance with isolated settings.
    settings_dir = tmp_path_factory.mktemp("settings")
    os.environ["FOSS_SETTINGS_DIR"] = str(settings_dir)
    instance = WebApi()
    if not hasattr(instance, "_dialog_answers"):
        instance._dialog_answers = []
    return instance


@pytest.fixture(scope="session")
def fixtures(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    # Session fixture generating test fixture files.
    f_dir = tmp_path_factory.mktemp("fixtures")
    return make_fixtures(f_dir)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    # Hook to write final UI audit report and optionally update baselines.
    try:
        r_dir = getattr(session.config, "_foss_run_dir", None)
        recs = getattr(session.config, "_foss_records", [])
        if r_dir:
            write_report(r_dir, recs)

            if session.config.getoption("--update-baselines"):
                baselines_dir = Path("tests/ui/baselines")
                baselines_dir.mkdir(parents=True, exist_ok=True)
                for png in r_dir.rglob("*.png"):
                    if not png.name.startswith("contact_"):
                        shutil.copy(png, baselines_dir / png.name)
    except Exception:  # noqa: 10
        pass
