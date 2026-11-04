"""Headless Markdown <-> HTML conversion and text-insertion helpers for Markdown Studio."""
from __future__ import annotations

import html
import re
from typing import Any
from markdown_it import MarkdownIt
import pygments
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer

SUPPORTED_MARKDOWN_FLAVORS: dict[str, str] = {
    "github": "GitHub Flavored Markdown (GFM)",
    "gfm": "GitHub Flavored Markdown (GFM)",
    "commonmark": "CommonMark (Strict)",
    "strict": "Strict Standard Markdown",
    "extra": "Markdown Extra (Footnotes, Def Lists, Smart Typography)",
    "minimal": "Minimal Markdown (Basic Blocks Only)",
}

_ALERT_PATTERN = re.compile(
    r"<blockquote>\s*<p>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*?)</p>(.*?)</blockquote>",
    re.DOTALL | re.IGNORECASE,
)
_FOOTNOTE_REF_PATTERN = re.compile(r"\[\^([a-zA-Z0-9_-]+)\](?!:)")
_FOOTNOTE_DEF_PATTERN = re.compile(r"^\[\^([a-zA-Z0-9_-]+)\]:\s*(.*)$", re.MULTILINE)
_CODE_BLOCK_PATTERN = re.compile(r'<pre><code class="language-([a-zA-Z0-9_+-]+)">(.*?)</code></pre>', re.DOTALL)


def render_markdown_to_html(text: str, flavor: str = "github") -> str:
    # Convert markdown text into HTML using markdown-it-py with chosen flavor.
    if not text.strip():
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    flavor_key = (flavor or "github").lower().strip()

    if flavor_key in ("commonmark", "strict", "strict standard markdown"):
        md = MarkdownIt("commonmark", {"html": True, "linkify": False})
        return md.render(normalized)

    if flavor_key == "minimal":
        md = MarkdownIt("zero", {"html": False}).enable(
            ["heading", "paragraph", "list", "emphasis", "link", "backticks", "fence"]
        )
        return md.render(normalized)

    # Footnote extraction for github and extra flavors
    footnotes: list[tuple[str, str]] = []

    def _extract_fn_def(match: re.Match[str]) -> str:
        fn_id, fn_text = match.group(1), match.group(2)
        footnotes.append((fn_id, fn_text))
        return ""

    body_text = _FOOTNOTE_DEF_PATTERN.sub(_extract_fn_def, normalized)

    # Handle Extra flavor specific syntax (TOC, definition lists, sup/sub)
    if flavor_key == "extra":
        # Definition lists: Term\n: Definition
        body_text = re.sub(
            r"^([^\n:]+)\n:\s+(.+)$",
            r"<dl><dt>\1</dt><dd>\2</dd></dl>",
            body_text,
            flags=re.MULTILINE,
        )
        # Superscript ^text^ and Subscript ~text~
        body_text = re.sub(r"\^([^\s^]+)\^", r"<sup>\1</sup>", body_text)
        body_text = re.sub(r"~([^\s~]+)~", r"<sub>\1</sub>", body_text)

        md = MarkdownIt("gfm-like", {"html": True, "linkify": False, "typographer": True}).enable(
            ["table", "strikethrough"]
        )
    else:
        md = MarkdownIt("gfm-like", {"html": True, "linkify": False, "breaks": False, "typographer": False}).enable(
            ["table", "strikethrough"]
        )

    rendered = md.render(body_text)

    # Task list checkbox transformation
    rendered = re.sub(
        r"<li>\s*\[ \]\s+",
        r'<li class="task-list-item"><input type="checkbox" disabled> ',
        rendered,
    )
    rendered = re.sub(
        r"<li>\s*\[[xX]\]\s+",
        r'<li class="task-list-item"><input type="checkbox" disabled checked> ',
        rendered,
    )

    # GFM Alert / Callout transformation
    def _replace_alert(m: re.Match[str]) -> str:
        kind = m.group(1).upper()
        first_line = m.group(2)
        rest = m.group(3)
        return (
            f'<div class="markdown-alert markdown-alert-{kind.lower()}">'
            f'<p class="markdown-alert-title">{kind.title()}</p>'
            f'<p>{first_line}</p>{rest}</div>'
        )

    rendered = _ALERT_PATTERN.sub(_replace_alert, rendered)

    # Footnote inline link replacement
    rendered = _FOOTNOTE_REF_PATTERN.sub(
        r'<sup class="footnote-ref"><a href="#fn-\1" id="fnref-\1">[\1]</a></sup>',
        rendered,
    )

    # Pygments syntax highlighting
    def _highlight_code(m: re.Match[str]) -> str:
        lang, code_raw = m.group(1), m.group(2)
        unescaped = html.unescape(code_raw)
        try:
            lexer = get_lexer_by_name(lang, stripall=True)
            formatter = HtmlFormatter(nowrap=True)
            highlighted = pygments.highlight(unescaped, lexer, formatter)
            return (
                f'<div class="code-header"><span class="code-lang">{html.escape(lang)}</span></div>'
                f'<pre><code class="language-{html.escape(lang)}">{highlighted}</code></pre>'
            )
        except Exception:
            return m.group(0)

    rendered = _CODE_BLOCK_PATTERN.sub(_highlight_code, rendered)

    # KaTeX math formula transformations
    def _replace_display_math(m: re.Match[str]) -> str:
        formula = m.group(1).strip()
        return f'<div class="katex-display-math"><span class="math display">\\[{html.escape(formula)}\\]</span></div>'

    def _replace_inline_math(m: re.Match[str]) -> str:
        formula = m.group(1).strip()
        return f'<span class="katex-inline-math"><span class="math inline">\\({html.escape(formula)}\\)</span></span>'

    rendered = re.sub(r"\$\$(.+?)\$\$", _replace_display_math, rendered, flags=re.DOTALL)
    rendered = re.sub(r"(?<!\$)\$(?!\$)([^\n$]+?)(?<!\$)\$(?!\$)", _replace_inline_math, rendered)

    # Append footnote list if footnotes were defined
    if footnotes:
        items = "".join(
            f'<li id="fn-{html.escape(fid)}"><p>{html.escape(ftext)} '
            f'<a href="#fnref-{html.escape(fid)}" class="footnote-backref">&#8617;</a></p></li>'
            for fid, ftext in footnotes
        )
        rendered += f'\n<section class="footnotes"><ol>{items}</ol></section>'

    return rendered


