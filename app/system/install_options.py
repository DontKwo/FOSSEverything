"""Applies first-run preferences chosen in the Windows or Linux installer."""
from __future__ import annotations

import math

from app.system.settings import set_setting

INSTALL_THEMES: tuple[str, ...] = (
    "ut_austin_dark", "dark", "light", "solarized", "monokai", "cyberpunk", "ut_austin",
)
INSTALL_SIDEBAR_MODES: tuple[str, ...] = ("expanded", "collapsed")
INSTALL_STARTUP_VIEWS: tuple[str, ...] = (
    "home", "pdf", "images", "media", "converter", "data", "model3d", "network_monitor",
)
MIN_UI_SCALE: float = 0.50
MAX_UI_SCALE: float = 2.50

_FLAG_TO_KEY: tuple[tuple[str, str], ...] = (
    ("--theme=", "theme"),
    ("--ui-scale=", "ui_scale"),
    ("--sidebar=", "sidebar"),
    ("--startup-view=", "startup_view"),
)


def parse_install_options(argv: list[str]) -> dict[str, str]:
    # Collect supported --<flag>=<value> arguments from argv.
    options: dict[str, str] = {}
    for arg in argv:
        for prefix, key in _FLAG_TO_KEY:
            if arg.startswith(prefix):
                options[key] = arg.split("=", 1)[1].strip()
                break
    return options


def apply_install_options(argv: list[str]) -> tuple[bool, str]:
    # Validate all supplied installer options before writing any setting.
    options = parse_install_options(argv)
    if not options:
        return False, (
            "No install options supplied. Use --theme=<id>, --ui-scale=<0.5-2.5>, "
            "--sidebar=<expanded|collapsed>, and/or --startup-view=<id>."
        )

    theme = options.get("theme")
    if theme is not None and theme not in INSTALL_THEMES:
        return False, f"Unknown theme '{theme}'. Valid themes: {', '.join(INSTALL_THEMES)}."

    scale_value: float | None = None
    if "ui_scale" in options:
        try:
            scale_value = float(options["ui_scale"])
        except ValueError:
            return False, f"UI scale '{options['ui_scale']}' is not a number."
        if not math.isfinite(scale_value):
            return False, "UI scale must be a finite number."
        scale_value = round(max(MIN_UI_SCALE, min(MAX_UI_SCALE, scale_value)), 2)

    sidebar = options.get("sidebar")
    if sidebar is not None and sidebar not in INSTALL_SIDEBAR_MODES:
        return False, f"Unknown sidebar mode '{sidebar}'. Valid modes: {', '.join(INSTALL_SIDEBAR_MODES)}."

    startup_view = options.get("startup_view")
    if startup_view is not None and startup_view not in INSTALL_STARTUP_VIEWS:
        return False, f"Unknown startup view '{startup_view}'. Valid views: {', '.join(INSTALL_STARTUP_VIEWS)}."

    if theme is not None:
        set_setting("theme", theme)
    if scale_value is not None:
        set_setting("ui_scale", scale_value)
    if sidebar is not None:
        set_setting("sidebar_collapsed", sidebar == "collapsed")
    if startup_view is not None:
        set_setting("startup_view", startup_view)
    return True, "Preferences applied."
