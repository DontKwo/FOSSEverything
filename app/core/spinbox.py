"""Spinboxes without scroll-to-change or increment/decrement arrows."""
from __future__ import annotations

from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QAbstractSpinBox, QDoubleSpinBox, QSpinBox


class NoScrollSpinBox(QSpinBox):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: 21 (Qt override, invoked by the event system)
        event.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """Double spin box that preserves exactly what the user types, not a fixed decimal count.

    Do not call setDecimals() on instances of this box: the default here (MAX_DECIMALS)
    is already as high as a double can reliably hold, so entering 1, 1.32, or
    1.2763627398 all round-trip exactly instead of being silently truncated.
    """

    MAX_DECIMALS = 10

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setDecimals(self.MAX_DECIMALS)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: 21 (Qt override, invoked by the event system)
        event.ignore()

    def textFromValue(self, value: float) -> str:  # noqa: 21 (Qt override, invoked by the event system)
        text = f"{value:.{self.decimals()}f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text or "0"

    def valueFromText(self, text: str) -> float:  # noqa: 21 (Qt override, invoked by the event system)
        try:
            return float(text)
        except ValueError:
            return super().valueFromText(text)