def build_styled_markdown_document(
    text: str,
    flavor: str = "github",
    theme_mode: str = "dark",
    for_pdf: bool = False,
) -> str:
    # Render complete HTML document with GitHub typography styles for preview or export.
    body_html = render_markdown_to_html(text, flavor=flavor)
    is_dark = theme_mode.lower() == "dark" and not for_pdf

    bg_color = "#0d1322" if is_dark else "#ffffff"
    text_color = "#e6edf3" if is_dark else "#1f2328"
    border_color = "#30363d" if is_dark else "#d0d7de"
    code_bg = "#161b22" if is_dark else "#f6f8fa"
    table_alt = "#161b22" if is_dark else "#f6f8fa"
    link_color = "#58a6ff" if is_dark else "#0969da"

    css = f"""
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
      font-size: 15px;
      line-height: 1.6;
      word-wrap: break-word;
      background-color: {bg_color};
      color: {text_color};
      margin: 0;
      padding: {"24px" if not for_pdf else "0"};
    }}
    a {{ color: {link_color}; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    h1, h2, h3, h4, h5, h6 {{
      margin-top: 24px;
      margin-bottom: 16px;
      font-weight: 600;
      line-height: 1.25;
    }}
    h1 {{ font-size: 2em; padding-bottom: 0.3em; border-bottom: 1px solid {border_color}; }}
    h2 {{ font-size: 1.5em; padding-bottom: 0.3em; border-bottom: 1px solid {border_color}; }}
    h3 {{ font-size: 1.25em; }}
    p, blockquote, ul, ol, dl, table, pre, details {{
      margin-top: 0;
      margin-bottom: 16px;
    }}
    ul {{ list-style-type: disc; padding-left: 2em; }}
    ul ul {{ list-style-type: circle; }}
    ul ul ul {{ list-style-type: square; }}
    ol {{ list-style-type: decimal; padding-left: 2em; }}
    ol ol {{ list-style-type: lower-alpha; }}
    ol ol ol {{ list-style-type: lower-roman; }}
    li + li {{ margin-top: 0.25em; }}
    .task-list-item {{ list-style-type: none; margin-left: -1.25em; }}
    .task-list-item input {{ margin-right: 0.5em; vertical-align: middle; }}
    blockquote {{
      padding: 0 1em;
      color: #8c959f;
      border-left: 0.25em solid {border_color};
      margin: 0 0 16px 0;
    }}
    table {{
      border-spacing: 0;
      border-collapse: collapse;
      width: 100%;
      margin-bottom: 16px;
      page-break-inside: avoid;
    }}
    table th, table td {{
      padding: 6px 13px;
      border: 1px solid {border_color};
    }}
    table tr:nth-child(2n) {{ background-color: {table_alt}; }}
    code {{
      padding: 0.2em 0.4em;
      margin: 0;
      font-size: 85%;
      background-color: {code_bg};
      border-radius: 6px;
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    }}
    pre {{
      padding: 16px;
      overflow: auto;
      font-size: 85%;
      line-height: 1.45;
      background-color: {code_bg};
      border-radius: 6px;
      page-break-inside: avoid;
    }}
    pre code {{ padding: 0; background-color: transparent; }}
    .code-header {{
      background: {table_alt};
      border: 1px solid {border_color};
      border-bottom: none;
      padding: 4px 12px;
      font-size: 12px;
      font-family: monospace;
      color: #8c959f;
      border-top-left-radius: 6px;
      border-top-right-radius: 6px;
    }}
    .code-header + pre {{
      border-top-left-radius: 0;
      border-top-right-radius: 0;
      border: 1px solid {border_color};
    }}
    .markdown-alert {{
      padding: 8px 16px;
      margin-bottom: 16px;
      border-left: 0.25em solid #0969da;
      background-color: {code_bg};
      border-radius: 0 6px 6px 0;
    }}
    .markdown-alert-note {{ border-left-color: #0969da; }}
    .markdown-alert-tip {{ border-left-color: #1a7f37; }}
    .markdown-alert-important {{ border-left-color: #8250df; }}
    .markdown-alert-warning {{ border-left-color: #9a6700; }}
    .markdown-alert-caution {{ border-left-color: #cf222e; }}
    .markdown-alert-title {{ font-weight: 600; margin-bottom: 4px; }}
    .footnotes {{
      font-size: 12px;
      border-top: 1px solid {border_color};
      padding-top: 16px;
      color: #8c959f;
    }}
    """

    return (
        "<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"utf-8\">\n"
        "<title>Markdown Document</title>\n"
        f"<style>{css}</style>\n"
        f"</head>\n<body>\n<div class=\"markdown-body\">{body_html}</div>\n</body>\n</html>"
    )


