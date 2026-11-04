from pathlib import Path


def test_web_static_completeness() -> None:
    # Assert all required files exist and are valid UTF-8.
    expected_tools = [
        "archive.js", "collage.js", "compressor.js", "converter.js",
        "data.js", "encoding.js", "images.js", "markdown.js",
        "media.js", "metadata.js", "model3d.js", "network_monitor.js",
        "ocr.js", "palette.js", "pdf.js", "playlist.js",
        "qr.js", "renamer.js", "resume.js", "text_tools.js",
        "unit_converter.js"
    ]
    expected_css = [
        "tokens.css", "themes.css", "base.css",
        "layout.css", "components.css", "tools.css"
    ]

    web_dir = Path("app/web")

    for tool in expected_tools:
        p = web_dir / "js" / "tools" / tool
        assert p.exists(), f"Tool JS missing: {p}"
        p.read_text(encoding="utf-8")

    for css in expected_css:
        p = web_dir / "css" / css
        assert p.exists(), f"CSS missing: {p}"
        p.read_text(encoding="utf-8")

    icons_p = web_dir / "js" / "core" / "icons.js"
    assert icons_p.exists(), f"Icons missing: {icons_p}"
    icons_p.read_text(encoding="utf-8")
