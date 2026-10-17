"""Text Tools workspace: case conversion, reversal, cleanup, line ops, and conversions."""
from __future__ import annotations

import os
from typing import Callable, Optional

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from app.core.customizable_toolbar import AppToolBar
from app.core.spinbox import NoScrollSpinBox
from app.core.tooltips import get_tooltip_for
from app.features.text_tools import ops as text_tools_ops
from app.ui.ui_scaling import scaled_font_size


class RegexReplaceDialog(QDialog):
    """Modal dialog collecting a regex pattern, replacement, and match flags."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Regex Find & Replace")
        self.resize(420, 220)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Pattern:"))
        self.pattern_edit = QLineEdit()
        self.pattern_edit.setToolTip(get_tooltip_for("Regex Pattern"))
        layout.addWidget(self.pattern_edit)

        layout.addWidget(QLabel("Replacement:"))
        self.replacement_edit = QLineEdit()
        self.replacement_edit.setToolTip(get_tooltip_for("Regex Replacement"))
        layout.addWidget(self.replacement_edit)

        flags_row = QHBoxLayout()
        self.ignore_case_check = QCheckBox("Case-insensitive")
        self.ignore_case_check.setToolTip(get_tooltip_for("Regex Case-insensitive"))
        self.multiline_check = QCheckBox("Multiline")
        self.multiline_check.setToolTip(get_tooltip_for("Regex Multiline"))
        self.dotall_check = QCheckBox("Dot matches all")
        self.dotall_check.setToolTip(get_tooltip_for("Regex Dot Matches All"))
        for widget in (self.ignore_case_check, self.multiline_check, self.dotall_check):
            flags_row.addWidget(widget)
        layout.addLayout(flags_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {
            "pattern": self.pattern_edit.text(),
            "replacement": self.replacement_edit.text(),
            "ignore_case": self.ignore_case_check.isChecked(),
            "multiline": self.multiline_check.isChecked(),
            "dotall": self.dotall_check.isChecked(),
        }


class DiffDialog(QDialog):
    """Modal dialog with two text panes for comparing left vs. right text."""

    def __init__(self, left_text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Diff Checker")
        self.resize(720, 480)

        layout = QVBoxLayout(self)
        panes = QHBoxLayout()

        left_col = QVBoxLayout()
        left_col.addWidget(QLabel("Left (original):"))
        self.left_edit = QTextEdit()
        self.left_edit.setPlainText(left_text)
        left_col.addWidget(self.left_edit)
        panes.addLayout(left_col)

        right_col = QVBoxLayout()
        right_col.addWidget(QLabel("Right (compare against):"))
        self.right_edit = QTextEdit()
        self.right_edit.setPlaceholderText("Paste the text you want to compare against the left side...")
        right_col.addWidget(self.right_edit)
        panes.addLayout(right_col)

        layout.addLayout(panes)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def texts(self) -> tuple[str, str]:
        return self.left_edit.toPlainText(), self.right_edit.toPlainText()


class TextToolsTab(QWidget):
    """Interactive workspace for general-purpose text manipulation."""

    def __init__(self, parent: Optional[QWidget] = None, settings: Optional[QSettings] = None) -> None:  # noqa: 20 (required to match DataTab.__init__ exactly per spec; same pattern already present in app/features/data/tab.py)
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings("FOSSEverything", "FOSSEverything")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Text Tools")
        title.setStyleSheet("font-weight: 700;")
        root.addWidget(title)
        root.addWidget(QLabel("Case conversion, reversal, whitespace cleanup, line operations, and text/ASCII/binary conversion."))

        toolbar = AppToolBar(self.settings, "text_tools_toolbar")
        self.toolbar = toolbar
        root.addWidget(toolbar)

        toolbar.addWidget(QLabel("Case:"))
        toolbar.add_action("UPPERCASE", lambda: self._apply(text_tools_ops.to_uppercase))
        toolbar.add_action("lowercase", lambda: self._apply(text_tools_ops.to_lowercase))
        toolbar.add_action("Title Case", lambda: self._apply(text_tools_ops.to_title_case))
        toolbar.add_action("Sentence case", lambda: self._apply(text_tools_ops.to_sentence_case))
        toolbar.add_action("camelCase", lambda: self._apply(text_tools_ops.to_camel_case))
        toolbar.add_action("snake_case", lambda: self._apply(text_tools_ops.to_snake_case))
        toolbar.add_action("kebab-case", lambda: self._apply(text_tools_ops.to_kebab_case))
        toolbar.add_action("CONSTANT_CASE", lambda: self._apply(text_tools_ops.to_constant_case))
        toolbar.addSeparator()

        toolbar.addWidget(QLabel("Reverse:"))
        toolbar.add_action("Reverse Characters", lambda: self._apply(text_tools_ops.reverse_characters))
        toolbar.add_action("Reverse Words", lambda: self._apply(text_tools_ops.reverse_words))
        toolbar.add_action("Reverse Lines", lambda: self._apply(text_tools_ops.reverse_lines))
        toolbar.addSeparator()

        toolbar.addWidget(QLabel("Cleanup:"))
        toolbar.add_action("Trim Trailing Whitespace", lambda: self._apply(text_tools_ops.trim_trailing_whitespace))
        toolbar.add_action("Trim Leading Whitespace", lambda: self._apply(text_tools_ops.trim_leading_whitespace))
        toolbar.add_action("Collapse Spaces", lambda: self._apply(text_tools_ops.collapse_spaces))
        toolbar.add_action("Remove Blank Lines", lambda: self._apply(text_tools_ops.remove_blank_lines))

        toolbar.addWidget(QLabel(" Tab Width:"))
        self.tab_width_spin = NoScrollSpinBox()
        self.tab_width_spin.setRange(1, 16)
        self.tab_width_spin.setValue(4)
        self.tab_width_spin.setToolTip(get_tooltip_for("Tab Width"))
        toolbar.addWidget(self.tab_width_spin)
        toolbar.add_action("Tabs to Spaces", self._tabs_to_spaces)
        toolbar.add_action("Spaces to Tabs", self._spaces_to_tabs)

        toolbar.addWidget(QLabel(" Line Endings:"))
        self.line_ending_combo = QComboBox()
        self.line_ending_combo.addItems(["LF", "CRLF", "CR"])
        self.line_ending_combo.setToolTip(get_tooltip_for("Line Ending Style"))
        toolbar.addWidget(self.line_ending_combo)
        toolbar.add_action("Normalize Line Endings", self._normalize_line_endings)
        toolbar.addSeparator()

        toolbar.addWidget(QLabel("Lines:"))
        toolbar.add_action("Sort A-Z", lambda: self._apply(lambda text: text_tools_ops.sort_lines(text, reverse=False)), tooltip_key="Sort Lines A-Z")
        toolbar.add_action("Sort Z-A", lambda: self._apply(lambda text: text_tools_ops.sort_lines(text, reverse=True)), tooltip_key="Sort Lines Z-A")
        toolbar.add_action("Deduplicate Lines", lambda: self._apply(text_tools_ops.dedupe_lines))
        toolbar.add_action("Number Lines", lambda: self._apply(text_tools_ops.number_lines))

        toolbar.addWidget(QLabel(" Prefix:"))
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setToolTip(get_tooltip_for("Line Prefix"))
        self.prefix_edit.setMaximumWidth(80)
        toolbar.addWidget(self.prefix_edit)
        toolbar.addWidget(QLabel("Suffix:"))
        self.suffix_edit = QLineEdit()
        self.suffix_edit.setToolTip(get_tooltip_for("Line Suffix"))
        self.suffix_edit.setMaximumWidth(80)
        toolbar.addWidget(self.suffix_edit)
        toolbar.add_action("Add Prefix/Suffix", self._add_prefix_suffix)

        toolbar.addWidget(QLabel(" Delimiter:"))
        self.delimiter_edit = QLineEdit(",")
        self.delimiter_edit.setToolTip(get_tooltip_for("Line Delimiter"))
        self.delimiter_edit.setMaximumWidth(50)
        toolbar.addWidget(self.delimiter_edit)
        toolbar.add_action("Join Lines", self._join_lines)
        toolbar.add_action("Split Text", self._split_text)
        toolbar.addSeparator()

        toolbar.addWidget(QLabel("Convert:"))
        toolbar.add_action("Text to Code Points", lambda: self._apply(text_tools_ops.text_to_code_points))
        toolbar.add_action("Code Points to Text", lambda: self._apply(text_tools_ops.code_points_to_text))
        toolbar.add_action("Text to Binary", lambda: self._apply(text_tools_ops.text_to_binary))
        toolbar.add_action("Binary to Text", lambda: self._apply(text_tools_ops.binary_to_text))
        toolbar.addSeparator()

        toolbar.add_action("Regex Find & Replace", self._regex_find_replace)
        toolbar.add_action("Diff Checker", self._diff_checker)
        toolbar.addSeparator()

        toolbar.add_action("Copy", self._copy_to_clipboard)
        toolbar.add_action("Clear", self._clear_text)

        toolbar.finalize()

        self.editor = QTextEdit()
        font = QFont("Courier New" if os.name == "nt" else "Monospace", scaled_font_size(11))
        self.editor.setFont(font)
        self.editor.setPlaceholderText("Type or paste text here to case-convert, reverse, clean up, sort, or convert it...")
        root.addWidget(self.editor, stretch=1)

        self.status_bar = QLabel("Ready")
        root.addWidget(self.status_bar)

    def _apply(self, func: Callable[[str], str]) -> None:
        text = self.editor.toPlainText()
        try:
            result = func(text)
        except Exception as exc:
            QMessageBox.critical(self, "Text Tools Error", str(exc))
            return
        self.editor.setPlainText(result)
        self.status_bar.setText("[OK] Operation applied")

    def _tabs_to_spaces(self) -> None:
        width = self.tab_width_spin.value()
        self._apply(lambda text: text_tools_ops.tabs_to_spaces(text, width=width))

    def _spaces_to_tabs(self) -> None:
        width = self.tab_width_spin.value()
        self._apply(lambda text: text_tools_ops.spaces_to_tabs(text, width=width))

    def _normalize_line_endings(self) -> None:
        style = self.line_ending_combo.currentText().lower()
        self._apply(lambda text: text_tools_ops.normalize_line_endings(text, style=style))

    def _add_prefix_suffix(self) -> None:
        prefix = self.prefix_edit.text()
        suffix = self.suffix_edit.text()
        self._apply(lambda text: text_tools_ops.add_prefix_suffix(text, prefix=prefix, suffix=suffix))

    def _join_lines(self) -> None:
        delimiter = self.delimiter_edit.text()
        self._apply(lambda text: text_tools_ops.join_lines(text, delimiter=delimiter))

    def _split_text(self) -> None:
        delimiter = self.delimiter_edit.text()
        self._apply(lambda text: text_tools_ops.split_text(text, delimiter=delimiter))

    def _regex_find_replace(self) -> None:
        dialog = RegexReplaceDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        self._apply(lambda text: text_tools_ops.regex_replace(
            text,
            values["pattern"],
            values["replacement"],
            ignore_case=values["ignore_case"],
            multiline=values["multiline"],
            dotall=values["dotall"],
        ))

    def _diff_checker(self) -> None:
        dialog = DiffDialog(self.editor.toPlainText(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        left_text, right_text = dialog.texts()
        result = text_tools_ops.diff_texts(left_text, right_text)
        self.editor.setPlainText(result["diff"] if result["diff"] else "No differences found.")
        self.status_bar.setText(f"[OK] Diff complete: {result['added']} added, {result['removed']} removed")

    def _copy_to_clipboard(self) -> None:
        QGuiApplication.clipboard().setText(self.editor.toPlainText())
        self.status_bar.setText("[OK] Copied to clipboard")

    def _clear_text(self) -> None:
        if self.editor.toPlainText().strip():
            confirm = QMessageBox.question(
                self, "Clear Text", "Discard the current text? This can't be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
        self.editor.clear()
        self.status_bar.setText("Ready")
