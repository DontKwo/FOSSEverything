"""OCR Studio workspace: extract text from images/PDFs and create searchable PDFs."""
from __future__ import annotations

import os
from typing import Sequence
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, QSettings
from PyQt6.QtGui import QGuiApplication, QPixmap, QImage, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QTextEdit, QPushButton, QLabel, QFileDialog, QMessageBox, QGroupBox,
    QTabWidget, QCheckBox, QProgressBar, QSplitter, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QRadioButton, QButtonGroup
)
import pymupdf
from PIL import Image
from app.core.customizable_toolbar import AppToolBar
from app.features.ocr import ops as ocr_ops
from app.features.office import ops as office_ops
from app.core.theme import resolved_palette, theme_signals
from app.core.tooltips import get_tooltip_for
from app.ui.ui_scaling import scaled_font_pt, scaled_font_size


class _OcrWorker(QObject):
    """Background worker for OCR processing."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)  # current, total

    def __init__(self, file_path: str, pages: list[int] | None, language: str, dpi: int) -> None:
        super().__init__()
        self.file_path = file_path
        self.pages = pages
        self.language = language
        self.dpi = dpi

    def run(self) -> None:
        try:
            def _prog(curr: int, tot: int) -> None:
                self.progress.emit(curr, tot)

            result = ocr_ops.ocr_file(
                self.file_path,
                pages=self.pages,
                language=self.language,
                dpi=self.dpi,
                progress_callback=_prog,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class _SearchablePdfWorker(QObject):
    """Background worker for searchable PDF generation."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)

    def __init__(self, input_path: str, output_path: str, pages: list[int] | None, language: str, dpi: int) -> None:
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.pages = pages
        self.language = language
        self.dpi = dpi

    def run(self) -> None:
        try:
            def _prog(curr: int, tot: int) -> None:
                self.progress.emit(curr, tot)

            out = ocr_ops.create_searchable_pdf(
                self.input_path,
                self.output_path,
                pages=self.pages,
                language=self.language,
                dpi=self.dpi,
                progress_callback=_prog,
            )
            self.finished.emit(out)
        except Exception as exc:
            self.error.emit(str(exc))