# Pure toolbar-insertion and indentation helpers

def indent_lines(text: str, spaces: int = 2) -> str:
    # Indent every non-empty line by given number of spaces.
    prefix = " " * spaces
    return "\n".join(prefix + line if line.strip() else line for line in text.split("\n"))


def outdent_lines(text: str, spaces: int = 2) -> str:
    # Remove up to spaces leading whitespace characters from each line.
    lines = text.split("\n")
    res: list[str] = []
    for line in lines:
        stripped = 0
        while stripped < spaces and line.startswith(" "):
            line = line[1:]
            stripped += 1
        res.append(line)
    return "\n".join(res)


def toggle_task_item(line: str) -> str:
    # Apply or cycle task checkbox marker on line.
    match = re.match(r"^(\s*[-*+]\s+)\[([ xX])\]\s+(.*)$", line)
    if match:
        prefix = match.group(1)
        state = match.group(2)
        content = match.group(3)
        next_state = " " if state.lower() == "x" else "x"
        return f"{prefix}[{next_state}] {content}"
    list_match = re.match(r"^(\s*[-*+]\s+)(.*)$", line)
    if list_match:
        return f"{list_match.group(1)}[ ] {list_match.group(2)}"
    return f"- [ ] {line}"


def callout_block(kind: str = "NOTE", body: str = "Important details here.") -> str:
    # Return GitHub-flavored Markdown alert callout block.
    return f"> [!{kind.upper()}]\n> {body}"


