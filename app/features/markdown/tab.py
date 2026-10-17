"""Markdown Studio workspace: side-by-side live Markdown editor and HTML preview."""
from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QSplitter, QPlainTextEdit, QTextBrowser,
    QLabel, QFileDialog, QMessageBox,
)

from app.core.customizable_toolbar import AppToolBar
from app.features.markdown import ops as markdown_ops
from app.ui.ui_scaling import scaled_font_size


class MarkdownTab(QWidget):
    """Live side-by-side Markdown editor with an HTML preview and insertion toolbar."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_path: Optional[str] = None
        self._build_ui()
        self._update_preview()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title_label = QLabel("Markdown Studio")
        title_label.setStyleSheet("font-weight: 700;")
        root.addWidget(title_label)

        file_bar = AppToolBar(None, "markdown_file_toolbar")
        file_bar.add_action("Open File...", self._browse_file, tooltip_key="Open File")
        file_bar.add_action("Save", self._save_file, tooltip_key="Save")
        file_bar.add_action("Save As...", self._save_file_as, tooltip_key="Save As")
        file_bar.add_action("Export HTML...", self._export_html, tooltip_key="Export HTML")
        file_bar.add_action("Clear", self._clear_text, tooltip_key="Clear All")
        file_bar.finalize()
        root.addWidget(file_bar)

        format_bar = AppToolBar(None, "markdown_format_toolbar")
        format_bar.add_action("Bold", lambda: self._apply_wrap("**"), shortcut="Ctrl+B", tooltip_key="Bold")
        format_bar.add_action("Italic", lambda: self._apply_wrap("*"), shortcut="Ctrl+I", tooltip_key="Italic")
        format_bar.add_action("Strikethrough", lambda: self._apply_wrap("~~"), tooltip_key="Strikethrough")
        format_bar.addSeparator()
        format_bar.add_action("H1", lambda: self._apply_heading(1), tooltip_key="Heading 1")
        format_bar.add_action("H2", lambda: self._apply_heading(2), tooltip_key="Heading 2")
        format_bar.add_action("H3", lambda: self._apply_heading(3), tooltip_key="Heading 3")
        format_bar.addSeparator()
        format_bar.add_action("Inline Code", lambda: self._apply_wrap("`"), tooltip_key="Inline Code")
        format_bar.add_action("Code Block", self._insert_code_block, tooltip_key="Code Block")
        format_bar.addSeparator()
        format_bar.add_action("Link", self._insert_link, tooltip_key="Link")
        format_bar.add_action("Image", self._insert_image, tooltip_key="Image")
        format_bar.addSeparator()
        format_bar.add_action("Bulleted List", lambda: self._apply_list(ordered=False), tooltip_key="Bulleted List")
        format_bar.add_action("Numbered List", lambda: self._apply_list(ordered=True), tooltip_key="Numbered List")
        format_bar.add_action("Blockquote", self._apply_blockquote, tooltip_key="Blockquote")
        format_bar.add_action("Horizontal Rule", self._insert_horizontal_rule, tooltip_key="Horizontal Rule")
        format_bar.addSeparator()
        format_bar.add_action("Markdown Table", self._insert_markdown_table, tooltip_key="Markdown Table")
        format_bar.add_action("HTML Table", self._insert_html_table, tooltip_key="HTML Table")
        format_bar.finalize()
        root.addWidget(format_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        editor_box = QGroupBox("Markdown Source")
        editor_layout = QVBoxLayout(editor_box)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Type or paste Markdown here...")
        self.editor.setFont(QFont("Consolas", scaled_font_size(10)))
        self.editor.textChanged.connect(self._update_preview)
        editor_layout.addWidget(self.editor)
        splitter.addWidget(editor_box)

        preview_box = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_box)
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)
        preview_layout.addWidget(self.preview)
        splitter.addWidget(preview_box)

        splitter.setSizes([600, 600])
        root.addWidget(splitter, stretch=1)

    # ─── Insertion toolbar actions ────────────────────────────────────────────

    def _selected_text(self, cursor: QTextCursor) -> str:
        return cursor.selectedText().replace(" ", "\n")

    def _apply_wrap(self, marker: str) -> None:
        cursor = self.editor.textCursor()
        selected = self._selected_text(cursor)
        start = cursor.selectionStart()
        new_text = markdown_ops.wrap_or_placeholder(selected, marker, marker)
        cursor.insertText(new_text)
        if not selected:
            placeholder_len = len(new_text) - 2 * len(marker)
            sel_start = start + len(marker)
            cursor.setPosition(sel_start)
            cursor.setPosition(sel_start + placeholder_len, QTextCursor.MoveMode.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _apply_line_transform(self, transform: Callable[[str, int], str]) -> None:
        cursor = self.editor.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        block_start = cursor.position()
        cursor.setPosition(end)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        block_end = cursor.position()
        cursor.setPosition(block_start)
        cursor.setPosition(block_end, QTextCursor.MoveMode.KeepAnchor)
        text = self._selected_text(cursor)
        lines = text.split("\n")
        new_lines = [transform(line, index) for index, line in enumerate(lines)]
        cursor.insertText("\n".join(new_lines))
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _apply_heading(self, level: int) -> None:
        self._apply_line_transform(lambda line, _index: markdown_ops.toggle_heading(line, level))

    def _apply_list(self, ordered: bool) -> None:
        self._apply_line_transform(lambda line, index: markdown_ops.toggle_list_item(line, ordered, index + 1))

    def _apply_blockquote(self) -> None:
        self._apply_line_transform(lambda line, _index: markdown_ops.toggle_blockquote(line))

    def _insert_block(self, text: str) -> None:
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()
        doc_text = self.editor.toPlainText()
        pos = cursor.position()
        needs_prefix_nl = pos > 0 and doc_text[pos - 1:pos] != "\n"
        cursor.insertText(("\n\n" if needs_prefix_nl else "") + text + "\n\n")
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _insert_code_block(self) -> None:
        cursor = self.editor.textCursor()
        selected = self._selected_text(cursor)
        self._insert_block(markdown_ops.code_block(selected))

    def _insert_horizontal_rule(self) -> None:
        self._insert_block(markdown_ops.horizontal_rule())

    def _insert_markdown_table(self) -> None:
        self._insert_block(markdown_ops.markdown_table_skeleton())

    def _insert_html_table(self) -> None:
        self._insert_block(markdown_ops.html_table_skeleton())

    def _select_trailing_url(self, cursor: QTextCursor, start: int, text: str) -> None:
        url_start = start + text.index("https://")
        url_end = url_start + len("https://")
        cursor.setPosition(url_start)
        cursor.setPosition(url_end, QTextCursor.MoveMode.KeepAnchor)

    def _insert_link(self) -> None:
        cursor = self.editor.textCursor()
        selected = self._selected_text(cursor)
        start = cursor.selectionStart()
        text = markdown_ops.make_link(selected)
        cursor.insertText(text)
        self._select_trailing_url(cursor, start, text)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _insert_image(self) -> None:
        cursor = self.editor.textCursor()
        selected = self._selected_text(cursor)
        start = cursor.selectionStart()
        text = markdown_ops.make_image(selected)
        cursor.insertText(text)
        self._select_trailing_url(cursor, start, text)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    # ─── File and preview handling ────────────────────────────────────────────

    def _update_preview(self) -> None:
        try:
            self.preview.setHtml(markdown_ops.render_markdown_to_html(self.editor.toPlainText()))
        except Exception as exc:
            self.preview.setPlainText(f"Preview error: {exc}")

    def _clear_text(self) -> None:
        if self.editor.toPlainText().strip():
            confirm = QMessageBox.question(
                self, "Clear Document", "Discard the current document text? This can't be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
        self.editor.clear()
        self._current_path = None

    def load_file(self, file_path: str) -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.editor.setPlainText(f.read())
            self._current_path = file_path
        except Exception as exc:
            QMessageBox.critical(self, "Load Error", f"Could not read document: {exc}")

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Markdown File", "",
            "Markdown (*.md *.markdown);;Text (*.txt);;All Files (*.*)"
        )
        if path:
            self.load_file(path)

    def _save_file(self) -> None:
        if self._current_path:
            self._write_to(self._current_path)
        else:
            self._save_file_as()

    def _save_file_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Markdown File", "document.md",
            "Markdown (*.md);;Text (*.txt);;All Files (*.*)"
        )
        if path:
            self._write_to(path)
            self._current_path = path

    def _write_to(self, path: str) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            QMessageBox.information(self, "Saved", f"Markdown saved to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    def _export_html(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export HTML", "document.html", "HTML (*.html);;All Files (*.*)"
        )
        if not path:
            return
        body = markdown_ops.render_markdown_to_html(self.editor.toPlainText())
        document = f'<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n</head>\n<body>\n{body}\n</body>\n</html>\n'
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(document)
            QMessageBox.information(self, "Exported", f"HTML exported to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", str(exc))