class OcrTab(QWidget):
    """Standalone OCR Studio workspace."""

    def __init__(self, parent: QWidget | None = None, settings: QSettings | None = None) -> None:
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings("FOSSEverything", "FOSSEverything")
        self.current_file: str | None = None
        self.current_page_idx: int = 0
        self.total_pages: int = 0
        self.ocr_result: dict | None = None
        self._thread: QThread | None = None
        self._worker: QObject | None = None

        self._build_ui()
        theme_signals.changed.connect(self._refresh_theme_colors)

    def _refresh_theme_colors(self) -> None:
        self.preview_label.setStyleSheet(self._preview_box_stylesheet())

    def _preview_box_stylesheet(self) -> str:
        palette = resolved_palette(self.settings)
        return f"background: {palette['panel']}; border: 1px solid {palette['border']}; border-radius: 4px;"

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("OCR Studio")
        title.setStyleSheet("font-weight: 700;")
        sub = QLabel("Extract copyable text from scanned documents and images, or generate searchable PDFs offline.")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box, stretch=1)
        root.addLayout(header)

        # Main tabs: Document OCR vs Batch OCR
        self.main_tabs = QTabWidget()
        self.main_tabs.addTab(self._build_doc_ocr_tab(), "Document OCR")
        self.main_tabs.addTab(self._build_batch_ocr_tab(), "Batch OCR")
        root.addWidget(self.main_tabs, stretch=1)

    # ─── Document OCR View ───────────────────────────────────────────────────
    def _build_doc_ocr_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(14)

        # Top file control bar
        top_bar = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText(
            "Select a PDF or image file (PNG, JPG, TIFF, WEBP, BMP, etc)...")
        self.file_path_edit.setReadOnly(True)
        top_bar.addWidget(self.file_path_edit, stretch=1)

        browse_btn = QPushButton("Open File...")
        browse_btn.setToolTip(get_tooltip_for("Open File"))
        browse_btn.setStyleSheet("font-weight: 600; padding: 6px 14px;")
        browse_btn.clicked.connect(self._browse_file)
        top_bar.addWidget(browse_btn)

        layout.addLayout(top_bar)

        # Main Splitter: Left Preview + Controls, Right Text Output
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel (Preview & OCR Config)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(14)

        # Preview box
        preview_group = QGroupBox("Document Preview")
        prev_layout = QVBoxLayout(preview_group)
        prev_layout.setContentsMargins(8, 8, 8, 8)

        # Page nav
        nav_row = QHBoxLayout()
        self.prev_page_btn = QPushButton("◀ Prev")
        self.prev_page_btn.setToolTip(get_tooltip_for("Previous page"))
        self.prev_page_btn.clicked.connect(self._prev_page)
        self.prev_page_btn.setEnabled(False)
        self.page_label = QLabel("No document loaded")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_page_btn = QPushButton("Next ▶")
        self.next_page_btn.setToolTip(get_tooltip_for("Next page"))
        self.next_page_btn.clicked.connect(self._next_page)
        self.next_page_btn.setEnabled(False)

        nav_row.addWidget(self.prev_page_btn)
        nav_row.addWidget(self.page_label, stretch=1)
        nav_row.addWidget(self.next_page_btn)
        prev_layout.addLayout(nav_row)

        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setMinimumHeight(240)
        self.preview_label = QLabel("Open a document to see preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet(self._preview_box_stylesheet())
        self.preview_scroll.setWidget(self.preview_label)
        prev_layout.addWidget(self.preview_scroll, stretch=1)

        left_layout.addWidget(preview_group, stretch=1)

        # OCR Settings
        settings_group = QGroupBox("OCR Configuration")
        form = QFormLayout(settings_group)
        form.setContentsMargins(10, 10, 10, 10)
        form.setSpacing(8)

        # Language
        self.lang_combo = QComboBox()
        self.lang_combo.setToolTip(get_tooltip_for("Recognition Language"))
        for code, name in ocr_ops.get_supported_languages().items():
            self.lang_combo.addItem(f"{name} ({code})", code)
        self.lang_combo.setCurrentIndex(0)  # English default
        form.addRow("Recognition Language:", self.lang_combo)

        # DPI
        self.dpi_combo = QComboBox()
        self.dpi_combo.setToolTip(get_tooltip_for("Scan Resolution"))
        self.dpi_combo.addItem("Standard (150 DPI) - Fast", 150)
        self.dpi_combo.addItem("High Quality (200 DPI) - Recommended", 200)
        self.dpi_combo.addItem("Ultra (300 DPI) - Fine text / receipts", 300)
        self.dpi_combo.setCurrentIndex(1)
        form.addRow("Scan Resolution:", self.dpi_combo)

        # Page range
        self.page_range_edit = QLineEdit()
        self.page_range_edit.setPlaceholderText("All pages (or e.g. 1-3, 5)")
        form.addRow("Pages to Process:", self.page_range_edit)

        left_layout.addWidget(settings_group)

        # Action Buttons
        btn_row = QHBoxLayout()
        self.run_ocr_btn = QPushButton("Extract Text (OCR)")
        self.run_ocr_btn.setToolTip(get_tooltip_for("Extract Text (OCR)"))
        self.run_ocr_btn.setStyleSheet(f"font-weight: 700; padding: 9px 18px; font-size: {scaled_font_pt(13)};")
        self.run_ocr_btn.clicked.connect(self._run_ocr)
        self.run_ocr_btn.setEnabled(False)

        self.make_pdf_btn = QPushButton("Make Searchable PDF...")
        self.make_pdf_btn.setToolTip(get_tooltip_for("Make Searchable PDF"))
        self.make_pdf_btn.setStyleSheet(f"padding: 9px 14px; font-size: {scaled_font_pt(13)};")
        self.make_pdf_btn.clicked.connect(self._export_searchable_pdf)
        self.make_pdf_btn.setEnabled(False)

        btn_row.addWidget(self.run_ocr_btn, stretch=1)
        btn_row.addWidget(self.make_pdf_btn)
        left_layout.addLayout(btn_row)

        self.ocr_progress = QProgressBar()
        self.ocr_progress.setVisible(False)
        left_layout.addWidget(self.ocr_progress)

        splitter.addWidget(left_widget)

        # Right Panel (Extracted Text & Actions)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        text_header = QHBoxLayout()
        text_title = QLabel("Extracted Text")
        text_title.setStyleSheet(f"font-weight: 700; font-size: {scaled_font_pt(14)};")
        self.stats_label = QLabel("0 characters | 0 words")
        self.stats_label.setStyleSheet(f"font-size: {scaled_font_pt(11)};")
        text_header.addWidget(text_title)
        text_header.addStretch(1)
        text_header.addWidget(self.stats_label)
        right_layout.addLayout(text_header)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Extracted OCR text will appear here. You can edit and format the text directly.")
        font = QFont("Consolas" if os.name == "nt" else "Monospace", scaled_font_size(10))
        self.text_edit.setFont(font)
        self.text_edit.textChanged.connect(self._update_stats)
        right_layout.addWidget(self.text_edit, stretch=1)

        # Text Action Buttons
        actions_toolbar = AppToolBar(self.settings, "ocr_text_actions_toolbar")
        actions_toolbar.add_action("Copy to Clipboard", self._copy_text)
        actions_toolbar.add_action("Save as .txt", lambda: self._save_text_file(as_markdown=False))
        actions_toolbar.add_action("Save as .md", lambda: self._save_text_file(as_markdown=True))
        actions_toolbar.addSeparator()
        actions_toolbar.add_action("Clear", self._clear_text, tooltip_key="Clear All")
        actions_toolbar.finalize()
        right_layout.addWidget(actions_toolbar)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        layout.addWidget(splitter, stretch=1)
        return w

    # ─── Batch OCR View ──────────────────────────────────────────────────────
    def _build_batch_ocr_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        toolbar = AppToolBar(self.settings, "ocr_batch_toolbar")
        toolbar.add_action("Add Files...", self._batch_add_files, tooltip_key="Add Files")
        toolbar.add_action("Clear List", self._batch_clear, tooltip_key="Clear All")
        toolbar.finalize()
        layout.addWidget(toolbar)

        # Table
        self.batch_table = QTableWidget(0, 4)
        self.batch_table.setHorizontalHeaderLabels(["Filename", "Pages/Type", "Target Format", "Status"])
        self.batch_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.batch_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.batch_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.batch_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.batch_table, stretch=1)

        # Batch Config & Run
        config_row = QHBoxLayout()
        config_row.addWidget(QLabel("Output Format:"))
        self.batch_fmt_combo = QComboBox()
        self.batch_fmt_combo.setToolTip(get_tooltip_for("Batch Output Format"))
        self.batch_fmt_combo.addItems(["Searchable PDF (.pdf)", "Plain Text (.txt)", "Markdown (.md)"])
        config_row.addWidget(self.batch_fmt_combo)

        config_row.addWidget(QLabel("Language:"))
        self.batch_lang_combo = QComboBox()
        self.batch_lang_combo.setToolTip(get_tooltip_for("Recognition Language"))
        for code, name in ocr_ops.get_supported_languages().items():
            self.batch_lang_combo.addItem(f"{name} ({code})", code)
        config_row.addWidget(self.batch_lang_combo)

        out_dir_btn = QPushButton("Output Folder...")
        out_dir_btn.setToolTip(get_tooltip_for("Output Folder"))
        out_dir_btn.clicked.connect(self._choose_batch_out_dir)
        self.batch_out_dir_edit = QLineEdit()
        self.batch_out_dir_edit.setPlaceholderText("Save in source file folder")
        self.batch_out_dir_edit.setReadOnly(True)
        config_row.addWidget(out_dir_btn)
        config_row.addWidget(self.batch_out_dir_edit, stretch=1)

        self.start_batch_btn = QPushButton("Run Batch OCR")
        self.start_batch_btn.setToolTip(get_tooltip_for("Run Batch OCR"))
        self.start_batch_btn.setStyleSheet("font-weight: 700; padding: 8px 16px;")
        self.start_batch_btn.clicked.connect(self._run_batch_ocr)
        config_row.addWidget(self.start_batch_btn)
        layout.addLayout(config_row)

        self.batch_progress = QProgressBar()
        self.batch_progress.setVisible(False)
        layout.addWidget(self.batch_progress)

        return w

    # ─── File Loading & Navigation ───────────────────────────────────────────
    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Document, Office File, or Image for Text Extraction / OCR",
            "",
            "All Supported Files (*.pdf *.docx *.pptx *.xlsx *.odt *.ods *.odp *.png *.jpg *.jpeg *.webp *.tiff *.tif *.bmp *.gif);;Office Documents (*.docx *.pptx *.xlsx *.odt *.ods *.odp);;PDFs (*.pdf);;Images (*.png *.jpg *.jpeg *.webp *.tiff *.tif *.bmp);;All Files (*.*)"
        )
        if path:
            self.load_file(path)

    def load_file(self, path: str) -> None:
        if not os.path.exists(path):
            return
        self.current_file = path
        self.file_path_edit.setText(path)
        self.current_page_idx = 0

        ext = os.path.splitext(path)[1].lower()
        if ext in (".docx", ".pptx", ".xlsx", ".odt", ".ods", ".odp", ".docm", ".pptm", ".xlsm"):
            try:
                txt = office_ops.extract_text_from_office(path)
                self.text_edit.setPlainText(txt)
                self.stats_label.setText(f"Extracted: {len(txt.split())} words | {len(txt)} chars")
                self.total_pages = 1
                self.preview_label.setText(f"Office Document: {os.path.basename(path)}\n\nDirect text extracted successfully.")
                self.page_label.setText("Office Document")
                self.run_ocr_btn.setEnabled(False)
                self.make_pdf_btn.setEnabled(True)
                return
            except Exception as e:
                QMessageBox.warning(self, "Office Extraction", f"Could not read Office file: {e}")

        if ext == ".pdf":
            try:
                with pymupdf.open(path) as doc:
                    self.total_pages = len(doc)
            except Exception as e:
                QMessageBox.critical(self, "PDF Error", f"Could not open PDF: {e}")
                return
        else:
            self.total_pages = 1

        self.run_ocr_btn.setEnabled(True)
        self.make_pdf_btn.setEnabled(True)
        self._update_preview()

    def _update_preview(self) -> None:
        if not self.current_file or not os.path.exists(self.current_file):
            self.preview_label.setText("No document loaded")
            self.page_label.setText("No document loaded")
            self.prev_page_btn.setEnabled(False)
            self.next_page_btn.setEnabled(False)
            return

        self.page_label.setText(f"Page {self.current_page_idx + 1} of {self.total_pages}")
        self.prev_page_btn.setEnabled(self.current_page_idx > 0)
        self.next_page_btn.setEnabled(self.current_page_idx < self.total_pages - 1)

        ext = os.path.splitext(self.current_file)[1].lower()
        try:
            if ext == ".pdf":
                with pymupdf.open(self.current_file) as doc:
                    page = doc[self.current_page_idx]
                    pix = page.get_pixmap(dpi=100)
                    img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(img)
            else:
                pixmap = QPixmap(self.current_file)

            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    450, 600,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled)
            else:
                self.preview_label.setText("Could not render preview")
        except Exception as e:
            self.preview_label.setText(f"Preview error: {e}")

    def _prev_page(self) -> None:
        if self.current_page_idx > 0:
            self.current_page_idx -= 1
            self._update_preview()

    def _next_page(self) -> None:
        if self.current_page_idx < self.total_pages - 1:
            self.current_page_idx += 1
            self._update_preview()

    # ─── OCR Execution ───────────────────────────────────────────────────────
    def _parse_pages(self) -> list[int] | None:
        txt = self.page_range_edit.text().strip()
        if not txt:
            return None
        pages = set()
        parts = txt.split(",")
        for part in parts:
            part = part.strip()
            if "-" in part:
                sub = part.split("-")
                try:
                    s, e = int(sub[0]), int(sub[1])
                    for p in range(s, e + 1):
                        pages.add(p)
                except ValueError:
                    continue
            elif part.isdigit():
                pages.add(int(part))
        return sorted(pages) if pages else None

    def _run_ocr(self) -> None:
        if not self.current_file:
            return

        lang = self.lang_combo.currentData()
        dpi = int(self.dpi_combo.currentData())
        pages = self._parse_pages()

        self.run_ocr_btn.setEnabled(False)
        self.ocr_progress.setValue(0)
        self.ocr_progress.setVisible(True)

        self._thread = QThread(self)
        self._worker = _OcrWorker(self.current_file, pages, lang, dpi)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_ocr_progress)
        self._worker.finished.connect(self._on_ocr_finished)
        self._worker.error.connect(self._on_ocr_error)

        self._thread.start()

    def _on_ocr_progress(self, curr: int, total: int) -> None:
        if total > 0:
            pct = int((curr / total) * 100)
            self.ocr_progress.setValue(pct)

    def _on_ocr_finished(self, result: dict) -> None:
        self.ocr_result = result
        self.text_edit.setPlainText(result.get("text", ""))
        self._cleanup_worker()
        self.run_ocr_btn.setEnabled(True)
        self.ocr_progress.setVisible(False)

    def _on_ocr_error(self, err_msg: str) -> None:
        self._cleanup_worker()
        self.run_ocr_btn.setEnabled(True)
        self.ocr_progress.setVisible(False)
        QMessageBox.critical(self, "OCR Error", f"OCR processing failed:\n{err_msg}")

    def _cleanup_worker(self) -> None:
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
        self._thread = None
        self._worker = None

    # ─── Searchable PDF Export ───────────────────────────────────────────────
    def _export_searchable_pdf(self) -> None:
        if not self.current_file:
            return

        base = os.path.splitext(os.path.basename(self.current_file))[0]
        default_out = f"{base}_searchable.pdf"
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Searchable PDF",
            default_out,
            "PDF Files (*.pdf)"
        )
        if not out_path:
            return

        lang = self.lang_combo.currentData()
        dpi = int(self.dpi_combo.currentData())
        pages = self._parse_pages()

        self.make_pdf_btn.setEnabled(False)
        self.ocr_progress.setValue(0)
        self.ocr_progress.setVisible(True)

        self._thread = QThread(self)
        self._worker = _SearchablePdfWorker(self.current_file, out_path, pages, lang, dpi)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_ocr_progress)
        self._worker.finished.connect(self._on_searchable_pdf_finished)
        self._worker.error.connect(self._on_ocr_error)

        self._thread.start()

    def _on_searchable_pdf_finished(self, out_path: str) -> None:
        self._cleanup_worker()
        self.make_pdf_btn.setEnabled(True)
        self.ocr_progress.setVisible(False)
        QMessageBox.information(self, "Success", f"Searchable PDF created successfully:\n{out_path}")

    # ─── Text Editor Utilities ───────────────────────────────────────────────
    def _update_stats(self) -> None:
        txt = self.text_edit.toPlainText()
        char_count = len(txt)
        word_count = len(txt.split()) if txt else 0
        line_count = len(txt.splitlines()) if txt else 0
        self.stats_label.setText(f"{char_count} chars | {word_count} words | {line_count} lines")

    def _copy_text(self) -> None:
        txt = self.text_edit.toPlainText()
        if not txt:
            return
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(txt)
            QMessageBox.information(self, "Copied", "Extracted text copied to clipboard.")

    def _save_text_file(self, as_markdown: bool = False) -> None:
        txt = self.text_edit.toPlainText()
        if not txt:
            QMessageBox.warning(self, "Empty Text", "No text to save.")
            return

        ext = ".md" if as_markdown else ".txt"
        filt = "Markdown Files (*.md)" if as_markdown else "Text Files (*.txt)"
        path, _ = QFileDialog.getSaveFileName(self, "Save OCR Text", f"ocr_output{ext}", filt)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
            QMessageBox.information(self, "Saved", f"Text saved to:\n{path}")

    def _clear_text(self) -> None:
        self.text_edit.clear()

    # ─── Batch OCR ───────────────────────────────────────────────────────────
    def _batch_add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Documents/Images for Batch OCR",
            "",
            "Documents and Images (*.pdf *.png *.jpg *.jpeg *.webp *.tiff *.tif *.bmp);;All Files (*.*)"
        )
        for p in paths:
            row = self.batch_table.rowCount()
            self.batch_table.insertRow(row)
            self.batch_table.setItem(row, 0, QTableWidgetItem(os.path.basename(p)))
            self.batch_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, p)
            ext = os.path.splitext(p)[1].lower()
            self.batch_table.setItem(row, 1, QTableWidgetItem("PDF" if ext == ".pdf" else f"Image ({ext[1:].upper()})"))
            self.batch_table.setItem(row, 2, QTableWidgetItem(self.batch_fmt_combo.currentText()))
            self.batch_table.setItem(row, 3, QTableWidgetItem("Pending"))

    def _batch_clear(self) -> None:
        self.batch_table.setRowCount(0)

    def _choose_batch_out_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Choose Output Directory")
        if d:
            self.batch_out_dir_edit.setText(d)

    def _run_batch_ocr(self) -> None:
        count = self.batch_table.rowCount()
        if count == 0:
            QMessageBox.warning(self, "Empty Queue", "No files in the batch queue.")
            return

        lang = self.batch_lang_combo.currentData()
        fmt = self.batch_fmt_combo.currentText()
        target_dir = self.batch_out_dir_edit.text().strip() or None

        self.start_batch_btn.setEnabled(False)
        self.batch_progress.setValue(0)
        self.batch_progress.setVisible(True)

        success = 0
        failed = 0

        for r in range(count):
            p = self.batch_table.item(r, 0).data(Qt.ItemDataRole.UserRole)
            self.batch_table.setItem(r, 3, QTableWidgetItem("Processing..."))
            QGuiApplication.processEvents()

            base_dir = target_dir if target_dir else os.path.dirname(p)
            base_name = os.path.splitext(os.path.basename(p))[0]

            try:
                if "Searchable PDF" in fmt:
                    out = os.path.join(base_dir, f"{base_name}_searchable.pdf")
                    ocr_ops.create_searchable_pdf(p, out, language=lang)
                elif "Markdown" in fmt:
                    out = os.path.join(base_dir, f"{base_name}_ocr.md")
                    res = ocr_ops.ocr_file(p, language=lang)
                    ocr_ops.save_ocr_text(res, out, as_markdown=True)
                else:
                    out = os.path.join(base_dir, f"{base_name}_ocr.txt")
                    res = ocr_ops.ocr_file(p, language=lang)
                    ocr_ops.save_ocr_text(res, out, as_markdown=False)

                self.batch_table.setItem(r, 3, QTableWidgetItem("Done"))
                success += 1
            except Exception as e:
                self.batch_table.setItem(r, 3, QTableWidgetItem(f"Failed: {e}"))
                failed += 1

            self.batch_progress.setValue(int(((r + 1) / count) * 100))
            QGuiApplication.processEvents()

        self.start_batch_btn.setEnabled(True)
        self.batch_progress.setVisible(False)
        msg = f"Finished processing {count} files:\n- {success} succeeded\n- {failed} failed"
        QMessageBox.information(self, "Batch OCR Complete", msg)
