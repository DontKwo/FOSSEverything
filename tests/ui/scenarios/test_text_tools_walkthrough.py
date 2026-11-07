from typing import Any
from playwright.sync_api import Page, expect


def test_text_tools_walkthrough(page: Page, api: Any) -> None:
    # Full walkthrough of the text tools module.
    page.evaluate("window.FOSS.router.open('text_tools', 'main')")

    # 1. Transforms
    in_box = page.locator("[data-testid='text_tools-input-input']")
    in_box.fill("hello world")
    page.click("[data-testid='text_tools-case-upper']")
    out_box = page.locator("[data-testid='text_tools-output-input']")
    expect(out_box).to_have_value("HELLO WORLD")

    # 2. Diff checker
    page.evaluate("window.FOSS.router.open('text_tools', 'diff')")
    diff_left = page.locator("[data-testid='text_tools-diff-left-input']")
    diff_right = page.locator("[data-testid='text_tools-diff-right-input']")
    diff_left.fill("line one\nline two")
    diff_right.fill("line one\nline three")
    page.click("[data-testid='text_tools-diff-compare']")
    diff_out = page.locator("[data-testid='text_tools-diff-output-input']")
    expect(diff_out).not_to_have_value("")

    # 3. Word counter
    page.evaluate("window.FOSS.router.open('text_tools', 'counter')")
    cnt_box = page.locator("[data-testid='text_tools-counter-input-input']")
    cnt_box.fill(
        "Antigravity open source software suite provides private offline tools."
    )
    page.wait_for_timeout(350)
    words_el = page.locator("[data-testid='text_tools-stat-words']")
    expect(words_el).to_have_text("9")

    # 4. Grammar & Citations
    page.evaluate("window.FOSS.router.open('text_tools', 'writing')")
    cit_title = page.locator("[data-testid='text_tools-cit-title']")
    cit_title.fill("Example Citation")
    page.click("[data-testid='text_tools-citation-generate']")
    cit_out = page.locator("[data-testid='text_tools-citation-output']")
    expect(cit_out).to_contain_text("Example Citation")