def footnote_snippet(index: int = 1) -> str:
    # Return paired footnote reference and definition snippet.
    return f"[^{index}]\n\n[^{index}]: Footnote text here."


def wrap_or_placeholder(
    selected: str,
    marker_open: str = "",
    marker_close: str = "",
    placeholder: str = "text",
    marker: str = "",
) -> str:
    # Wrap selected text with markdown markers, toggling off if already present.
    m_open = marker_open or marker or "**"
    m_close = marker_close or m_open
    if selected:
        if (
            selected.startswith(m_open)
            and selected.endswith(m_close)
            and len(selected) >= len(m_open) + len(m_close)
        ):
            return selected[len(m_open) : len(selected) - len(m_close)]
        return f"{m_open}{selected}{m_close}"
    return f"{m_open}{placeholder}{m_close}"


def toggle_heading(line: str, level: int) -> str:
    # Apply or remove an ATX heading prefix of level on line.
    match = re.match(r"^(#{1,6})\s+(.*)$", line)
    content = match.group(2) if match else line
    if match and len(match.group(1)) == level:
        return content
    return f"{'#' * level} {content}"


def toggle_list_item(line: str, ordered: bool, number: int = 1) -> str:
    # Apply or remove list marker on line.
    unordered_match = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
    ordered_match = re.match(r"^(\s*)\d+[.)]\s+(.*)$", line)
    if unordered_match:
        content = unordered_match.group(2)
    elif ordered_match:
        content = ordered_match.group(2)
    else:
        content = line
    if ordered:
        if ordered_match:
            return content
        return f"{number}. {content}"
    if unordered_match:
        return content
    return f"- {content}"


def toggle_blockquote(line: str) -> str:
    # Apply or remove blockquote prefix on line.
    match = re.match(r"^>\s?(.*)$", line)
    if match:
        return match.group(1)
    return f"> {line}"


def make_link(selected: str = "", url: str = "https://") -> str:
    # Generate markdown link syntax.
    label = selected or "link text"
    target = url or "https://"
    return f"[{label}]({target})"


def make_image(selected: str = "", url: str = "https://") -> str:
    # Generate markdown image syntax.
    alt = selected or "alt text"
    target = url or "https://"
    return f"![{alt}]({target})"


def horizontal_rule() -> str:
    # Return standard markdown horizontal rule.
    return "---"


def code_block(selected: str = "", language: str = "") -> str:
    # Return fenced code block snippet with optional language.
    body = selected or "code"
    lang = language.strip()
    return f"```{lang}\n{body}\n```"


def markdown_table_skeleton(rows: int = 2, cols: int = 3) -> str:
    # Generate Markdown table grid skeleton.
    header = "| " + " | ".join(f"Header {col_idx + 1}" for col_idx in range(cols)) + " |"
    separator = "| " + " | ".join("---" for _ in range(cols)) + " |"
    body_rows = ["| " + " | ".join(f"Cell {row_idx + 1}.{col_idx + 1}" for col_idx in range(cols)) + " |" for row_idx in range(rows)]
    return "\n".join([header, separator, *body_rows])


def html_table_skeleton(rows: int = 2, cols: int = 3) -> str:
    # Generate HTML table skeleton.
    head_cells = "".join(f"<th>Header {col_idx + 1}</th>" for col_idx in range(cols))
    row_list = ["<tr>" + "".join(f"<td>Cell {row_idx + 1}.{col_idx + 1}</td>" for col_idx in range(cols)) + "</tr>" for row_idx in range(rows)]
    body_cells = "".join(row_list)
    return f'<table border="1">\n  <tr>{head_cells}</tr>\n  {body_cells}\n</table>'
