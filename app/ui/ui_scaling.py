from __future__ import annotations

from app.core.theme import get_font_scale

__all__ = ["get_font_scale", "scaled_font_pt", "scaled_font_size"]


def scaled_font_pt(base_pt: float) -> str:
    return f"{max(7.0, base_pt * get_font_scale()):.2f}pt"


def scaled_font_size(base_px: float) -> int:
    return max(7, int(round(base_px * get_font_scale())))
