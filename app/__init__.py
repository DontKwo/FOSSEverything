from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox


def _selectable_box(box: QMessageBox) -> QMessageBox:
    box.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
        | Qt.TextInteractionFlag.TextSelectableByKeyboard
    )
    return box


def _box_factory(icon: QMessageBox.Icon, default_buttons: QMessageBox.StandardButton) -> Callable[..., int]:
    def _factory(
        parent: QMessageBox | None = None,
        title: str = "",
        text: str = "",
        buttons: QMessageBox.StandardButton = default_buttons,
        default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
        **kwargs: Any,
    ) -> int:
        box = QMessageBox(icon, title, text, buttons, parent=parent)
        _selectable_box(box)
        if default_button != QMessageBox.StandardButton.NoButton:
            box.setDefaultButton(default_button)
        if "informative_text" in kwargs:
            box.setInformativeText(kwargs["informative_text"])
        if "detailed_text" in kwargs:
            box.setDetailedText(kwargs["detailed_text"])
        return box.exec()
    return _factory


_original_qmsgbox_init = QMessageBox.__init__

def _patched_qmsgbox_init(self: QMessageBox, *args: Any, **kwargs: Any) -> None:
    _original_qmsgbox_init(self, *args, **kwargs)
    self.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
        | Qt.TextInteractionFlag.TextSelectableByKeyboard
    )


QMessageBox.__init__ = _patched_qmsgbox_init
QMessageBox.warning = staticmethod(_box_factory(QMessageBox.Icon.Warning, QMessageBox.StandardButton.Ok))
QMessageBox.critical = staticmethod(_box_factory(QMessageBox.Icon.Critical, QMessageBox.StandardButton.Ok))
QMessageBox.information = staticmethod(_box_factory(QMessageBox.Icon.Information, QMessageBox.StandardButton.Ok))
QMessageBox.question = staticmethod(_box_factory(
    QMessageBox.Icon.Question, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
))
