"""Settings page (and reusable widget) for registering FOSSEverything's file-type associations."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QFrame, QGroupBox, QLabel, QMessageBox, QScrollArea, QVBoxLayout, QWidget

from app.system import shell_integration
from app.ui.settings_page import SettingsPage


class FileAssociationSettings(SettingsPage):
    """Register FOSSEverything as the default app for its supported file types."""

    def setup_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        scroll.setWidget(inner)
        outer_layout.addWidget(scroll)

        intro = QLabel(
            "Windows requires your confirmation before changing a default app. Checking a box "
            "below opens the native \"Open with\" picker for that file type. Select "
            "FOSSEverything in that picker and check \"Always use this app\"."
        )
        intro.setWordWrap(True)
        intro.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(intro)

        self._family_checks: dict[str, QCheckBox] = {}
        for label, extensions in shell_integration.FILE_FAMILIES:
            ext_list = ", ".join(sorted(extensions))
            check = QCheckBox(label)
            check.setToolTip(ext_list)
            check.setChecked(all(shell_integration.is_default_for_extension(ext) for ext in extensions))
            check.toggled.connect(lambda checked, exts=extensions, chk=check: self._on_family_toggled(checked, exts, chk))
            layout.addWidget(check)
            self._family_checks[label] = check

        manual_box = QGroupBox("Manual setup (if automatic registration doesn't stick)")
        manual_layout = QVBoxLayout(manual_box)
        all_extensions = {ext for _, extensions in shell_integration.FILE_FAMILIES for ext in extensions}
        manual_label = QLabel(shell_integration.manual_association_instructions(all_extensions))
        manual_label.setWordWrap(True)
        manual_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        manual_layout.addWidget(manual_label)
        layout.addWidget(manual_box)

        layout.addStretch()

    def _on_family_toggled(self, checked: bool, extensions: frozenset[str], check: QCheckBox) -> None:
        if not checked:
            return
        _ok, message = shell_integration.set_default_for_extensions(extensions)
        QMessageBox.information(self, "Default app", message)
        check.blockSignals(True)
        check.setChecked(all(shell_integration.is_default_for_extension(ext) for ext in extensions))
        check.blockSignals(False)
