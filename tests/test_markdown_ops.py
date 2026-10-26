"""Unit tests for Markdown parsing, toolbar helpers, and WebApi exports."""
from __future__ import annotations

import os
import tempfile
import unittest

from app.features.markdown import ops as md_ops
from app.web.api import WebApi


class TestMarkdownOps(unittest.TestCase):
    """Test suite for Markdown Studio parsing and manipulation helpers."""

    def test_render_headings_and_paragraphs(self) -> None:
        raw = "# Heading 1\n## Heading 2\n### Heading 3\nSimple paragraph text."
        html_out = md_ops.render_markdown_to_html(raw)
        self.assertIn("<h1>Heading 1</h1>", html_out)
        self.assertIn("<h2>Heading 2</h2>", html_out)
        self.assertIn("<h3>Heading 3</h3>", html_out)
        self.assertIn("<p>Simple paragraph text.</p>", html_out)

    def test_render_inline_styling(self) -> None:
        raw = "**bold** and *italic* and ~~strike~~ and `inline_code`."
        html_out = md_ops.render_markdown_to_html(raw)
        self.assertIn("<strong>bold</strong>", html_out)
        self.assertIn("<em>italic</em>", html_out)
        self.assertIn("<del>strike</del>", html_out)
        self.assertIn("<code>inline_code</code>", html_out)

    def test_render_links_and_images(self) -> None:
        raw = "[Link](https://example.com)\n\n![Alt](https://example.com/a.png)"
        html_out = md_ops.render_markdown_to_html(raw)
        self.assertIn('<a href="https://example.com">Link</a>', html_out)
        self.assertIn('<img src="https://example.com/a.png" alt="Alt">', html_out)

    def test_render_lists(self) -> None:
        raw_u = "- Item 1\n- Item 2"
        html_u = md_ops.render_markdown_to_html(raw_u)
        self.assertIn("<ul><li>Item 1</li><li>Item 2</li></ul>", html_u)

        raw_o = "1. First\n2. Second"
        html_o = md_ops.render_markdown_to_html(raw_o)
        self.assertIn("<ol><li>First</li><li>Second</li></ol>", html_o)

    def test_render_code_block_and_quote(self) -> None:
        raw_code = "```python\nx = 42\n```"
        html_code = md_ops.render_markdown_to_html(raw_code)
        self.assertIn("<pre><code>x = 42</code></pre>", html_code)

        raw_quote = "> This is a quoted line."
        html_quote = md_ops.render_markdown_to_html(raw_quote)
        self.assertIn("<blockquote>", html_quote)
        self.assertIn("This is a quoted line.", html_quote)

    def test_render_table(self) -> None:
        raw_table = "| Col A | Col B |\n|---|---|\n| 1 | 2 |"
        html_table = md_ops.render_markdown_to_html(raw_table)
        self.assertIn('<table border="1">', html_table)
        self.assertIn("<th>Col A</th>", html_table)
        self.assertIn("<td>1</td>", html_table)

    def test_render_horizontal_rule(self) -> None:
        raw_hr = "Paragraph before\n\n---\n\nParagraph after"
        html_hr = md_ops.render_markdown_to_html(raw_hr)
        self.assertIn("<hr>", html_hr)

    def test_toolbar_text_helpers(self) -> None:
        wrapped = md_ops.wrap_or_placeholder("sample", "**", "**")
        self.assertEqual(wrapped, "**sample**")

        unwrapped = md_ops.wrap_or_placeholder("**sample**", "**", "**")
        self.assertEqual(unwrapped, "sample")

        default_wrap = md_ops.wrap_or_placeholder("", "`", "`", "code")
        self.assertEqual(default_wrap, "`code`")

        h1_line = md_ops.toggle_heading("Title", 1)
        self.assertEqual(h1_line, "# Title")
        self.assertEqual(md_ops.toggle_heading(h1_line, 1), "Title")

        list_line = md_ops.toggle_list_item("item", ordered=False)
        self.assertEqual(list_line, "- item")
        self.assertEqual(md_ops.toggle_list_item(list_line, ordered=False), "item")

        quote_line = md_ops.toggle_blockquote("text")
        self.assertEqual(quote_line, "> text")
        self.assertEqual(md_ops.toggle_blockquote(quote_line), "text")

        link_str = md_ops.make_link("Docs")
        self.assertEqual(link_str, "[Docs](https://)")

        table_skel = md_ops.markdown_table_skeleton(rows=2, cols=2)
        self.assertIn("| Header 1 | Header 2 |", table_skel)


class TestMarkdownWebApi(unittest.TestCase):
    """Test suite for Markdown Studio WebApi endpoints."""

    def setUp(self) -> None:
        self.api = WebApi()

    def test_render_markdown_api(self) -> None:
        res = self.api.render_markdown("# Title\n\n**Body**")
        self.assertIn("html", res)
        self.assertIn("<h1>Title</h1>", res["html"])
        self.assertIn("<strong>Body</strong>", res["html"])

    def test_export_html_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = os.path.join(tmp_dir, "test_doc.html")
            res = self.api.markdown_export_html("# Heading\n\nContent", out_file)
            self.assertTrue(res.get("success"))
            self.assertTrue(os.path.isfile(out_file))
            with open(out_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("<!DOCTYPE html>", content)
            self.assertIn("<h1>Heading</h1>", content)

    def test_export_pdf_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = os.path.join(tmp_dir, "test_doc.pdf")
            res = self.api.markdown_export_pdf("# PDF Title\n\nParagraph in PDF", out_file)
            self.assertTrue(res.get("success"))
            self.assertTrue(os.path.isfile(out_file))
            self.assertGreater(os.path.getsize(out_file), 500)


if __name__ == "__main__":
    unittest.main()
