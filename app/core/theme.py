"""Single source of truth for theme colors and palettes without PyQt dependencies."""
from __future__ import annotations

import json
import math
import re
from typing import Any, Callable

from app.system.settings import get_setting

DEFAULT_ACCENT_DARK = "#5aa8ff"
DEFAULT_ACCENT_LIGHT = "#4a8df6"
DEFAULT_BUTTON_RADIUS = 8

_LIGHT_PALETTE = {
    "background": "#f8fafc",
    "panel": "#ffffff",
    "text": "#0f172a",
    "muted": "#64748b",
    "border": "#e2e8f0",
    "button": "#f1f5f9",
    "input": "#ffffff",
    "menu": "#ffffff",
    "toolbar": "#ffffff",
    "tab": "#f1f5f9",
    "accent": DEFAULT_ACCENT_LIGHT,
    "on_accent": "#ffffff",
    "selection_text": "#ffffff",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
}

_DARK_PALETTE = {
    "background": "#0b0f19",
    "panel": "#111827",
    "text": "#f9fafb",
    "muted": "#9ca3af",
    "border": "#1f2937",
    "button": "#1f2937",
    "input": "#0f172a",
    "menu": "#111827",
    "toolbar": "#0f172a",
    "tab": "#1f2937",
    "accent": DEFAULT_ACCENT_DARK,
    "on_accent": "#ffffff",
    "selection_text": "#ffffff",
    "success": "#34d399",
    "warning": "#fbbf24",
    "danger": "#f87171",
}

_HIGH_CONTRAST_PALETTE = {
    "background": "#000000",
    "panel": "#111111",
    "text": "#ffffff",
    "muted": "#d8d8d8",
    "border": "#ffffff",
    "button": "#1a1a1a",
    "input": "#0a0a0a",
    "menu": "#000000",
    "toolbar": "#000000",
    "tab": "#141414",
    "accent": "#ffd60a",
    "on_accent": "#000000",
    "selection_text": "#000000",
    "success": "#00e676",
    "warning": "#ffd60a",
    "danger": "#ff5252",
}

_SOLARIZED_PALETTE = {
    "background": "#002b36",
    "panel": "#073642",
    "text": "#eee8d5",
    "muted": "#93a1a1",
    "border": "#586e75",
    "button": "#073642",
    "input": "#00212b",
    "menu": "#073642",
    "toolbar": "#073642",
    "tab": "#0a4552",
    "accent": "#2aa198",
    "on_accent": "#002b36",
    "selection_text": "#002b36",
    "success": "#859900",
    "warning": "#b58900",
    "danger": "#dc322f",
}

_SEPIA_PALETTE = {
    "background": "#f4ecd8",
    "panel": "#fbf5e6",
    "text": "#4b3621",
    "muted": "#7a6752",
    "border": "#d8c8a5",
    "button": "#fbf5e6",
    "input": "#fffaf0",
    "menu": "#f4ecd8",
    "toolbar": "#efe3c8",
    "tab": "#ead9b8",
    "accent": "#a9682b",
    "on_accent": "#ffffff",
    "selection_text": "#ffffff",
    "success": "#4c7a3d",
    "warning": "#b0762a",
    "danger": "#a3372b",
}

_UT_AUSTIN_PALETTE = {
    "background": "#ffffff",
    "panel": "#f7f5f1",
    "text": "#333f48",
    "muted": "#6b7280",
    "border": "#e2ddd3",
    "button": "#ffffff",
    "input": "#faf9f6",
    "menu": "#ffffff",
    "toolbar": "#f7f5f1",
    "tab": "#efece4",
    "accent": "#bf5700",
    "on_accent": "#ffffff",
    "selection_text": "#ffffff",
    "success": "#4b7729",
    "warning": "#a15c00",
    "danger": "#b3261e",
}

THEME_PRESET_ORDER = ("dark", "light", "high_contrast", "solarized", "sepia", "ut_austin")

THEME_PRESET_LABELS = {
    "dark": "Dark",
    "light": "Light",
    "high_contrast": "High Contrast",
    "solarized": "Solarized",
    "sepia": "Sepia",
    "ut_austin": "UT Austin",
}

_THEME_PRESETS = {
    "dark": _DARK_PALETTE,
    "light": _LIGHT_PALETTE,
    "high_contrast": _HIGH_CONTRAST_PALETTE,
    "solarized": _SOLARIZED_PALETTE,
    "sepia": _SEPIA_PALETTE,
    "ut_austin": _UT_AUSTIN_PALETTE,
    "ut": _UT_AUSTIN_PALETTE,
}

_theme_listeners: list[Callable[[], None]] = []


def add_theme_listener(cb: Callable[[], None]) -> None:
    _theme_listeners.append(cb)


def notify_theme_changed() -> None:
    for cb in _theme_listeners:
        try:
            cb()
        except Exception:  # noqa: 10
            pass


def default_palette(theme_name: str) -> dict[str, str]:
    return dict(_THEME_PRESETS.get(theme_name, _DARK_PALETTE))


def current_theme_name(settings: Any = None) -> str:
    theme_name = str(get_setting("app/theme", "dark"))
    return theme_name if theme_name in _THEME_PRESETS else "dark"


def load_ui_palette(settings: Any = None) -> dict[str, str]:
    raw = get_setting("app/ui_palette", "")
    if not raw:
        return {}
    try:
        palette = json.loads(str(raw))
    except (TypeError, ValueError):
        return {}
    if not isinstance(palette, dict):
        return {}
    return {key: value for key, value in palette.items() if isinstance(value, str) and bool(value.strip())}


def resolved_palette(settings: Any = None) -> dict[str, str]:
    palette = default_palette(current_theme_name(settings))
    palette.update(load_ui_palette(settings))
    accent = str(get_setting("app/accent_color", "")).strip()
    if accent:
        palette["accent"] = accent
    return palette


def get_font_scale(settings: Any = None) -> float:
    try:
        scale = float(get_setting("app/font_scale", 1.0))
    except (TypeError, ValueError):
        scale = 1.0
    if not math.isfinite(scale) or scale <= 0:
        return 1.0
    return scale


def parse_color_value(value: object, fallback: str) -> str:
    # Parse color text or return fallback.
    text = str(value or "").strip()
    return text if text else fallback


def rgba(color_value: str, alpha: float) -> str:
    # Format color string with opacity.
    hex_digits = color_value.strip().lstrip("#")
    if len(hex_digits) == 6:
        r_val = int(hex_digits[0:2], 16)
        g_val = int(hex_digits[2:4], 16)
        b_val = int(hex_digits[4:6], 16)
        return f"rgba({r_val}, {g_val}, {b_val}, {alpha})"
    return f"rgba(0, 0, 0, {alpha})"


def profile_key(slot: int) -> str:
    # Return settings key for palette slot.
    return f"app/ui_palette_profile_{slot}"
