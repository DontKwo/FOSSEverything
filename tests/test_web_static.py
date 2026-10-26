import re
from pathlib import Path


def test_no_inline_styles_in_html() -> None:
    # Assert no inline style attributes exist in HTML files.
    for p in Path("app/web").rglob("*.html"):
        content = p.read_text(encoding="utf-8")
        assert 'style="' not in content and "style='" not in content, f"Inline style found in {p}"


def test_js_style_writes() -> None:
    # Assert JS files only use allowed dynamic style properties.
    js_dir = Path("app/web/js")
    if not js_dir.exists():
        return
    for p in js_dir.rglob("*.js"):
        if "vendor" in p.parts:
            continue
        code = p.read_text(encoding="utf-8")
        assert not re.search(r"\.style\.cssText", code), f"style.cssText found in {p}"
        assert not re.search(r'setAttribute\(\s*["\']style', code), f"setAttribute('style') found in {p}"

        assignments = re.findall(r"\.style\.[a-zA-Z0-9_]+\s*=", code)
        for a in assignments:
            assert ".style.transform" in a, f"Disallowed direct style assignment {a} in {p}"


def test_css_static_rules() -> None:
    # Assert CSS rules outside tokens and themes use tokens instead of raw colors or px.
    css_dir = Path("app/web/css")
    if not css_dir.exists():
        return
    for p in css_dir.rglob("*.css"):
        if p.name in ("tokens.css", "themes.css"):
            continue
        text = p.read_text(encoding="utf-8")
        text_no_url = re.sub(r"url\([^)]+\)", "", text)

        # Check raw hex colors
        hex_matches = re.findall(r"#[0-9a-fA-F]{3,8}\b", text_no_url)
        assert not hex_matches, f"Raw hex colors {hex_matches[:5]} in {p}"

        # Check rgb/rgba/hsl outside color-mix
        text_no_mix = re.sub(r"color-mix\([^)]+\)", "", text_no_url)
        color_fn_matches = re.findall(r"\b(?:rgb|rgba|hsl|hsla)\(", text_no_mix)
        assert not color_fn_matches, f"Raw color functions in {p}"

        # Check px units (only allow 1px, 0.5px, media/container px)
        clean_text = re.sub(r"@(?:media|container)[^{]+\{", "", text)
        px_matches = re.findall(r"(?<![0-9.])([0-9.]+)px\b", clean_text)
        disallowed_px = [m for m in px_matches if m not in ("1", "0.5")]
        assert not disallowed_px, f"Disallowed px units {disallowed_px[:5]} in {p}"


def test_unique_keyframes_and_single_reduced_motion() -> None:
    # Assert no duplicate keyframes and at most one prefers-reduced-motion block.
    css_dir = Path("app/web/css")
    if not css_dir.exists():
        return
    reduced_motion_count = 0
    all_keyframes: set[str] = set()

    for p in css_dir.rglob("*.css"):
        text = p.read_text(encoding="utf-8")
        reduced_motion_count += len(re.findall(r"@media\s*\(\s*prefers-reduced-motion", text))
        kfs = re.findall(r"@keyframes\s+([a-zA-Z0-9_-]+)", text)
        for k in kfs:
            assert k not in all_keyframes, f"Duplicate @keyframes name '{k}' in {p}"
            all_keyframes.add(k)

    assert reduced_motion_count <= 1, f"Found {reduced_motion_count} prefers-reduced-motion blocks"


def test_ascii_only_web_files() -> None:
    # Assert all source files in app/web except vendor are pure ASCII.
    web_dir = Path("app/web")
    if not web_dir.exists():
        return
    text_extensions = {".py", ".js", ".css", ".html", ".md", ".json", ".svg"}
    for p in web_dir.rglob("*"):
        if p.is_file() and "vendor" not in p.parts and "__pycache__" not in p.parts:
            if p.suffix.lower() in text_extensions:
                try:
                    p.read_bytes().decode("ascii")
                except UnicodeDecodeError as exc:
                    raise AssertionError(f"Non-ASCII byte in {p}: {exc}") from exc


def test_index_html_structure() -> None:
    # Assert index.html has no inline scripts and stylesheets in exact order.
    index_path = Path("app/web/index.html")
    if not index_path.exists():
        return
    text = index_path.read_text(encoding="utf-8")
    assert "<script>" not in text and "<script type=" not in text, "Inline script tag found in index.html"

    # Verify CSS links order
    expected_css = ["tokens.css", "themes.css", "base.css", "layout.css", "components.css", "tools.css"]
    links = re.findall(r'<link[^>]+href=["\']([^"\']+\.css)["\']', text)
    css_names = [Path(l).name for l in links]
    assert css_names == expected_css, f"CSS order {css_names} != expected {expected_css}"


def test_tool_data_testids() -> None:
    # Assert data-testid in tool JS files starts with tool id prefix.
    tools_dir = Path("app/web/js/tools")
    if not tools_dir.exists():
        return
    for p in tools_dir.glob("*.js"):
        tool_id = p.stem.split("_parts")[0]
        code = p.read_text(encoding="utf-8")
        testids = re.findall(r'data-testid=["\']([^"\']+)["\']', code)
        for tid in testids:
            expected_prefix = f"{tool_id}-"
            assert tid.startswith(expected_prefix), f"Testid '{tid}' in {p.name} does not start with '{expected_prefix}'"
