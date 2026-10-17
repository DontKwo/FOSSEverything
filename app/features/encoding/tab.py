"""Encoding/Decoding workspace: Base64, URL/percent-encoding, HTML entities, hex, and binary."""
from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QTextEdit,
    QLabel, QFileDialog, QMessageBox, QCheckBox
)

from app.core.customizable_toolbar import AppToolBar
from app.features.encoding import ops as encoding_ops
from app.core.tooltips import get_tooltip_for
from app.ui.ui_scaling import scaled_font_size

_TEXT_SCHEMES = ("Base64", "URL", "HTML", "Hex")
_FILE_SCHEMES = ("Base64", "Hex", "Binary")
_OPTION_LABELS = {
    "Base64": "URL-safe alphabet",
    "URL": "Preserve reserved characters (full URL)",
    "HTML": "Numeric character references",
    "Hex": "Space-separated bytes",
    "Binary": "Space-separated bytes",
}


class EncodingTab(QWidget):
    """Interactive workspace for encoding and decoding text and files."""

    def __init__(self, parent: Optional[QWidget] = None, settings: Optional[QSettings] = None) -> None:  # noqa: 20 (required to match DataTab.__init__ exactly per spec; same pattern already present in app/features/data/tab.py)
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings("FOSSEverything", "FOSSEverything")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Encoding / Decoding")
        title.setStyleSheet("font-weight: 700;")
        root.addWidget(title)
        root.addWidget(QLabel("Encode and decode text and files between Base64, URL/percent-encoding, HTML entities, hex, and binary."))

        toolbar = AppToolBar(self.settings, "encoding_toolbar")
        self.toolbar = toolbar
        root.addWidget(toolbar)

        toolbar.addWidget(QLabel("Scheme:"))
        self.scheme_combo = QComboBox()
        self.scheme_combo.addItems(["Base64", "URL", "HTML", "Hex", "Binary"])
        self.scheme_combo.setToolTip(get_tooltip_for("Encoding Scheme"))
        self.scheme_combo.currentTextChanged.connect(self._on_scheme_changed)
        toolbar.addWidget(self.scheme_combo)

        self.option_check = QCheckBox()
        self.option_check.setToolTip(get_tooltip_for("Encoding Option"))
        toolbar.addWidget(self.option_check)
        toolbar.addSeparator()

        self.encode_action = toolbar.add_action("Encode", self._encode_text, tooltip_key="Encode")
        self.decode_action = toolbar.add_action("Decode", self._decode_text, tooltip_key="Decode")
        toolbar.addSeparator()

        toolbar.add_action("Encode File...", self._encode_file, tooltip_key="Encode File")
        toolbar.add_action("Decode to File...", self._decode_to_file, tooltip_key="Decode to File")
        toolbar.addSeparator()
        toolbar.add_action("Copy", self._copy_to_clipboard, tooltip_key="Copy")
        toolbar.finalize()

        self.editor = QTextEdit()
        font = QFont("Courier New" if os.name == "nt" else "Monospace", scaled_font_size(11))
        self.editor.setFont(font)
        self.editor.setPlaceholderText("Type or paste text/encoded data here...")
        root.addWidget(self.editor, stretch=1)

        self.status_bar = QLabel("Ready")
        root.addWidget(self.status_bar)

        self._on_scheme_changed(self.scheme_combo.currentText())

    def _on_scheme_changed(self, scheme: str) -> None:
        self.option_check.setText(_OPTION_LABELS.get(scheme, ""))
        supports_text = scheme in _TEXT_SCHEMES
        self.encode_action.setEnabled(supports_text)
        self.decode_action.setEnabled(supports_text)
        if not supports_text:
            self.status_bar.setText("Binary is byte-level only: use \"Encode File...\" / \"Decode to File...\".")
        else:
            self.status_bar.setText("Ready")

    def _encode_text(self) -> None:
        text = self.editor.toPlainText()
        scheme = self.scheme_combo.currentText()
        option = self.option_check.isChecked()
        try:
            if scheme == "Base64":
                result = encoding_ops.base64_encode_text(text, url_safe=option)
            elif scheme == "URL":
                result = encoding_ops.url_encode(text, full_url=option)
            elif scheme == "HTML":
                result = encoding_ops.html_encode_numeric(text) if option else encoding_ops.html_encode(text)
            elif scheme == "Hex":
                result = encoding_ops.hex_encode_text(text, spaced=option)
            else:
                return
            self.editor.setPlainText(result)
            self.status_bar.setText(f"[OK] Encoded with {scheme}")
        except Exception as exc:
            QMessageBox.critical(self, "Encoding Error", str(exc))

    def _decode_text(self) -> None:
        text = self.editor.toPlainText()
        scheme = self.scheme_combo.currentText()
        option = self.option_check.isChecked()
        try:
            if scheme == "Base64":
                result = encoding_ops.base64_decode_text(text, url_safe=option)
            elif scheme == "URL":
                result = encoding_ops.url_decode(text)
            elif scheme == "HTML":
                result = encoding_ops.html_decode(text)
            elif scheme == "Hex":
                result = encoding_ops.hex_decode_text(text)
            else:
                return
            self.editor.setPlainText(result)
            self.status_bar.setText(f"[OK] Decoded with {scheme}")
        except Exception as exc:
            QMessageBox.critical(self, "Decoding Error", str(exc))

    def _encode_file(self) -> None:
        scheme = self.scheme_combo.currentText()
        if scheme not in _FILE_SCHEMES:
            QMessageBox.information(self, "Not Supported", f"{scheme} does not support file encoding.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Select File to Encode", "", "All Files (*.*)")
        if not path:
            return
        option = self.option_check.isChecked()
        try:
            if scheme == "Base64":
                result = encoding_ops.base64_encode_file(path, url_safe=option)
            elif scheme == "Hex":
                result = encoding_ops.hex_encode_file(path, spaced=option)
            else:
                result = encoding_ops.binary_encode_file(path, spaced=option)
            self.editor.setPlainText(result)
            self.status_bar.setText(f"[OK] Encoded {os.path.basename(path)} with {scheme}")
        except Exception as exc:
            QMessageBox.critical(self, "Encode File Error", str(exc))

    def _decode_to_file(self) -> None:
        scheme = self.scheme_combo.currentText()
        if scheme not in _FILE_SCHEMES:
            QMessageBox.information(self, "Not Supported", f"{scheme} does not support file decoding.")
            return
        text = self.editor.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "No Data", "Nothing in the editor to decode.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Decoded File", "decoded.bin", "All Files (*.*)")
        if not path:
            return
        option = self.option_check.isChecked()
        try:
            if scheme == "Base64":
                encoding_ops.base64_decode_to_file(text, path, url_safe=option)
            elif scheme == "Hex":
                encoding_ops.hex_decode_to_file(text, path)
            else:
                encoding_ops.binary_decode_to_file(text, path)
            self.status_bar.setText(f"[OK] Decoded to {path}")
            QMessageBox.information(self, "Saved", f"Decoded bytes written to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Decode File Error", str(exc))

    def _copy_to_clipboard(self) -> None:
        content = self.editor.toPlainText()
        if not content:
            return
        QGuiApplication.clipboard().setText(content)
        self.status_bar.setText("[OK] Copied encoded/decoded output to clipboard")
