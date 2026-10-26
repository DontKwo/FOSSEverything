"""Headless Markdown <-> HTML conversion and text-insertion helpers for Markdown Studio."""
from __future__ import annotations

import html
import re

_FENCE_RE = re.compile(r"^(`{3,}|~{3,})(\S*)\s*$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_HR_RE = re.compile(r"^ {0,3}(?:-\s*){3,}$|^ {0,3}(?:\*\s*){3,}$|^ {0,3}(?:_\s*){3,}$")
_BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")
_UNORDERED_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_ORDERED_RE = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")
_HTML_BLOCK_RE = re.compile(r"^\s*</?[a-zA-Z][a-zA-Z0-9-]*(\s|>|/>|$)")

_CODE_SPAN_RE = re.compile(r"(`+)(.+?)\1")
_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)')
_LINK_RE = re.compile(r'\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)')
_BOLD_ITALIC_RE = re.compile(r"(\*\*\*|___)(.+?)\1")
_BOLD_RE = re.compile(r"(\*\*|__)(.+?)\1")
_ITALIC_RE = re.compile(r"(\*|_)(.+?)\1")
_STRIKE_RE = re.compile(r"~~(.+?)~~")


def render_markdown_to_html(text: str) -> str:
    """Convert Markdown source into an HTML fragment for local preview rendering."""
    if not text.strip():
        return ""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks = _split_blocks(lines)
    return "\n".join(_render_block(block) for block in blocks if block)


def _split_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        fence_match = _FENCE_RE.match(line.strip())
        if fence_match:
            if current:
                blocks.append(current)
                current = []
            fence_lines = [line]
            fence_char = fence_match.group(1)[0]
            i += 1
            while i < len(lines):
                fence_lines.append(lines[i])
                closing = re.match(rf"^{re.escape(fence_char)}{{3,}}\s*$", lines[i].strip())
                i += 1
                if closing:
                    break
            blocks.append(fence_lines)
            continue

        if not line.strip():
            if current:
                blocks.append(current)
                current = []
            i += 1
            continue

        if _HTML_BLOCK_RE.match(line):
            if current:
                blocks.append(current)
                current = []
            html_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip():
                html_lines.append(lines[i])
                i += 1
            blocks.append(html_lines)
            continue

        if _HEADING_RE.match(line):
            if current:
                blocks.append(current)
                current = []
            blocks.append([line])
            i += 1
            continue

        if _HR_RE.match(line.strip()):
            if current:
                blocks.append(current)
                current = []
            blocks.append([line])
            i += 1
            continue

        current.append(line)
        i += 1

    if current:
        blocks.append(current)
    return blocks


def _render_block(block: list[str]) -> str:
    first = block[0]

    fence_match = _FENCE_RE.match(first.strip())
    if fence_match:
        inner = block[1:-1] if len(block) > 1 and re.match(r"^[`~]{3,}\s*$", block[-1].strip()) else block[1:]
        code = "\n".join(inner)
        return f"<pre><code>{html.escape(code)}</code></pre>"

    if _HTML_BLOCK_RE.match(first):
        return "\n".join(block)

    if len(block) == 1 and _HR_RE.match(block[0].strip()):
        return "<hr>"

    if all(_BLOCKQUOTE_RE.match(line) for line in block):
        inner = [_BLOCKQUOTE_RE.match(line).group(1) for line in block]
        return f"<blockquote>{_render_block(inner)}</blockquote>"

    if _looks_like_table(block):
        return _render_table(block)

    if all(_UNORDERED_RE.match(line) for line in block):
        items = "".join(f"<li>{_render_inline(_UNORDERED_RE.match(line).group(2))}</li>" for line in block)
        return f"<ul>{items}</ul>"

    if all(_ORDERED_RE.match(line) for line in block):
        items = "".join(f"<li>{_render_inline(_ORDERED_RE.match(line).group(2))}</li>" for line in block)
        return f"<ol>{items}</ol>"

    if len(block) == 1:
        heading_match = _HEADING_RE.match(block[0])
        if heading_match:
            level = len(heading_match.group(1))
            return f"<h{level}>{_render_inline(heading_match.group(2))}</h{level}>"

    return f"<p>{_render_paragraph(block)}</p>"


def _looks_like_table(block: list[str]) -> bool:
    return len(block) >= 2 and "|" in block[0] and bool(_TABLE_SEP_RE.match(block[1]))


