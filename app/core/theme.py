"""Single source of truth for theme colors, font scale, and live-update notification."""
from __future__ import annotations

import json
import math
import re

from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtGui import QColor

DEFAULT_ACCENT_DARK = "#5aa8ff"
DEFAULT_ACCENT_LIGHT = "#4a8df6"
DEFAULT_BUTTON_RADIUS = 8

_LIGHT_PALETTE = {
    "background": "#f5f7fb",
    "panel": "#ffffff",
    "text": "#1f2937",
    "muted": "#5c6f86",
    "border": "#dfe6f0",
    "button": "#ffffff",
    "input": "#f9fbff",
    "menu": "#ffffff",
    "toolbar": "#f2f6fb",
    "tab": "#edf3fa",
    "accent": DEFAULT_ACCENT_LIGHT,
    "on_accent": "#ffffff",
    "selection_text": "#ffffff",
    "success": "#1f9d61",
    "warning": "#c77d23",
    "danger": "#d9485f",
}

_DARK_PALETTE = {
    "background": "#0f1724",
    "panel": "#1b2430",
    "text": "#ffffff",
    "muted": "#b6c0cf",
    "border": "#3a475b",
    "button": "#283548",
    "input": "#121c2a",
    "menu": "#182230",
    "toolbar": "#131d2b",
    "tab": "#1d2a39",
    "accent": DEFAULT_ACCENT_DARK,
    "on_accent": "#ffffff",
    "selection_text": "#ffffff",
    "success": "#6cd29d",
    "warning": "#f0b75d",
    "danger": "#ff6b7b",
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
}


class _ThemeSignals(QObject):
    """Emitted whenever theme colors, accent, palette, or font scale change."""

    changed = pyqtSignal()


theme_signals = _ThemeSignals()


def notify_theme_changed() -> None:
    theme_signals.changed.emit()


def _settings(settings: QSettings | None) -> QSettings:
    return settings if settings is not None else QSettings("FOSSEverything", "FOSSEverything")


def default_palette(theme_name: str) -> dict[str, str]:
    return dict(_THEME_PRESETS.get(theme_name, _DARK_PALETTE))


def current_theme_name(settings: QSettings | None = None) -> str:
    theme_name = str(_settings(settings).value("app/theme", "dark"))
    return theme_name if theme_name in _THEME_PRESETS else "dark"


def load_ui_palette(settings: QSettings | None = None) -> dict[str, str]:
    raw = _settings(settings).value("app/ui_palette", "")
    if not raw:
        return {}
    try:
        palette = json.loads(str(raw))
    except (TypeError, ValueError):
        return {}
    if not isinstance(palette, dict):
        return {}
    return {key: value for key, value in palette.items() if isinstance(value, str) and bool(value.strip())}


def resolved_palette(settings: QSettings | None = None) -> dict[str, str]:
    settings = _settings(settings)
    palette = default_palette(current_theme_name(settings))
    palette.update(load_ui_palette(settings))
    accent = str(settings.value("app/accent_color", "")).strip()
    if accent:
        palette["accent"] = accent
    return palette


def parse_color_value(value: object, fallback: str) -> QColor:
    if value is None:
        return QColor(fallback)
    text = str(value).strip()
    if not text:
        return QColor(fallback)

    rgb_match = re.search(r"rgba?\(([^)]+)\)", text, flags=re.IGNORECASE)
    if rgb_match:
        parts = [part.strip() for part in rgb_match.group(1).split(',')]
        if len(parts) >= 3 and all(part.lstrip('-').isdigit() for part in parts[:3]):
            color = QColor(int(parts[0]), int(parts[1]), int(parts[2]))
            if color.isValid():
                return color

    color = QColor(text)
    if color.isValid():
        return color
    return QColor(fallback)


def rgba(color_value: str, alpha: float) -> str:
    color = QColor(color_value)
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"


def profile_key(slot: int) -> str:
    return f"app/ui_palette_profile_{slot}"


def get_font_scale(settings: QSettings | None = None) -> float:
    try:
        scale = float(_settings(settings).value("app/font_scale", 1.0))
    except (TypeError, ValueError):
        scale = 1.0
    if not math.isfinite(scale) or scale <= 0:
        return 1.0
    return scale
