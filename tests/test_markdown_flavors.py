# Unit tests for multi-flavor markdown parsing, sub-bullets, and typography.
import unittest

from app.features.markdown.ops import (
    SUPPORTED_MARKDOWN_FLAVORS,
    build_styled_markdown_document,
    callout_block,
    code_block,
    footnote_snippet,
    indent_lines,
    make_image,
    make_link,
    outdent_lines,
    render_markdown_to_html,
    toggle_heading,
    toggle_list_item,
    toggle_task_item,
    wrap_or_placeholder,
)


class TestMarkdownFlavors(unittest.TestCase):
    # Verify nested lists, GFM task lists, alerts, footnotes, and parser flavors.

    def test_nested_sub_bullets(self) -> None:
        # Verify markdown-it renders nested unordered lists cleanly.
        md_src = "- Parent A\n  - Child A1\n  - Child A2\n    - Grandchild A2a\n- Parent B"
        html_out = render_markdown_to_html(md_src, flavor="github")
        self.assertIn("<ul>", html_out)
        self.assertIn("<li>Parent A", html_out)
        self.assertIn("<li>Child A1</li>", html_out)
        self.assertIn("<li>Grandchild A2a</li>", html_out)
        self.assertIn("<li>Parent B</li>", html_out)

    def test_task_lists(self) -> None:
        # Verify GFM task checkboxes transform into disabled input elements.
        md_src = "- [ ] Pending task\n- [x] Finished task"
        html_out = render_markdown_to_html(md_src, flavor="github")
        self.assertIn('class="task-list-item"', html_out)
        self.assertIn('<input type="checkbox" disabled> Pending task', html_out)
        self.assertIn('<input type="checkbox" disabled checked> Finished task', html_out)

    def test_github_alerts(self) -> None:
        # Verify blockquote alert callouts render styled alert containers.
        md_src = "> [!NOTE]\n> General notice.\n\n> [!WARNING]\n> Extreme hazard."
        html_out = render_markdown_to_html(md_src, flavor="github")
        self.assertIn('class="markdown-alert markdown-alert-note"', html_out)
        self.assertIn('<p class="markdown-alert-title">Note</p>', html_out)
        self.assertIn('class="markdown-alert markdown-alert-warning"', html_out)
        self.assertIn('<p class="markdown-alert-title">Warning</p>', html_out)

    def test_footnotes(self) -> None:
        # Verify inline footnote links and appended footnote list section.
        md_src = "Statement with citation[^demo].\n\n[^demo]: Reference details."
        html_out = render_markdown_to_html(md_src, flavor="github")
        self.assertIn('<sup class="footnote-ref"><a href="#fn-demo" id="fnref-demo">[demo]</a></sup>', html_out)
        self.assertIn('<section class="footnotes">', html_out)
        self.assertIn('<li id="fn-demo">', html_out)

    def test_flavor_differences(self) -> None:
        # Verify GFM table and strikethrough vs CommonMark strict parsing.
        table_src = "| A | B |\n|---|---|\n| 1 | 2 |"
        strike_src = "~~struck text~~"

        gfm_table = render_markdown_to_html(table_src, flavor="github")
        gfm_strike = render_markdown_to_html(strike_src, flavor="github")
        self.assertIn("<table>", gfm_table)
        self.assertIn("<s>", gfm_strike)

        cm_table = render_markdown_to_html(table_src, flavor="commonmark")
        cm_strike = render_markdown_to_html(strike_src, flavor="commonmark")
        self.assertNotIn("<table>", cm_table)
        self.assertNotIn("<s>", cm_strike)

        self.assertIn("github", SUPPORTED_MARKDOWN_FLAVORS)
        self.assertIn("commonmark", SUPPORTED_MARKDOWN_FLAVORS)
        self.assertIn("extra", SUPPORTED_MARKDOWN_FLAVORS)
        self.assertIn("minimal", SUPPORTED_MARKDOWN_FLAVORS)

    def test_indent_outdent_and_helpers(self) -> None:
        # Verify pure text manipulation and snippet formatting helpers.
        text = "line1\nline2"
        indented = indent_lines(text, spaces=2)
        self.assertEqual(indented, "  line1\n  line2")
        outdented = outdent_lines(indented, spaces=2)
        self.assertEqual(outdented, text)

        self.assertEqual(toggle_task_item("item"), "- [ ] item")
        self.assertEqual(toggle_task_item("- [ ] item"), "- [x] item")
        self.assertEqual(toggle_task_item("- [x] item"), "- [ ] item")

        self.assertEqual(callout_block("TIP", "Helpful advice."), "> [!TIP]\n> Helpful advice.")
        self.assertEqual(footnote_snippet(2), "[^2]\n\n[^2]: Footnote text here.")

        self.assertEqual(wrap_or_placeholder("text", "**", "**"), "**text**")
        self.assertEqual(wrap_or_placeholder("**text**", "**", "**"), "text")
        self.assertEqual(wrap_or_placeholder("", "**", "**", placeholder="bold"), "**bold**")
        self.assertEqual(code_block("x = 1", language="python"), "```python\nx = 1\n```")
        self.assertEqual(make_link("doc", "https://example.com"), "[doc](https://example.com)")
        self.assertEqual(make_image("pic", "https://example.com/p.png"), "![pic](https://example.com/p.png)")
        self.assertEqual(toggle_heading("Title", 2), "## Title")
        self.assertEqual(toggle_list_item("Bullet", ordered=False), "- Bullet")

    def test_build_styled_markdown_document(self) -> None:
        # Verify complete styled document structure for HTML and PDF exports.
        doc_html = build_styled_markdown_document("# Heading\n\nParagraph", flavor="github", theme_mode="dark")
        self.assertIn("<!DOCTYPE html>", doc_html)
        self.assertIn("<style>", doc_html)
        self.assertIn("markdown-body", doc_html)
        self.assertIn("<h1>Heading</h1>", doc_html)


class TestMarkdownTaskLists(unittest.TestCase):
    # Verify task list checkboxes render for tight and loose lists.

    def test_tight_task_list_checkboxes(self) -> None:
        # Tight task items become checkbox list items.
        html_out = render_markdown_to_html("- [ ] open\n- [x] done", flavor="gfm")
        self.assertEqual(html_out.count('class="task-list-item"'), 2)
        self.assertIn('<input type="checkbox" disabled checked>', html_out)

    def test_loose_task_list_checkboxes(self) -> None:
        # Loose task items keep their paragraph wrapper and still get a checkbox.
        html_out = render_markdown_to_html("- [ ] first\n\n- [x] second", flavor="gfm")
        self.assertEqual(html_out.count('class="task-list-item"'), 2)
        self.assertIn('<p><input type="checkbox" disabled> first</p>', html_out)

    def test_math_markup(self) -> None:
        # Inline and display math produce KaTeX-ready containers.
        html_out = render_markdown_to_html("Inline $x^2$ and\n\n$$a+b$$", flavor="gfm")
        self.assertIn("katex-inline-math", html_out)
        self.assertIn("katex-display-math", html_out)