def _render_table(block: list[str]) -> str:
    def split_row(row: str) -> list[str]:
        row = row.strip()
        if row.startswith("|"):
            row = row[1:]
        if row.endswith("|"):
            row = row[:-1]
        return [cell.strip() for cell in row.split("|")]

    header_cells = split_row(block[0])
    separators = split_row(block[1])
    aligns = []
    for sep in separators:
        left, right = sep.startswith(":"), sep.endswith(":")
        if left and right:
            aligns.append("center")
        elif right:
            aligns.append("right")
        elif left:
            aligns.append("left")
        else:
            aligns.append("")

    def style_for(idx: int) -> str:
        if idx < len(aligns) and aligns[idx]:
            return f' style="text-align:{aligns[idx]}"'
        return ""

    head = "".join(f"<th{style_for(i)}>{_render_inline(cell)}</th>" for i, cell in enumerate(header_cells))
    body_rows = []
    for row in block[2:]:
        cells = split_row(row)
        body_rows.append("<tr>" + "".join(f"<td{style_for(i)}>{_render_inline(cell)}</td>" for i, cell in enumerate(cells)) + "</tr>")
    return f"<table border=\"1\"><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _render_paragraph(lines: list[str]) -> str:
    rendered_lines = []
    for line in lines:
        hard_break = line.endswith("  ") or line.endswith("\\")
        rendered_lines.append((_render_inline(line.rstrip()), hard_break))
    out = ""
    for idx, (text, hard_break) in enumerate(rendered_lines):
        out += text
        if idx < len(rendered_lines) - 1:
            out += "<br>" if hard_break else " "
    return out


def _render_inline(text: str) -> str:
    escaped = html.escape(text, quote=False)

    code_spans: list[str] = []

    def _stash_code(match: re.Match) -> str:
        code_spans.append(match.group(2))
        return f"\x00CODE{len(code_spans) - 1}\x00"

    escaped = _CODE_SPAN_RE.sub(_stash_code, escaped)
    escaped = _IMAGE_RE.sub(lambda m: _render_image(m), escaped)
    escaped = _LINK_RE.sub(lambda m: _render_link(m), escaped)
    escaped = _BOLD_ITALIC_RE.sub(r"<strong><em>\2</em></strong>", escaped)
    escaped = _BOLD_RE.sub(r"<strong>\2</strong>", escaped)
    escaped = _STRIKE_RE.sub(r"<del>\1</del>", escaped)
    escaped = _ITALIC_RE.sub(r"<em>\2</em>", escaped)

    for idx, code in enumerate(code_spans):
        escaped = escaped.replace(f"\x00CODE{idx}\x00", f"<code>{code}</code>")
    return escaped


def _render_image(match: re.Match) -> str:
    alt, src, title = match.group(1), match.group(2), match.group(3)
    title_attr = f' title="{title}"' if title else ""
    return f'<img src="{src}" alt="{alt}"{title_attr}>'


def _render_link(match: re.Match) -> str:
    text, href, title = match.group(1), match.group(2), match.group(3)
    title_attr = f' title="{title}"' if title else ""
    return f'<a href="{href}"{title_attr}>{text}</a>'


# ─── Pure toolbar-insertion helpers (Qt-free, unit-testable) ─────────────────

def wrap_or_placeholder(selected: str, marker_open: str, marker_close: str, placeholder: str = "text") -> str:
    """Wrap *selected* with markdown markers, toggling them off if already applied."""
    if selected:
        if (
            selected.startswith(marker_open)
            and selected.endswith(marker_close)
            and len(selected) >= len(marker_open) + len(marker_close)
        ):
            return selected[len(marker_open): len(selected) - len(marker_close)]
        return f"{marker_open}{selected}{marker_close}"
    return f"{marker_open}{placeholder}{marker_close}"


def toggle_heading(line: str, level: int) -> str:
    """Apply/remove an ATX heading prefix of *level* (1-6) on a single line."""
    match = re.match(r"^(#{1,6})\s+(.*)$", line)
    content = match.group(2) if match else line
    if match and len(match.group(1)) == level:
        return content
    return f"{'#' * level} {content}"


def toggle_list_item(line: str, ordered: bool, number: int = 1) -> str:
    """Apply/remove a list marker on a single line, toggling off the matching kind."""
    unordered_match = _UNORDERED_RE.match(line)
    ordered_match = _ORDERED_RE.match(line)
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
    """Apply/remove a blockquote prefix on a single line."""
    match = _BLOCKQUOTE_RE.match(line)
    if match:
        return match.group(1)
    return f"> {line}"


def make_link(selected: str) -> str:
    label = selected or "link text"
    return f"[{label}](https://)"


def make_image(selected: str) -> str:
    alt = selected or "alt text"
    return f"![{alt}](https://)"


def horizontal_rule() -> str:
    return "---"


def code_block(selected: str = "") -> str:
    body = selected or "code"
    return f"```\n{body}\n```"


def markdown_table_skeleton(rows: int = 2, cols: int = 3) -> str:
    header = "| " + " | ".join(f"Header {c + 1}" for c in range(cols)) + " |"
    separator = "| " + " | ".join("---" for _ in range(cols)) + " |"
    body_rows = ["| " + " | ".join(f"Cell {r + 1}.{c + 1}" for c in range(cols)) + " |" for r in range(rows)]
    return "\n".join([header, separator, *body_rows])


def html_table_skeleton(rows: int = 2, cols: int = 3) -> str:
    head = "".join(f"<th>Header {c + 1}</th>" for c in range(cols))
    body = "".join(
        "<tr>" + "".join(f"<td>Cell {r + 1}.{c + 1}</td>" for c in range(cols)) + "</tr>"
        for r in range(rows)
    )
    return f'<table border="1">\n  <tr>{head}</tr>\n  {body}\n</table>'
