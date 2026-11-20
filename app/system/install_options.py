"""Applies first-run preferences chosen in the Windows installer wizard."""
from __future__ import annotations

import math

from app.system.settings import set_setting

INSTALL_THEMES: tuple[str, ...] = (
    "ut_austin_dark", "dark", "light", "solarized", "monokai", "cyberpunk", "ut_austin",
)
MIN_UI_SCALE: float = 0.50
MAX_UI_SCALE: float = 2.50


def parse_install_options(argv: list[str]) -> dict[str, str]:
    # Collect --theme=<id> and --ui-scale=<float> arguments.
    options: dict[str, str] = {}
    for arg in argv:
        if arg.startswith("--theme="):
            options["theme"] = arg.split("=", 1)[1].strip()
        elif arg.startswith("--ui-scale="):
            options["ui_scale"] = arg.split("=", 1)[1].strip()
    return options


def apply_install_options(argv: list[str]) -> tuple[bool, str]:
    # Validate then persist installer-chosen theme and UI scale; writes nothing on any invalid value.
    options = parse_install_options(argv)
    if not options:
        return False, "No install options supplied. Use --theme=<id> and/or --ui-scale=<0.5-2.5>."

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

    if theme is not None:
        set_setting("theme", theme)
    if scale_value is not None:
        set_setting("ui_scale", scale_value)
    return True, "Preferences applied."
