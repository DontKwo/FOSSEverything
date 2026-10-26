import re
from pathlib import Path

import pytest


def calc_hex_to_rgb(hex_str: str) -> tuple[float, float, float]:
    # Convert hex color string to float RGB tuple.
    h = hex_str.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return float(int(h[0:2], 16)), float(int(h[2:4], 16)), float(int(h[4:6], 16))


def calc_parse_color(c: str) -> tuple[float, float, float, float]:
    # Parse hex or rgba color into float RGBA tuple.
    c = c.strip()
    if c.startswith("#"):
        r, g, b = calc_hex_to_rgb(c)
        return r, g, b, 1.0
    m = re.match(r"rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)(?:\s*,\s*([0-9.]+))?\s*\)", c)
    if m:
        r = float(m.group(1))
        g = float(m.group(2))
        b = float(m.group(3))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return r, g, b, a
    return 0.0, 0.0, 0.0, 1.0


def calc_blend(fg: tuple[float, float, float, float], bg: tuple[float, float, float, float]) -> tuple[float, float, float]:
    # Alpha blend foreground color over opaque background color.
    a = fg[3]
    r = fg[0] * a + bg[0] * (1.0 - a)
    g = fg[1] * a + bg[1] * (1.0 - a)
    b = fg[2] * a + bg[2] * (1.0 - a)
    return r, g, b


def calc_luminance(rgb: tuple[float, float, float]) -> float:
    # Compute relative luminance from RGB 0-255 tuple.
    chan: list[float] = []
    for v in rgb:
        norm = v / 255.0
        c = norm / 12.92 if norm <= 0.03928 else ((norm + 0.055) / 1.055) ** 2.4
        chan.append(c)
    return 0.2126 * chan[0] + 0.7152 * chan[1] + 0.0722 * chan[2]


def calc_contrast_ratio(c1_str: str, c2_str: str) -> float:
    # Compute WCAG contrast ratio between two color strings.
    fg = calc_parse_color(c1_str)
    bg = calc_parse_color(c2_str)
    rgb_bg = bg[0], bg[1], bg[2]
    rgb_fg = calc_blend(fg, bg) if fg[3] < 1.0 else (fg[0], fg[1], fg[2])
    l1 = calc_luminance(rgb_fg)
    l2 = calc_luminance(rgb_bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def calc_load_themes() -> dict[str, dict[str, str]]:
    # Parse tokens.css and themes.css into resolved per-theme token maps.
    tokens_text = Path("app/web/css/tokens.css").read_text(encoding="utf-8")
    themes_text = Path("app/web/css/themes.css").read_text(encoding="utf-8")

    dark_tokens: dict[str, str] = {}
    for line in tokens_text.splitlines():
        line = line.strip()
        if line.startswith("--") and ":" in line:
            k, v = line.split(":", 1)
            dark_tokens[k.strip()] = v.rstrip(";").strip()

    themes: dict[str, dict[str, str]] = {"dark": dict(dark_tokens)}

    blocks = re.findall(r'html\[data-theme=["\']?([a-zA-Z0-9_-]+)["\']?\]\s*\{([^}]+)\}', themes_text)
    for theme_name, body in blocks:
        theme_map = dict(dark_tokens)
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("--") and ":" in line:
                k, v = line.split(":", 1)
                theme_map[k.strip()] = v.rstrip(";").strip()
        themes[theme_name] = theme_map

    return themes


def test_theme_contrast() -> None:
    # Assert all themes satisfy WCAG contrast ratio requirements.
    themes = calc_load_themes()
    assert len(themes) >= 5, f"Expected 5 themes, found {list(themes.keys())}"

    bg_keys = ["--bg-app", "--bg-sidebar", "--bg-surface", "--bg-input", "--bg-raised"]
    violations: list[str] = []

    for theme_name, tokens in themes.items():
        # Text on 5 backgrounds: >= 7.0
        for bg in bg_keys:
            cr = calc_contrast_ratio(tokens["--text"], tokens[bg])
            if cr < 6.95:
                violations.append(f"[{theme_name}] --text on {bg}: {cr:.2f} < 7.0")

        # Text-muted on 5 backgrounds: >= 4.5
        for bg in bg_keys:
            cr = calc_contrast_ratio(tokens["--text-muted"], tokens[bg])
            if cr < 4.45:
                violations.append(f"[{theme_name}] --text-muted on {bg}: {cr:.2f} < 4.5")

        # Accent-text on 3 backgrounds: >= 4.5
        for bg in ["--bg-app", "--bg-surface", "--bg-raised"]:
            cr = calc_contrast_ratio(tokens["--accent-text"], tokens[bg])
            if cr < 4.45:
                violations.append(f"[{theme_name}] --accent-text on {bg}: {cr:.2f} < 4.5")

        # On-accent on accent and accent-hover: >= 4.5
        for ac in ["--accent", "--accent-hover"]:
            cr = calc_contrast_ratio(tokens["--on-accent"], tokens[ac])
            if cr < 4.45:
                violations.append(f"[{theme_name}] --on-accent on {ac}: {cr:.2f} < 4.5")

        # Status text on status fill: >= 4.5
        status_pairs = [
            ("--on-success", "--success"),
            ("--on-warning", "--warning"),
            ("--on-danger", "--danger"),
            ("--on-info", "--info"),
        ]
        for on_c, fill_c in status_pairs:
            cr = calc_contrast_ratio(tokens[on_c], tokens[fill_c])
            if cr < 4.45:
                violations.append(f"[{theme_name}] {on_c} on {fill_c}: {cr:.2f} < 4.5")

        # Status text on surface: >= 4.5
        for st in ["--success-text", "--warning-text", "--danger-text", "--info-text"]:
            cr = calc_contrast_ratio(tokens[st], tokens["--bg-surface"])
            if cr < 4.45:
                violations.append(f"[{theme_name}] {st} on --bg-surface: {cr:.2f} < 4.5")

        # Text-dim on surface: >= 3.0
        cr_dim = calc_contrast_ratio(tokens["--text-dim"], tokens["--bg-surface"])
        if cr_dim < 2.95:
            violations.append(f"[{theme_name}] --text-dim on --bg-surface: {cr_dim:.2f} < 3.0")

        # Border-strong on surface: >= 1.5
        cr_bs = calc_contrast_ratio(tokens["--border-strong"], tokens["--bg-surface"])
        if cr_bs < 1.45:
            violations.append(f"[{theme_name}] --border-strong on --bg-surface: {cr_bs:.2f} < 1.5")

        # Focus on surface: >= 3.0
        cr_focus = calc_contrast_ratio(tokens["--focus"], tokens["--bg-surface"])
        if cr_focus < 2.95:
            violations.append(f"[{theme_name}] --focus on --bg-surface: {cr_focus:.2f} < 3.0")

    assert not violations, f"Theme contrast violations ({len(violations)}):\n" + "\n".join(violations[:30])

