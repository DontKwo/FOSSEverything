from pathlib import Path
from typing import Any, Callable
from playwright.sync_api import Page, expect


def calc_clear_overlays(page: Page) -> None:
    # Clear tooltips, toasts, and reset view scroll.
    try:
        page.mouse.move(0, 0)
    except Exception:
        page.wait_for_timeout(0)
    page.evaluate(
        "if (window.FOSS && window.FOSS.tooltips) window.FOSS.tooltips.hide(); "
        "var t = document.getElementById('tooltip-host'); if (t) t.innerHTML = ''; "
        "var h = document.getElementById('toast-host'); if (h) h.innerHTML = ''; "
        "document.querySelectorAll('*').forEach(function (el) { if (el.scrollTop) el.scrollTop = 0; if (el.scrollLeft) el.scrollLeft = 0; }); "
        "window.scrollTo(0, 0);"
    )


def scenario_personal(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Open personal tab and populate contact and summary details.
    page.evaluate("window.FOSS.router.open('resume', 'personal')")
    page.wait_for_timeout(200)

    expect(page.locator("[data-testid='resume-offline-badge']")).to_be_visible()
    expect(page.locator("[data-testid='resume-contact-card']")).to_be_visible()
    expect(page.locator("[data-testid='resume-summary-card']")).to_be_visible()

    page.fill("[data-testid='resume-name-input']", "Jordan Developer")
    page.fill("[data-testid='resume-title-input']", "Principal Systems Architect")
    page.wait_for_timeout(100)
    calc_clear_overlays(page)


def scenario_sections(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Add new section and verify bullet controls in sections tab.
    page.evaluate("window.FOSS.router.open('resume', 'sections')")
    page.wait_for_timeout(200)

    expect(page.locator("[data-testid='resume-master-mgmt']")).to_be_visible()
    page.click("[data-testid='resume-add-sec-btn']")
    page.wait_for_timeout(150)

    first_bullet = page.locator("[data-testid='resume-bullet-toggle']").first
    expect(first_bullet).to_be_visible()
    calc_clear_overlays(page)


def scenario_profiles(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Input target job posting and run ATS keyword match analyzer.
    page.evaluate("window.FOSS.router.open('resume', 'profiles')")
    page.wait_for_timeout(200)

    expect(page.locator("[data-testid='resume-profile-select']")).to_be_visible()
    sample_jd = "Senior Python engineer with Kubernetes, distributed systems, and Redis experience."
    page.fill("[data-testid='resume-job-desc-input']", sample_jd)
    page.click("[data-testid='resume-analyze-ats-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='resume-ats-results']")).to_be_visible()
    calc_clear_overlays(page)


def scenario_preview(page: Page, fixtures: dict[str, str], api: Any) -> None:
    # Exercise preview toolbar modes and export plain text through the Save As dialog.
    sample = fixtures.get("sample.txt", "sample.txt")
    out_txt = str(Path(sample).parent / "out_resume.txt")
    api._dialog_answers.append(out_txt)

    page.evaluate("window.FOSS.router.open('resume', 'preview')")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='resume-preview-stage']")).to_be_visible()
    for testid in ["resume-fit-page", "resume-zoom-50", "resume-zoom-125", "resume-fit-width"]:
        page.click(f"[data-testid='{testid}']")
        expect(page.locator(f"[data-testid='{testid}']")).to_have_attribute("aria-pressed", "true")
    page.click("[data-testid='resume-export-txt-btn']")
    page.wait_for_timeout(300)

    expect(page.locator("[data-testid='resume-export-result']")).to_be_visible()
    assert Path(out_txt).exists()
    calc_clear_overlays(page)


SCENARIOS: list[tuple[str, Callable[[Page, dict[str, str], Any], None]]] = [
    ("personal", scenario_personal),
    ("sections", scenario_sections),
    ("profiles", scenario_profiles),
    ("preview", scenario_preview),
]
