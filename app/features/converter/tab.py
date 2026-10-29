"""Format Converter workspace backed by explicit local capabilities."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional, Any, Callable
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import (
    QFileDialog, QComboBox, QFormLayout, QHBoxLayout, QLabel, QMessageBox,
    QProgressDialog, QPushButton, QVBoxLayout, QWidget, QLineEdit,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QGroupBox
)

from app.features.converter import ops as converter_ops
from app.features.media import ops as media_ops
from app.core.customizable_toolbar import AppToolBar
from app.core.spinbox import NoScrollSpinBox
from app.core.theme import resolved_palette, theme_signals
from app.core.tooltips import get_tooltip_for
from app.system.workers import WorkerThread

COMPRESSOR_PRESETS = {
    "Small (max compression)": {"preset": "small", "quality": 60, "audio_bitrate": "96k", "max_width": 1600, "max_height": 1600},
    "Balanced": {"preset": "balanced", "quality": 80, "audio_bitrate": "128k", "max_width": None, "max_height": None},
    "High Quality": {"preset": "quality", "quality": 92, "audio_bitrate": "192k", "max_width": None, "max_height": None},
}


class ConverterTab(QWidget):
    """Convert files locally while exposing only supported target formats."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.input_path: Optional[str] = None
        self.compressor_input_path: Optional[str] = None
        self.batch_items: list[converter_ops.BatchConversionItem] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        heading = QLabel("File Format Converter")
        heading.setStyleSheet("font-weight: 700;")
        root.addWidget(heading)
        root.addWidget(QLabel("Convert documents, images, and data formats locally with explicit engine checks."))

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_single_tab(), "Single File Converter")
        self.tabs.addTab(self._build_batch_tab(), "Batch Conversion Queue")
        self.tabs.addTab(self._build_compressor_tab(), "Compressor")
        root.addWidget(self.tabs, stretch=1)
        theme_signals.changed.connect(self._refresh_theme_colors)

    def _refresh_theme_colors(self) -> None:
        self.summary_label.setStyleSheet(f"color: {resolved_palette()['muted']}; padding: 6px;")

    # ─── Single File Tab ──────────────────────────────────────────────────────
    def _build_single_tab(self) -> QWidget:
        w: QWidget = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        source_row = QHBoxLayout()
        self.source_label = QLabel("No file selected")
        palette = self.palette()
        self.source_label.setStyleSheet(
            f"padding: 6px; background: {palette.color(QPalette.ColorRole.Base).name()}; "
            f"border: 1px solid {palette.color(QPalette.ColorRole.Mid).name()}; border-radius: 6px;"
        )
        choose_button = QPushButton("Choose file...")
        choose_button.setToolTip(get_tooltip_for("Choose file"))
        choose_button.clicked.connect(self.choose_file)
        source_row.addWidget(self.source_label, stretch=1)
        source_row.addWidget(choose_button)
        layout.addLayout(source_row)

        form = QFormLayout()
        self.target_combo = QComboBox()
        self.target_combo.setToolTip(get_tooltip_for("Convert to"))
        self.target_combo.currentTextChanged.connect(self._update_summary)
        form.addRow("Convert to:", self.target_combo)
        self.output_name = QLineEdit()
        self.output_name.setPlaceholderText("Output filename (without extension)")
        self.output_name.setToolTip(get_tooltip_for("Output filename"))
        form.addRow("Output filename:", self.output_name)
        self.dpi_spin = NoScrollSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(144)
        self.dpi_spin.setSuffix(" DPI")
        self.dpi_spin.setToolTip(get_tooltip_for("PDF resolution"))
        form.addRow("PDF resolution:", self.dpi_spin)
        layout.addLayout(form)

        self.summary_label = QLabel("Image, PDF, JSON, YAML, and CSV conversions run 100% locally on your machine.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(f"color: {resolved_palette()['muted']}; padding: 6px;")
        layout.addWidget(self.summary_label)

        self.convert_button = QPushButton("Convert locally")
        self.convert_button.setToolTip(get_tooltip_for("Convert locally"))
        self.convert_button.setEnabled(False)
        self.convert_button.setStyleSheet("font-weight: 700; padding: 8px 16px;")
        self.convert_button.clicked.connect(self.convert)
        layout.addWidget(self.convert_button)

        notes_export_button = QPushButton("Export Notes Folder to ENEX...")
        notes_export_button.setToolTip(get_tooltip_for("Export Notes Folder to ENEX..."))
        notes_export_button.clicked.connect(self._export_notes_folder_to_enex)
        layout.addWidget(notes_export_button)
        layout.addStretch()
        return w

    def _export_notes_folder_to_enex(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose a folder of plain-text/Markdown notes")
        if not folder:
            return
        note_files = sorted(
            f for f in os.listdir(folder) if f.lower().endswith((".txt", ".md"))
        )
        if not note_files:
            QMessageBox.warning(self, "No notes found", "That folder has no .txt or .md files.")
            return
        output_path, _ = QFileDialog.getSaveFileName(self, "Save ENEX file", os.path.join(folder, "notes.enex"), "Evernote Notes (*.enex)")
        if not output_path:
            return

        self._progress_dialog = QProgressDialog("Exporting to ENEX...", None, 0, 0, self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()

        self._worker = WorkerThread(
            self._do_export_notes, folder, note_files, output_path
        )
        self._worker.finished_ok.connect(lambda count: self._on_export_complete(count, output_path))
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _do_export_notes(self, folder: str, note_files: list[str], output_path: str) -> int:
        notes = []
        for filename in note_files:
            full_path = os.path.join(folder, filename)
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            mtime = os.path.getmtime(full_path)
            created = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            notes.append({
                "title": os.path.splitext(filename)[0],
                "content": content,
                "created": created,
                "updated": created,
                "tags": [],
            })
        converter_ops.export_enex(notes, output_path)
        return len(notes)

    def _on_export_complete(self, count: int, output_path: str) -> None:
        self._progress_dialog.close()
        QMessageBox.information(self, "Exported", f"{count} note(s) exported to {output_path}")

    # ─── Batch Queue Tab ──────────────────────────────────────────────────────
    def _build_batch_tab(self) -> QWidget:
        w: QWidget = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        top_controls = AppToolBar(None, "converter_batch_toolbar")
        top_controls.add_action("Add Files...", self._batch_add_files, tooltip_key="Add Files")
        top_controls.add_action("Clear Queue", self._batch_clear, tooltip_key="Clear Queue")
        top_controls.addSeparator()
        top_controls.addWidget(QLabel("Target Format for All:"))
        self.batch_target_combo = QComboBox()
        self.batch_target_combo.setToolTip(get_tooltip_for("Target Format for All"))
        self.batch_target_combo.addItems(["PNG", "JPEG", "WEBP", "PDF", "JSON", "YAML", "CSV"])
        top_controls.addWidget(self.batch_target_combo)
        top_controls.add_action("Apply to All", self._batch_apply_format_to_all, tooltip_key="Apply to All")
        top_controls.finalize()
        layout.addWidget(top_controls)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Filename", "Source Type", "Target Format", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, stretch=1)

        bottom_row = QHBoxLayout()
        self.batch_progress = QProgressBar()
        self.batch_progress.setValue(0)
        bottom_row.addWidget(self.batch_progress, stretch=1)

        self.start_batch_btn = QPushButton("Start Batch Conversion")
        self.start_batch_btn.setToolTip(get_tooltip_for("Start Batch Conversion"))
        self.start_batch_btn.setStyleSheet("font-weight: 700; padding: 8px 18px;")
        self.start_batch_btn.clicked.connect(self._start_batch_convert)
        bottom_row.addWidget(self.start_batch_btn)
        layout.addLayout(bottom_row)

        return w

    # ─── Compressor Tab ───────────────────────────────────────────────────────
    def _build_compressor_tab(self) -> QWidget:
        w: QWidget = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        layout.addWidget(QLabel("Shrink any image, audio, or video file locally with one preset - no need to know which studio handles which format."))

        source_row = QHBoxLayout()
        self.compressor_source_label = QLabel("No file selected")
        palette = self.palette()
        self.compressor_source_label.setStyleSheet(
            f"padding: 6px; background: {palette.color(QPalette.ColorRole.Base).name()}; "
            f"border: 1px solid {palette.color(QPalette.ColorRole.Mid).name()}; border-radius: 6px;"
        )
        choose_button = QPushButton("Choose file...")
        choose_button.setToolTip(get_tooltip_for("Choose file"))
        choose_button.clicked.connect(self._compressor_choose_file)
        source_row.addWidget(self.compressor_source_label, stretch=1)
        source_row.addWidget(choose_button)
        layout.addLayout(source_row)

        form = QFormLayout()
        self.compressor_preset_combo = QComboBox()
        self.compressor_preset_combo.setToolTip(get_tooltip_for("Compressor Preset"))
        self.compressor_preset_combo.addItems(list(COMPRESSOR_PRESETS.keys()))
        self.compressor_preset_combo.setCurrentText("Balanced")
        form.addRow("Preset:", self.compressor_preset_combo)
        layout.addLayout(form)

        self.compressor_summary_label = QLabel("Select a file to see its detected type and current size.")
        self.compressor_summary_label.setWordWrap(True)
        self.compressor_summary_label.setStyleSheet(f"color: {resolved_palette()['muted']}; padding: 6px;")
        layout.addWidget(self.compressor_summary_label)

        self.compressor_button = QPushButton("Compress locally")
        self.compressor_button.setToolTip(get_tooltip_for("Compress locally"))
        self.compressor_button.setEnabled(False)
        self.compressor_button.setStyleSheet("font-weight: 700; padding: 8px 16px;")
        self.compressor_button.clicked.connect(self._run_compressor)
        layout.addWidget(self.compressor_button)
        layout.addStretch()
        return w

    def _detect_compressor_kind(self, path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"):
            return "image"
        if ext in (".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"):
            return "audio"
        return "video"

    def _compressor_choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose file to compress", "",
            "Compressible Files (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.mp3 *.wav *.flac *.aac *.m4a *.ogg *.mp4 *.mov *.mkv *.avi *.webm);;All Files (*.*)"
        )
        if not path:
            return
        self.compressor_input_path = path
        kind = self._detect_compressor_kind(path)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        self.compressor_source_label.setText(os.path.basename(path))
        self.compressor_summary_label.setText(f"Detected type: {kind} | Current size: {size_mb:.2f} MB")
        self.compressor_button.setEnabled(True)

    def _run_compressor(self) -> None:
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save compressed file",
            os.path.splitext(self.compressor_input_path)[0] + "_compressed" + os.path.splitext(self.compressor_input_path)[1],
        )
        if not output_path:
            return
        cfg = COMPRESSOR_PRESETS[self.compressor_preset_combo.currentText()]
        self._progress_dialog = QProgressDialog("Compressing locally...", None, 0, 0, self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()
        self._worker = WorkerThread(
            media_ops.compress_media, self.compressor_input_path, output_path,
            cfg["preset"], None, cfg["quality"], cfg["max_width"], cfg["max_height"], cfg["audio_bitrate"],
        )
        self._worker.finished_ok.connect(lambda out: self._on_compressor_complete(out, output_path))
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_compressor_complete(self, output_path: str, _display_path: str) -> None:
        self._progress_dialog.close()
        before = os.path.getsize(self.compressor_input_path) / (1024 * 1024)
        after = os.path.getsize(output_path) / (1024 * 1024)
        QMessageBox.information(
            self, "Compression complete",
            f"Saved to {output_path}\n{before:.2f} MB -> {after:.2f} MB"
        )

    def choose_file(self) -> None:
        path: str
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose file to convert", "",
            "All Supported Files (*.pdf *.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.gif *.heic *.heif *.avif *.svg *.psd *.docx *.pptx *.xlsx *.odt *.ods *.odp *.json *.yaml *.yml *.csv *.mp4 *.mov *.mkv *.avi *.webm *.mp3 *.wav *.flac *.aac *.m4a *.ogg *.ttf *.otf *.woff *.woff2 *.epub *.mobi *.azw *.azw3 *.fb2 *.enex);;Office Documents (*.docx *.pptx *.xlsx *.odt *.ods *.odp);;Documents (*.pdf *.docx *.pptx *.xlsx);;Images (*.png *.jpg *.jpeg *.webp *.gif *.heic *.heif *.avif *.svg *.psd);;RAW Photos (*.cr2 *.cr3 *.nef *.arw *.dng *.raf *.orf *.rw2 *.pef *.srw);;Audio & Video (*.mp4 *.mov *.mkv *.mp3 *.wav);;Fonts (*.ttf *.otf *.woff *.woff2);;E-books (*.epub *.mobi *.azw *.azw3 *.fb2);;Evernote Notes (*.enex);;Data (*.json *.yaml *.csv);;All Files (*.*)"
        )
        if not path:
            return
        self.load_file(path)

    def load_file(self, path: str) -> None:
        targets: list[str] = converter_ops.available_targets(path)
        if not targets:
            QMessageBox.warning(self, "Not supported yet", "This file has no installed local conversion backend yet.")
            return
        self.input_path = path
        self.source_label.setText(os.path.basename(path))
        self.source_label.setToolTip(path)
        self.output_name.setText(os.path.splitext(os.path.basename(path))[0])
        self.target_combo.clear()
        self.target_combo.addItems(targets)
        self.convert_button.setEnabled(True)
        self._update_summary()

    def _update_summary(self) -> None:
        if self.input_path and self.target_combo.currentText():
            self.summary_label.setText(converter_ops.conversion_summary(self.input_path, self.target_combo.currentText()))

    def convert(self) -> None:
        output_dir: str = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if not output_dir:
            return
        output_stem: str = self.output_name.text().strip()
        if not output_stem:
            QMessageBox.warning(self, "Output filename", "Enter an output filename.")
            return
        if os.path.basename(output_stem) != output_stem or output_stem in {".", ".."}:
            QMessageBox.warning(self, "Output filename", "Enter a filename only, not a folder path.")
            return
        self._progress_dialog = QProgressDialog("Converting locally...", None, 0, 0, self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()
        self._worker = WorkerThread(
            converter_ops.convert_file, self.input_path, output_dir,
            self.target_combo.currentText(), self.dpi_spin.value(), output_stem,
        )
        self._worker.finished_ok.connect(self._on_complete)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_complete(self, outputs: list) -> None:
        self._progress_dialog.close()
        QMessageBox.information(self, "Conversion complete", f"Wrote {len(outputs)} file(s).")

    def _on_failed(self, message: str) -> None:
        if hasattr(self, "_progress_dialog") and self._progress_dialog is not None:
            self._progress_dialog.close()
        QMessageBox.critical(self, "Conversion failed", message)

    # ─── Batch methods ────────────────────────────────────────────────────────
    def _batch_add_files(self) -> None:
        paths: list[str]
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Choose files for batch conversion", "",
            "All Supported (*.pdf *.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.gif *.heic *.heif *.avif *.svg *.psd *.cr2 *.cr3 *.nef *.arw *.dng *.raf *.orf *.rw2 *.pef *.srw *.json *.yaml *.yml *.csv *.mp4 *.mov *.mkv *.avi *.webm *.mp3 *.wav *.flac *.aac *.m4a *.ogg);;All Files (*.*)"
        )
        if not paths:
            return
        for path in paths:
            targets: list[str] = converter_ops.available_targets(path)
            if not targets:
                continue
            family: str = converter_ops.source_family(path) or "Unknown"
            default_target: str = targets[0]
            item: converter_ops.BatchConversionItem = converter_ops.BatchConversionItem(input_path=path, target_format=default_target)
            self.batch_items.append(item)

        self._refresh_batch_table()

    def _refresh_batch_table(self) -> None:
        self.table.setRowCount(len(self.batch_items))
        for row, item in enumerate(self.batch_items):
            self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(item.input_path)))
            self.table.setItem(row, 1, QTableWidgetItem(converter_ops.source_family(item.input_path) or "Unknown"))
            self.table.setItem(row, 2, QTableWidgetItem(item.target_format))
            status_item: QTableWidgetItem = QTableWidgetItem(item.status)
            if item.status == "done":
                status_item.setForeground(Qt.GlobalColor.green)
            elif item.status == "failed":
                status_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 3, status_item)

    def _batch_clear(self) -> None:
        self.batch_items.clear()
        self.table.setRowCount(0)
        self.batch_progress.setValue(0)

    def _batch_apply_format_to_all(self) -> None:
        target: str = self.batch_target_combo.currentText()
        for item in self.batch_items:
            available: list[str] = converter_ops.available_targets(item.input_path)
            if target in available:
                item.target_format = target
        self._refresh_batch_table()

    def _start_batch_convert(self) -> None:
        if not self.batch_items:
            QMessageBox.warning(self, "No files", "Add files to the batch conversion queue first.")
            return
        output_dir: str = QFileDialog.getExistingDirectory(self, "Choose Output Directory for Batch")
        if not output_dir:
            return

        self.batch_progress.setMaximum(len(self.batch_items))
        self.batch_progress.setValue(0)
        self.start_batch_btn.setEnabled(False)

        def _progress(done: int, total: int, item: Any) -> None:
            self.batch_progress.setValue(done)
            self._refresh_batch_table()

        self._worker = WorkerThread(
            converter_ops.batch_convert_files, self.batch_items, output_dir, progress_cb=_progress
        )
        self._worker.finished_ok.connect(self._on_batch_ok)
        self._worker.failed.connect(self._on_batch_failed)
        self._worker.start()

    def _on_batch_ok(self, results: list) -> None:
        self.start_batch_btn.setEnabled(True)
        self._refresh_batch_table()
        done_count: int = sum(1 for item in results if item.status == "done")
        QMessageBox.information(
            self, "Batch Complete", f"Successfully converted {done_count} of {len(results)} file(s)."
        )

    def _on_batch_failed(self, error: str) -> None:
        self.start_batch_btn.setEnabled(True)
        QMessageBox.critical(self, "Batch Error", f"Batch conversion error: {error}")
