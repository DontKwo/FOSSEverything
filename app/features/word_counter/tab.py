"""Word Counter & Document Analytics workspace tab."""
from __future__ import annotations

import os
import re
from typing import Optional, Callable, Any
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QTextEdit, QPushButton,
    QLabel, QFileDialog, QMessageBox, QGroupBox, QScrollArea, QFrame, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView,
)

from app.core.customizable_toolbar import AppToolBar
from app.features.word_counter import ops as word_counter_ops
from app.core.theme import resolved_palette, theme_signals
from app.core.tooltips import get_tooltip_for
from app.ui.ui_scaling import scaled_font_pt, scaled_font_size


class WordCounterTab(QWidget):
    """Interactive workspace for word counting and document analytics."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._on_text_changed()
        theme_signals.changed.connect(self._refresh_theme_colors)

    def _refresh_theme_colors(self) -> None:
        palette = resolved_palette()
        self.reading_ease_val.setStyleSheet(f"font-weight: 700; color: {palette['accent']};")
        for card in (self.card_words, self.card_chars, self.card_chars_ns, self.card_sentences, self.card_paragraphs, self.card_read_time, self.card_speak_time):
            card.setStyleSheet(
                f"QGroupBox {{ background: {palette['panel']}; "
                f"border: 1px solid {palette['border']}; border-radius: 6px; }}"
            )
            card.val_label.setStyleSheet(f"font-size: {scaled_font_pt(16)}; font-weight: 700; color: {palette[card.color_key]};")
            card.title_label.setStyleSheet(f"font-size: {scaled_font_pt(11)}; color: {palette['muted']};")

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header
        title_label = QLabel("Word Counter & Document Analytics")
        title_label.setStyleSheet("font-weight: 700;")
        root.addWidget(title_label)

        top_bar = AppToolBar(None, "word_counter_toolbar")
        top_bar.add_action("Open File (PDF, DOCX, XLSX, PPTX, TXT)...", self._browse_file, tooltip_key="Open File")
        top_bar.add_action("Paste Clipboard", self._paste_clipboard, tooltip_key="Paste Clipboard")
        top_bar.add_action("Clear", self._clear_text, tooltip_key="Clear All")
        top_bar.finalize()
        root.addWidget(top_bar)

        # Quick stats badges banner
        self.badge_layout = QHBoxLayout()
        self.badge_layout.setSpacing(10)

        self.card_words = self._make_stat_badge("Words", "0", "accent")
        self.card_chars = self._make_stat_badge("Characters", "0", "text")
        self.card_chars_ns = self._make_stat_badge("Chars (No Space)", "0", "success")
        self.card_sentences = self._make_stat_badge("Sentences", "0", "warning")
        self.card_paragraphs = self._make_stat_badge("Paragraphs", "0", "danger")
        self.card_read_time = self._make_stat_badge("Reading Time", "0s", "accent")
        self.card_speak_time = self._make_stat_badge("Speaking Time", "0s", "text")

        for card in (self.card_words, self.card_chars, self.card_chars_ns, self.card_sentences, self.card_paragraphs, self.card_read_time, self.card_speak_time):
            self.badge_layout.addWidget(card)

        root.addLayout(self.badge_layout)

        # Splitter: Text editor on left, analytics on right
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Editor
        editor_box = QGroupBox("Document Text")
        editor_layout = QVBoxLayout(editor_box)
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Type, paste text, or open any document (PDF, Word, Excel, PowerPoint, Text, Markdown) to analyze stats in real-time...")
        self.editor.setFont(QFont("Segoe UI", scaled_font_size(10)))
        self.editor.textChanged.connect(self._on_text_changed)
        editor_layout.addWidget(self.editor)

        # Transform tools row
        transform_row = AppToolBar(None, "word_counter_transform_toolbar")
        transform_row.add_action("UPPERCASE", lambda: self._transform_text(str.upper), tooltip_key="UPPERCASE")
        transform_row.add_action("lowercase", lambda: self._transform_text(str.lower), tooltip_key="lowercase")
        transform_row.add_action("Title Case", lambda: self._transform_text(str.title), tooltip_key="Title Case")
        transform_row.add_action("Clean Extra Spaces", self._clean_extra_spaces, tooltip_key="Clean Extra Spaces")
        transform_row.addSeparator()
        transform_row.add_action("Save Text...", self._save_text_file, tooltip_key="Save Text")
        transform_row.finalize()
        editor_layout.addWidget(transform_row)

        splitter.addWidget(editor_box)

        # Right: Analytics Panel
        right_scroll = QScrollArea(widgetResizable=True, frameShape=QFrame.Shape.NoFrame)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(12)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Readability Box
        read_box = QGroupBox("Readability && Structure")
        read_form = QFormLayout(read_box)

        self.reading_ease_val = QLabel("100.0 / 100")
        self.reading_ease_val.setStyleSheet(f"font-weight: 700; color: {resolved_palette()['accent']};")
        read_form.addRow("Flesch Reading Ease:", self.reading_ease_val)

        self.grade_level_val = QLabel("N/A")
        read_form.addRow("Grade Level:", self.grade_level_val)

        self.pages_val = QLabel("0.0 pages")
        read_form.addRow("Estimated Pages:", self.pages_val)

        self.avg_word_len_val = QLabel("0.0 chars")
        read_form.addRow("Avg. Word Length:", self.avg_word_len_val)

        self.avg_sent_len_val = QLabel("0.0 words")
        read_form.addRow("Avg. Sentence Length:", self.avg_sent_len_val)

        right_layout.addWidget(read_box)

        # Keyword density table
        kw_box = QGroupBox("Keyword Density (Top Words)")
        kw_layout = QVBoxLayout(kw_box)
        self.kw_table = QTableWidget(0, 3)
        self.kw_table.setHorizontalHeaderLabels(["Word", "Count", "Density"])
        self.kw_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.kw_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.kw_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        kw_layout.addWidget(self.kw_table)
        right_layout.addWidget(kw_box, stretch=1)

        right_scroll.setWidget(right_widget)
        right_scroll.setMinimumWidth(320)
        splitter.addWidget(right_scroll)
        splitter.setSizes([650, 350])

        root.addWidget(splitter, stretch=1)

    def _make_stat_badge(self, title: str, default_val: str, color_key: str) -> QGroupBox:
        box = QGroupBox()
        palette = resolved_palette()
        box.setStyleSheet(
            f"QGroupBox {{ background: {palette['panel']}; "
            f"border: 1px solid {palette['border']}; border-radius: 6px; }}"
        )
        l = QVBoxLayout(box)
        l.setContentsMargins(8, 6, 8, 6)
        l.setSpacing(2)

        val_label = QLabel(default_val)
        val_label.setStyleSheet(f"font-size: {scaled_font_pt(16)}; font-weight: 700; color: {palette[color_key]};")
        val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.val_label = val_label
        box.color_key = color_key

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: {scaled_font_pt(11)}; color: {palette['muted']};")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.title_label = title_label

        l.addWidget(val_label)
        l.addWidget(title_label)
        return box

    def load_file(self, file_path: str) -> None:
        """Load text from any supported file format."""
        try:
            txt = word_counter_ops.extract_text_from_file(file_path)
            self.editor.setPlainText(txt)
        except Exception as exc:
            QMessageBox.critical(self, "Load Error", f"Could not read document: {exc}")

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Document for Word Counter", "",
            "All Supported Documents (*.pdf *.docx *.pptx *.xlsx *.odt *.ods *.odp *.txt *.md *.html *.csv *.json *.yaml *.py);;Office Documents (*.docx *.pptx *.xlsx *.odt *.ods *.odp);;PDF Documents (*.pdf);;Text & Markdown (*.txt *.md *.html);;All Files (*.*)"
        )
        if path:
            self.load_file(path)

    def _paste_clipboard(self) -> None:
        txt = QGuiApplication.clipboard().text()
        if txt:
            self.editor.setPlainText(txt)

    def _clear_text(self) -> None:
        self.editor.clear()

    def _transform_text(self, func: Callable[[str], str]) -> None:
        txt = self.editor.toPlainText()
        if txt:
            self.editor.setPlainText(func(txt))

    def _clean_extra_spaces(self) -> None:
        txt = self.editor.toPlainText()
        cleaned = re.sub(r"[ \t]+", " ", txt)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        self.editor.setPlainText(cleaned.strip())

    def _save_text_file(self) -> None:
        txt = self.editor.toPlainText()
        if not txt:
            QMessageBox.warning(self, "Empty Text", "No text to save.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Text File", "document.txt", "Plain Text (*.txt);;Markdown (*.md);;All Files (*.*)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(txt)
                QMessageBox.information(self, "Saved", f"Text saved to {path}")
            except Exception as exc:
                QMessageBox.critical(self, "Save Error", str(exc))

    def _on_text_changed(self) -> None:
        text = self.editor.toPlainText()
        stats = word_counter_ops.analyze_text(text)

        # Update badges
        self.card_words.val_label.setText(f"{stats['words']:,}")
        self.card_chars.val_label.setText(f"{stats['characters']:,}")
        self.card_chars_ns.val_label.setText(f"{stats['characters_no_spaces']:,}")
        self.card_sentences.val_label.setText(f"{stats['sentences']:,}")
        self.card_paragraphs.val_label.setText(f"{stats['paragraphs']:,}")

        # Times
        r_secs = stats['reading_time_secs']
        r_str = f"{r_secs // 60}m {r_secs % 60}s" if r_secs >= 60 else f"{r_secs}s"
        self.card_read_time.val_label.setText(r_str)

        s_secs = stats['speaking_time_secs']
        s_str = f"{s_secs // 60}m {s_secs % 60}s" if s_secs >= 60 else f"{s_secs}s"
        self.card_speak_time.val_label.setText(s_str)

        # Readability
        fre = stats['flesch_reading_ease']
        self.reading_ease_val.setText(f"{fre:.1f} / 100")
        self.grade_level_val.setText(f"{stats['flesch_kincaid_grade']} - {stats['readability_label']}")
        self.pages_val.setText(f"~{stats['pages_est']} pages")
        self.avg_word_len_val.setText(f"{stats['avg_word_length']} characters")
        self.avg_sent_len_val.setText(f"{stats['avg_sentence_length']} words")

        # Keywords
        kws = stats['top_keywords']
        self.kw_table.setRowCount(len(kws))
        for r, kw in enumerate(kws):
            self.kw_table.setItem(r, 0, QTableWidgetItem(kw["word"]))
            self.kw_table.setItem(r, 1, QTableWidgetItem(str(kw["count"])))
            self.kw_table.setItem(r, 2, QTableWidgetItem(f"{kw['density_pct']}%"))

