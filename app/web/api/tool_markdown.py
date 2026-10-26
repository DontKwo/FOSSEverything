from pathlib import Path
from typing import Any

from app.features.markdown.ops import (
    code_block,
    horizontal_rule,
    html_table_skeleton,
    make_image,
    make_link,
    markdown_table_skeleton,
    render_markdown_to_html,
    toggle_blockquote,
    toggle_heading,
    toggle_list_item,
    wrap_or_placeholder,
)
from app.web.api.result import api_method, ok, require


class MarkdownApiMixin:
    @api_method
    def markdown_to_html(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert markdown text into HTML representation.
        require(params, "markdown")
        md_text = str(params["markdown"])
        html_out = render_markdown_to_html(md_text)
        return ok(html=html_out)

    @api_method
    def render_markdown(self, params: dict[str, Any]) -> dict[str, Any]:
        # Render markdown content alias.
        return self.markdown_to_html(params)

    @api_method
    def markdown_export_html(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export markdown content to standalone HTML document.
        require(params, "markdown", "output_path")
        md_text = str(params["markdown"])
        out_path = Path(params["output_path"]).resolve()
        html_body = render_markdown_to_html(md_text)
        full_html = (
            "<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"utf-8\">\n"
            "<title>Markdown Document</title>\n"
            "<style>body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; }</style>\n"
            f"</head>\n<body>\n{html_body}\n</body>\n</html>"
        )
        out_path.write_text(full_html, encoding="utf-8")
        return ok(output_path=str(out_path))

    @api_method
    def markdown_export_pdf(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export markdown content to PDF via PyMuPDF story or document.
        require(params, "markdown", "output_path")
        import pymupdf

        md_text = str(params["markdown"])
        out_path = Path(params["output_path"]).resolve()
        html_body = render_markdown_to_html(md_text)

        doc = pymupdf.open()
        story = pymupdf.Story(html=html_body)
        writer = pymupdf.DocumentWriter(str(out_path))
        mediabox = pymupdf.paper_rect("letter")
        where = mediabox + (36, 36, -36, -36)
        more = 1
        while more:
            device = writer.begin_page(mediabox)
            more, _ = story.place(where)
            story.draw(device)
            writer.end_page()
        writer.close()
        doc.close()
        return ok(output_path=str(out_path))

    @api_method
    def markdown_format_snippet(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate or toggle formatting snippets in markdown.
        require(params, "snippet_type")
        st = str(params["snippet_type"]).lower()
        text = str(params.get("text", ""))

        if st == "code_block":
            res = code_block(text, language=str(params.get("language", "")))
        elif st == "horizontal_rule":
            res = horizontal_rule()
        elif st == "html_table":
            rows = int(params.get("rows", 3))
            cols = int(params.get("cols", 3))
            res = html_table_skeleton(rows=rows, cols=cols)
        elif st == "markdown_table":
            rows = int(params.get("rows", 3))
            cols = int(params.get("cols", 3))
            res = markdown_table_skeleton(rows=rows, cols=cols)
        elif st == "image":
            res = make_image(str(params.get("alt", "image")), str(params.get("url", "")))
        elif st == "link":
            res = make_link(str(params.get("label", "link")), str(params.get("url", "")))
        elif st == "blockquote":
            res = toggle_blockquote(text)
        elif st == "heading":
            res = toggle_heading(text, level=int(params.get("level", 1)))
        elif st == "list_item":
            ordered = bool(params.get("ordered", False))
            res = toggle_list_item(text, ordered=ordered)
        elif st == "wrap":
            marker = str(params.get("marker", "**"))
            res = wrap_or_placeholder(text, marker=marker, placeholder=str(params.get("placeholder", "text")))
        else:
            res = text
        return ok(snippet=res)
