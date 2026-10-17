"""PDF tab: view, annotate, merge, split, and compress PDFs."""
import os
from typing import Callable, Optional

from PyQt6.QtCore import QPointF, QRectF, QSettings, Qt, QTimer
from PyQt6.QtGui import QImage, QAction, QActionGroup, QKeySequence, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStyle, QFileDialog,
    QLabel, QPushButton, QMessageBox, QDialog, QFormLayout, QComboBox,
    QSlider, QDialogButtonBox, QListWidget, QListWidgetItem, QAbstractItemView,
    QLineEdit, QProgressDialog, QTabWidget, QButtonGroup, QRadioButton,
    QCheckBox, QFontComboBox, QStackedWidget, QProgressBar, QGraphicsItem, QSizePolicy
)

from app.ui.canvas import AnnotationCanvas, Tool, ResizableTextItem, show_shortcuts_dialog
from app.features.pdf import ops as pdf_ops
from app.core.customizable_toolbar import AppToolBar
from app.core.spinbox import NoScrollSpinBox
from app.core.theme import resolved_palette, theme_signals
from app.core.tooltips import get_tooltip_for
from app.ui.ui_scaling import scaled_font_size
from app.system.workers import WorkerThread


class CompressDialog(QDialog):
    """Easy mode: 3 one-click presets, like most online compressors.
    Advanced mode: the original quality-preset + DPI slider controls."""

    EASY_PRESETS = {
        "Small file size": ("screen", 72),
        "Balanced": ("ebook", 120),
        "Best quality": ("printer", 200),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Compress PDF")
        self.resize(380, 280)
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # ---- Easy tab ----
        easy_widget = QWidget()
        easy_layout = QVBoxLayout(easy_widget)
        easy_layout.addWidget(QLabel("Choose a compression level:"))
        self.easy_group = QButtonGroup(self)
        self.easy_radios = {}
        descriptions = {
            "Small file size": "Smallest file, more image quality loss.",
            "Balanced": "Good trade-off for most documents (recommended).",
            "Best quality": "Largest file, minimal quality loss.",
        }
        for name in self.EASY_PRESETS:
            rb = QRadioButton(name)
            rb.setToolTip(get_tooltip_for(name))
            self.easy_group.addButton(rb)
            self.easy_radios[name] = rb
            easy_layout.addWidget(rb)
            hint = QLabel(f"    {descriptions[name]}")
            easy_layout.addWidget(hint)
        self.easy_radios["Balanced"].setChecked(True)
        easy_layout.addStretch()
        self.tabs.addTab(easy_widget, "Easy")

        # ---- Advanced tab ----
        adv_widget = QWidget()
        adv_layout = QFormLayout(adv_widget)

        self.quality_combo = QComboBox()
        self.quality_combo.setToolTip(get_tooltip_for("Compression preset"))
        self.quality_combo.addItems(["screen", "ebook", "printer", "prepress"])
        self.quality_combo.setCurrentText("ebook")
        adv_layout.addRow("Preset:", self.quality_combo)

        self.dpi_slider = QSlider(Qt.Orientation.Horizontal)
        self.dpi_slider.setRange(50, 300)
        self.dpi_slider.setValue(120)
        self.dpi_label = QLabel("120 DPI")
        self.dpi_slider.valueChanged.connect(lambda v: self.dpi_label.setText(f"{v} DPI"))
        dpi_row = QHBoxLayout()
        dpi_row.addWidget(self.dpi_slider)
        dpi_row.addWidget(self.dpi_label)
        adv_layout.addRow("Image DPI:", dpi_row)

        self.tabs.addTab(adv_widget, "Advanced")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, int]:
        if self.tabs.currentIndex() == 0:  # Easy tab
            for name, rb in self.easy_radios.items():
                if rb.isChecked():
                    return self.EASY_PRESETS[name]
            return self.EASY_PRESETS["Balanced"]
        return self.quality_combo.currentText(), self.dpi_slider.value()


class ExportPagesDialog(QDialog):
    """Choose a raster format for all pages of the current PDF."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export PDF Pages")
        layout = QFormLayout(self)
        self.format_combo = QComboBox()
        self.format_combo.setToolTip(get_tooltip_for("Export image format"))
        self.format_combo.addItems(pdf_ops.PAGE_IMAGE_FORMATS)
        layout.addRow("Image format:", self.format_combo)
        self.dpi_spin = NoScrollSpinBox()
        self.dpi_spin.setToolTip(get_tooltip_for("Export resolution"))
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(144)
        self.dpi_spin.setSuffix(" DPI")
        layout.addRow("Resolution:", self.dpi_spin)
        layout.addRow(QLabel("Each PDF page is written as a separate numbered image."))
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> tuple[str, int]:
        return self.format_combo.currentText(), self.dpi_spin.value()


class MergeDialog(QDialog):
    """Pick multiple PDFs, sort and/or reorder them for merging.

    Full paths are always stored on each list item (Qt.ItemDataRole.UserRole)
    since that's what's actually needed to open the files; only the
    *displayed* text and the *sort key* switch to basename-only unless the
    "Use full paths" checkbox is on.
    """

    SORT_OPTIONS = [
        "Manual order",
        "Name (A - Z)",
        "Name (Z - A)",
        "Date Modified (Newest first)",
        "Date Modified (Oldest first)",
        "Date Created (Newest first)",
        "Date Created (Oldest first)",
        "Size (Largest first)",
        "Size (Smallest first)",
    ]

    def __init__(self, parent: QWidget | None = None, initial_path: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Merge PDFs")
        self.resize(460, 400)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Files will be merged in this order (drag to reorder):"))

        sort_row = QHBoxLayout()
        sort_row.addWidget(QLabel("Sort by:"))
        self.sort_combo = QComboBox()
        self.sort_combo.setToolTip(get_tooltip_for("Merge sort order"))
        self.sort_combo.addItems(self.SORT_OPTIONS)
        sort_row.addWidget(self.sort_combo, stretch=1)
        sort_btn = QPushButton("Apply Sort")
        sort_btn.setToolTip(get_tooltip_for("Apply Sort"))
        sort_btn.clicked.connect(self._apply_sort)
        sort_row.addWidget(sort_btn)
        layout.addLayout(sort_row)

        self.full_path_check = QCheckBox("Show and sort by full path (instead of filename only)")
        self.full_path_check.setToolTip(get_tooltip_for("Sort by full path"))
        self.full_path_check.toggled.connect(self._refresh_display)
        layout.addWidget(self.full_path_check)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Files...")
        add_btn.setToolTip(get_tooltip_for("Add Files"))
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setToolTip(get_tooltip_for("Remove Selected"))
        up_btn = QPushButton("▲ Move Up")
        up_btn.setToolTip(get_tooltip_for("Move Up"))
        down_btn = QPushButton("▼ Move Down")
        down_btn.setToolTip(get_tooltip_for("Move Down"))
        add_btn.clicked.connect(self._add_files)
        remove_btn.clicked.connect(self._remove_selected)
        up_btn.clicked.connect(lambda: self._move(-1))
        down_btn.clicked.connect(lambda: self._move(1))
        for b in (add_btn, remove_btn, up_btn, down_btn):
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if initial_path:
            self._add_path(initial_path)

    def _display_text(self, full_path: str) -> str:
        return full_path if self.full_path_check.isChecked() else os.path.basename(full_path)

    def _add_path(self, full_path: str) -> None:
        item = QListWidgetItem(self._display_text(full_path))
        item.setData(Qt.ItemDataRole.UserRole, full_path)
        item.setToolTip(full_path)
        self.list_widget.addItem(item)

    def _refresh_display(self) -> None:
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            full_path = item.data(Qt.ItemDataRole.UserRole)
            item.setText(self._display_text(full_path))

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select PDFs", "", "PDF Files (*.pdf)")
        for p in paths:
            self._add_path(p)

    def _remove_selected(self) -> None:
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))

    def _move(self, delta: int) -> None:
        row = self.list_widget.currentRow()
        new_row = row + delta
        if row < 0 or new_row < 0 or new_row >= self.list_widget.count():
            return
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(new_row, item)
        self.list_widget.setCurrentRow(new_row)

    def _apply_sort(self) -> None:
        mode = self.sort_combo.currentText()
        if mode == "Manual order":
            return
        full_paths = self.get_paths()
        if not full_paths:
            return
        use_full = self.full_path_check.isChecked()
        name_key = (lambda p: p.lower()) if use_full else (lambda p: os.path.basename(p).lower())
        try:
            if mode == "Name (A -- Z)":
                full_paths.sort(key=name_key)
            elif mode == "Name (Z -- A)":
                full_paths.sort(key=name_key, reverse=True)
            elif mode == "Date Modified (Newest first)":
                full_paths.sort(key=os.path.getmtime, reverse=True)
            elif mode == "Date Modified (Oldest first)":
                full_paths.sort(key=os.path.getmtime)
            elif mode == "Date Created (Newest first)":
                # Linux: getctime is metadata-change time; Windows/macOS: true creation time.
                full_paths.sort(key=os.path.getctime, reverse=True)
            elif mode == "Date Created (Oldest first)":
                full_paths.sort(key=os.path.getctime)
            elif mode == "Size (Largest first)":
                full_paths.sort(key=os.path.getsize, reverse=True)
            elif mode == "Size (Smallest first)":
                full_paths.sort(key=os.path.getsize)
        except OSError as exc:
            QMessageBox.warning(self, "Sort failed", f"Couldn't read file info: {exc}")
            return
        self.list_widget.clear()
        for p in full_paths:
            self._add_path(p)

    def get_paths(self) -> list[str]:
        return [
            self.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.list_widget.count())
        ]


class ProtectDialog(QDialog):
    """Dialog to encrypt a PDF with password protection."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Protect PDF with Password")
        self.resize(380, 220)
        layout = QFormLayout(self)
        self.user_pwd = QLineEdit()
        self.user_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.user_pwd.setPlaceholderText("Password required to open the PDF")
        self.confirm_pwd = QLineEdit()
        self.confirm_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pwd.setPlaceholderText("Repeat password")
        self.owner_pwd = QLineEdit()
        self.owner_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.owner_pwd.setPlaceholderText("Optional owner/master password")
        self.allow_print = QCheckBox("Allow printing")
        self.allow_print.setToolTip(get_tooltip_for("Allow printing"))
        self.allow_print.setChecked(True)

        layout.addRow("Open Password*:", self.user_pwd)
        layout.addRow("Confirm Password*:", self.confirm_pwd)
        layout.addRow("Owner Password:", self.owner_pwd)
        layout.addRow(self.allow_print)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _validate_and_accept(self) -> None:
        p1 = self.user_pwd.text()
        p2 = self.confirm_pwd.text()
        if not p1:
            QMessageBox.warning(self, "Password required", "Please enter a password.")
            return
        if p1 != p2:
            QMessageBox.warning(self, "Passwords do not match", "The passwords you entered do not match.")
            return
        self.accept()

    def values(self) -> tuple[str, str | None, bool]:
        return self.user_pwd.text(), self.owner_pwd.text() or None, self.allow_print.isChecked()


class UnlockDialog(QDialog):
    """Dialog to enter a password and decrypt a PDF."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Unlock / Decrypt PDF")
        self.resize(340, 140)
        layout = QFormLayout(self)
        layout.addRow(QLabel("Enter the password to remove protection and save a clean PDF:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Password:", self.password_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def password(self) -> str:
        return self.password_edit.text()


class PageOrganizerDialog(QDialog):
    """Visual page manager to reorder, rotate, delete, duplicate, and extract pages."""

    def __init__(self, total_pages: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Organize PDF Pages")
        self.resize(520, 480)
        layout = QHBoxLayout(self)

        list_container = QVBoxLayout()
        list_container.addWidget(QLabel("Current Pages (drag or use buttons to reorder):"))
        self.page_list = QListWidget()
        self.page_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.page_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        for i in range(1, total_pages + 1):
            item = QListWidgetItem(f"Page {i} (Source p.{i})")
            item.setData(Qt.ItemDataRole.UserRole, {"source_page": i, "rotation": 0})
            self.page_list.addItem(item)
        list_container.addWidget(self.page_list)
        layout.addLayout(list_container, stretch=1)

        btn_layout = QVBoxLayout()
        btn_layout.addWidget(QLabel("Page Actions:"))
        up_btn = QPushButton("▲ Move Up")
        up_btn.setToolTip(get_tooltip_for("Move Up"))
        up_btn.clicked.connect(self._move_up)
        btn_layout.addWidget(up_btn)

        down_btn = QPushButton("▼ Move Down")
        down_btn.setToolTip(get_tooltip_for("Move Down"))
        down_btn.clicked.connect(self._move_down)
        btn_layout.addWidget(down_btn)

        rot_cw_btn = QPushButton("Rotate 90° CW")
        rot_cw_btn.setToolTip(get_tooltip_for("Rotate clockwise"))
        rot_cw_btn.clicked.connect(lambda: self._rotate_selected(90))
        btn_layout.addWidget(rot_cw_btn)

        rot_ccw_btn = QPushButton("Rotate 90° CCW")
        rot_ccw_btn.setToolTip(get_tooltip_for("Rotate counterclockwise"))
        rot_ccw_btn.clicked.connect(lambda: self._rotate_selected(-90))
        btn_layout.addWidget(rot_ccw_btn)

        dup_btn = QPushButton("Duplicate Page")
        dup_btn.setToolTip(get_tooltip_for("Duplicate Page"))
        dup_btn.clicked.connect(self._duplicate_selected)
        btn_layout.addWidget(dup_btn)

        self.del_btn = QPushButton("Delete Page")
        self.del_btn.setToolTip(get_tooltip_for("Delete Page"))
        self.del_btn.setStyleSheet(f"color: {resolved_palette()['danger']}; font-weight: 600;")
        self.del_btn.clicked.connect(self._delete_selected)
        btn_layout.addWidget(self.del_btn)

        btn_layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._check_and_accept)
        buttons.rejected.connect(self.reject)
        btn_layout.addWidget(buttons)
        layout.addLayout(btn_layout)

        theme_signals.changed.connect(self._refresh_theme_colors)

    def _refresh_theme_colors(self) -> None:
        self.del_btn.setStyleSheet(f"color: {resolved_palette()['danger']}; font-weight: 600;")

    def _move_up(self) -> None:
        row = self.page_list.currentRow()
        if row > 0:
            item = self.page_list.takeItem(row)
            self.page_list.insertItem(row - 1, item)
            self.page_list.setCurrentRow(row - 1)

    def _move_down(self) -> None:
        row = self.page_list.currentRow()
        if 0 <= row < self.page_list.count() - 1:
            item = self.page_list.takeItem(row)
            self.page_list.insertItem(row + 1, item)
            self.page_list.setCurrentRow(row + 1)

    def _rotate_selected(self, deg: int) -> None:
        for item in self.page_list.selectedItems():
            data = item.data(Qt.ItemDataRole.UserRole)
            rot = (data["rotation"] + deg) % 360
            data["rotation"] = rot
            item.setData(Qt.ItemDataRole.UserRole, data)
            rot_str = f" [{rot}°]" if rot else ""
            item.setText(f"Page {data['source_page']} (Source p.{data['source_page']}){rot_str}")

    def _duplicate_selected(self) -> None:
        items = self.page_list.selectedItems()
        for item in items:
            data = item.data(Qt.ItemDataRole.UserRole).copy()
            row = self.page_list.row(item)
            new_item = QListWidgetItem(f"Page {data['source_page']} (Copy of p.{data['source_page']})")
            new_item.setData(Qt.ItemDataRole.UserRole, data)
            self.page_list.insertItem(row + 1, new_item)

    def _delete_selected(self) -> None:
        items = self.page_list.selectedItems()
        for item in items:
            self.page_list.takeItem(self.page_list.row(item))

    def _check_and_accept(self) -> None:
        if self.page_list.count() == 0:
            QMessageBox.warning(self, "No pages", "You must keep at least one page in the document.")
            return
        self.accept()

    def page_operations(self) -> list[dict[str, int]]:
        ops = []
        for i in range(self.page_list.count()):
            item = self.page_list.item(i)
            ops.append(item.data(Qt.ItemDataRole.UserRole))
        return ops


class SplitDialog(QDialog):
    """Ask the user for a page-range string, e.g. '1-3,5,7-9'."""

    def __init__(self, total_pages: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Split PDF")
        layout = QFormLayout(self)
        layout.addRow(QLabel(f"Document has {total_pages} pages."))
        self.range_edit = QLineEdit()
        self.range_edit.setPlaceholderText("e.g. 1-3,5,7-9")
        layout.addRow("Ranges:", self.range_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def parsed_ranges(self) -> list[tuple[int, int]]:
        text = self.range_edit.text().strip()
        ranges = []
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-")
                ranges.append((int(a), int(b)))
            else:
                n = int(part)
                ranges.append((n, n))
        return ranges

class WatermarkDialog(QDialog):
    """Dialog to configure and apply a text watermark to a PDF."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add PDF Watermark")
        self.resize(420, 320)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Stamp a transparent diagonal text watermark on each page."))

        form = QFormLayout()
        self.text_edit = QLineEdit("CONFIDENTIAL")
        form.addRow("Watermark Text:", self.text_edit)

        self.opacity_spin = NoScrollSpinBox()
        self.opacity_spin.setToolTip(get_tooltip_for("Watermark opacity"))
        self.opacity_spin.setRange(5, 80)
        self.opacity_spin.setValue(25)
        self.opacity_spin.setSuffix("% opacity")
        form.addRow("Opacity:", self.opacity_spin)

        self.font_size_spin = NoScrollSpinBox()
        self.font_size_spin.setToolTip(get_tooltip_for("Watermark font size"))
        self.font_size_spin.setRange(10, 200)
        self.font_size_spin.setValue(64)
        self.font_size_spin.setSuffix(" pt")
        form.addRow("Font Size:", self.font_size_spin)

        self.angle_spin = NoScrollSpinBox()
        self.angle_spin.setToolTip(get_tooltip_for("Watermark rotation angle"))
        self.angle_spin.setRange(0, 180)
        self.angle_spin.setValue(45)
        self.angle_spin.setSuffix("°")
        form.addRow("Rotation Angle:", self.angle_spin)

        self.color_combo = QComboBox()
        self.color_combo.setToolTip(get_tooltip_for("Watermark color"))
        self.color_combo.addItem("Red (CONFIDENTIAL)", (0.8, 0.0, 0.0))
        self.color_combo.addItem("Dark Gray (DRAFT)", (0.3, 0.3, 0.3))
        self.color_combo.addItem("Blue (FOR REVIEW)", (0.0, 0.0, 0.8))
        self.color_combo.addItem("Green (APPROVED)", (0.0, 0.5, 0.0))
        form.addRow("Color:", self.color_combo)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, float, int, tuple[float, float, float], float]:
        return (
            self.text_edit.text(),
            self.opacity_spin.value() / 100.0,
            self.font_size_spin.value(),
            self.color_combo.currentData(),
            float(self.angle_spin.value()),
        )


class TextExtractDialog(QDialog):
    """Dialog to choose text extraction format, engine, and output path."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Extract Text from PDF")
        self.resize(420, 260)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Extract text from PDF pages into a local file (plain text or Markdown)."))

        form = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.setToolTip(get_tooltip_for("Text extraction output format"))
        self.mode_combo.addItem("Plain Text (.txt)", "plain")
        self.mode_combo.addItem("Markdown (.md)", "markdown")
        form.addRow("Output Format:", self.mode_combo)

        self.ocr_check = QCheckBox("Use OCR recognition (recommended for scanned PDFs)")
        self.ocr_check.setToolTip(get_tooltip_for("OCR text extraction"))
        form.addRow("OCR Engine:", self.ocr_check)

        self.lang_combo = QComboBox()
        self.lang_combo.setToolTip(get_tooltip_for("OCR language"))
        from app.features.ocr import ops as ocr_ops  # noqa: 13 (keeps PIL out of every PDF tab's cold-start import)
        for code, name in ocr_ops.get_supported_languages().items():
            self.lang_combo.addItem(f"{name} ({code})", code)
        self.lang_combo.setEnabled(False)
        self.ocr_check.toggled.connect(self.lang_combo.setEnabled)
        form.addRow("OCR Language:", self.lang_combo)

        self.sep_check = QCheckBox("Add '--- Page N ---' separators between pages")
        self.sep_check.setToolTip(get_tooltip_for("Page separators"))
        self.sep_check.setChecked(True)
        form.addRow("", self.sep_check)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, bool, bool, str | None]:
        return (
            self.mode_combo.currentData(),
            self.sep_check.isChecked(),
            self.ocr_check.isChecked(),
            self.lang_combo.currentData(),
        )



class PageNumberDialog(QDialog):
    """Dialog to configure and stamp page numbers or headers/footers."""

    def __init__(self, total_pages: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Page Numbers & Headers/Footers")
        self.resize(440, 340)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Stamp page numbers or header/footer labels across document ({total_pages} pages)."))

        form = QFormLayout()
        self.format_combo = QComboBox()
        self.format_combo.setToolTip(get_tooltip_for("Page number format"))
        self.format_combo.setEditable(True)
        self.format_combo.addItems([
            "Page {n} of {total}",
            "{n} / {total}",
            "Page {n}",
            "- {n} -",
            "{n}",
        ])
        form.addRow("Format / Template:", self.format_combo)

        self.pos_combo = QComboBox()
        self.pos_combo.setToolTip(get_tooltip_for("Page number position"))
        self.pos_combo.addItem("Bottom Center (Standard)", "bottom_center")
        self.pos_combo.addItem("Bottom Right", "bottom_right")
        self.pos_combo.addItem("Bottom Left", "bottom_left")
        self.pos_combo.addItem("Top Center (Header)", "top_center")
        self.pos_combo.addItem("Top Right (Header)", "top_right")
        self.pos_combo.addItem("Top Left (Header)", "top_left")
        form.addRow("Position:", self.pos_combo)

        self.font_size_spin = NoScrollSpinBox()
        self.font_size_spin.setToolTip(get_tooltip_for("Page number font size"))
        self.font_size_spin.setRange(6, 48)
        self.font_size_spin.setValue(10)
        self.font_size_spin.setSuffix(" pt")
        form.addRow("Font Size:", self.font_size_spin)

        self.margin_spin = NoScrollSpinBox()
        self.margin_spin.setToolTip(get_tooltip_for("Page number margin"))
        self.margin_spin.setRange(10, 150)
        self.margin_spin.setValue(36)
        self.margin_spin.setSuffix(" pt")
        form.addRow("Margin from Edge:", self.margin_spin)

        self.start_spin = NoScrollSpinBox()
        self.start_spin.setToolTip(get_tooltip_for("Page numbering start"))
        self.start_spin.setRange(1, 9999)
        self.start_spin.setValue(1)
        form.addRow("Start Number:", self.start_spin)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str, float, float, int]:
        return (
            self.format_combo.currentText().strip() or "Page {n} of {total}",
            self.pos_combo.currentData(),
            float(self.font_size_spin.value()),
            float(self.margin_spin.value()),
            self.start_spin.value(),
        )


class BatchDialog(QDialog):
    """Run one PDF operation (compress, watermark, or protect) over multiple files."""

    MODES = ["Compress", "Watermark (Text)", "Watermark (Image)", "Protect (Password)"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Batch Process PDFs")
        self.resize(520, 560)
        self._worker = None
        self.items: list[pdf_ops.BatchPdfItem] = []
        layout = QVBoxLayout(self)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Operation:"))
        self.mode_combo = QComboBox()
        self.mode_combo.setToolTip(get_tooltip_for("Batch operation mode"))
        self.mode_combo.addItems(self.MODES)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo, stretch=1)
        layout.addLayout(mode_row)

        self.options_stack = QStackedWidget()
        self.options_stack.addWidget(self._build_compress_options())
        self.options_stack.addWidget(self._build_text_watermark_options())
        self.options_stack.addWidget(self._build_image_watermark_options())
        self.options_stack.addWidget(self._build_protect_options())
        layout.addWidget(self.options_stack)

        layout.addWidget(QLabel("Files:"))
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.list_widget, stretch=1)

        file_btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Files...")
        add_btn.setToolTip(get_tooltip_for("Add Files"))
        add_btn.clicked.connect(self._add_files)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setToolTip(get_tooltip_for("Remove Selected"))
        remove_btn.clicked.connect(self._remove_selected)
        file_btn_row.addWidget(add_btn)
        file_btn_row.addWidget(remove_btn)
        layout.addLayout(file_btn_row)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output folder:"))
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        out_row.addWidget(self.output_dir_edit, stretch=1)
        browse_out_btn = QPushButton("Browse...")
        browse_out_btn.setToolTip(get_tooltip_for("Browse"))
        browse_out_btn.clicked.connect(self._choose_output_dir)
        out_row.addWidget(browse_out_btn)
        layout.addLayout(out_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.start_btn = QPushButton("Start Batch")
        self.start_btn.setToolTip(get_tooltip_for("Start Batch"))
        self.start_btn.setStyleSheet("font-weight: 700; padding: 8px 16px;")
        self.start_btn.clicked.connect(self._start_batch)
        layout.addWidget(self.start_btn)

    def _build_compress_options(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.quality_combo = QComboBox()
        self.quality_combo.setToolTip(get_tooltip_for("Batch compression preset"))
        self.quality_combo.addItems(["screen", "ebook", "printer", "prepress"])
        self.quality_combo.setCurrentText("ebook")
        form.addRow("Preset:", self.quality_combo)
        self.dpi_spin = NoScrollSpinBox()
        self.dpi_spin.setToolTip(get_tooltip_for("Batch compression DPI"))
        self.dpi_spin.setRange(50, 300)
        self.dpi_spin.setValue(120)
        self.dpi_spin.setSuffix(" DPI")
        form.addRow("Image DPI:", self.dpi_spin)
        return w

    def _build_text_watermark_options(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.wm_text_edit = QLineEdit("CONFIDENTIAL")
        form.addRow("Watermark Text:", self.wm_text_edit)
        self.wm_opacity_spin = NoScrollSpinBox()
        self.wm_opacity_spin.setToolTip(get_tooltip_for("Batch watermark opacity"))
        self.wm_opacity_spin.setRange(5, 80)
        self.wm_opacity_spin.setValue(25)
        self.wm_opacity_spin.setSuffix("% opacity")
        form.addRow("Opacity:", self.wm_opacity_spin)
        self.wm_font_size_spin = NoScrollSpinBox()
        self.wm_font_size_spin.setToolTip(get_tooltip_for("Batch watermark font size"))
        self.wm_font_size_spin.setRange(10, 200)
        self.wm_font_size_spin.setValue(64)
        self.wm_font_size_spin.setSuffix(" pt")
        form.addRow("Font Size:", self.wm_font_size_spin)
        self.wm_angle_spin = NoScrollSpinBox()
        self.wm_angle_spin.setToolTip(get_tooltip_for("Batch watermark rotation angle"))
        self.wm_angle_spin.setRange(0, 180)
        self.wm_angle_spin.setValue(45)
        self.wm_angle_spin.setSuffix("°")
        form.addRow("Rotation Angle:", self.wm_angle_spin)
        self.wm_color_combo = QComboBox()
        self.wm_color_combo.setToolTip(get_tooltip_for("Batch watermark color"))
        self.wm_color_combo.addItem("Red (CONFIDENTIAL)", (0.8, 0.0, 0.0))
        self.wm_color_combo.addItem("Dark Gray (DRAFT)", (0.3, 0.3, 0.3))
        self.wm_color_combo.addItem("Blue (FOR REVIEW)", (0.0, 0.0, 0.8))
        self.wm_color_combo.addItem("Green (APPROVED)", (0.0, 0.5, 0.0))
        form.addRow("Color:", self.wm_color_combo)
        return w

    def _build_image_watermark_options(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        img_row = QHBoxLayout()
        self.wm_img_edit = QLineEdit()
        self.wm_img_edit.setReadOnly(True)
        img_row.addWidget(self.wm_img_edit, stretch=1)
        browse_img_btn = QPushButton("Browse...")
        browse_img_btn.setToolTip(get_tooltip_for("Browse"))
        browse_img_btn.clicked.connect(self._choose_watermark_image)
        img_row.addWidget(browse_img_btn)
        form.addRow("Watermark Image:", img_row)
        self.wm_img_opacity_spin = NoScrollSpinBox()
        self.wm_img_opacity_spin.setToolTip(get_tooltip_for("Batch image watermark opacity"))
        self.wm_img_opacity_spin.setRange(5, 100)
        self.wm_img_opacity_spin.setValue(30)
        self.wm_img_opacity_spin.setSuffix("% opacity")
        form.addRow("Opacity:", self.wm_img_opacity_spin)
        self.wm_img_position_combo = QComboBox()
        self.wm_img_position_combo.setToolTip(get_tooltip_for("Batch image watermark position"))
        self.wm_img_position_combo.addItems(["center", "bottom-right", "bottom-left", "top-right", "top-left"])
        form.addRow("Position:", self.wm_img_position_combo)
        return w

    def _build_protect_options(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.pw_user_edit = QLineEdit()
        self.pw_user_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Open Password*:", self.pw_user_edit)
        self.pw_confirm_edit = QLineEdit()
        self.pw_confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Confirm Password*:", self.pw_confirm_edit)
        self.pw_owner_edit = QLineEdit()
        self.pw_owner_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Owner Password:", self.pw_owner_edit)
        self.pw_allow_print = QCheckBox("Allow printing")
        self.pw_allow_print.setToolTip(get_tooltip_for("Allow printing"))
        self.pw_allow_print.setChecked(True)
        form.addRow(self.pw_allow_print)
        return w

    def _on_mode_changed(self, index: int) -> None:
        self.options_stack.setCurrentIndex(index)

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select PDFs", "", "PDF Files (*.pdf)")
        for p in paths:
            item = QListWidgetItem(os.path.basename(p))
            item.setData(Qt.ItemDataRole.UserRole, p)
            item.setToolTip(p)
            self.list_widget.addItem(item)

    def _remove_selected(self) -> None:
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))

    def _choose_output_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if d:
            self.output_dir_edit.setText(d)

    def _choose_watermark_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Watermark Image", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if path:
            self.wm_img_edit.setText(path)

    def _paths(self) -> list[str]:
        return [self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list_widget.count())]

    def _start_batch(self) -> None:
        paths = self._paths()
        if not paths:
            QMessageBox.warning(self, "No files", "Add at least one PDF file.")
            return
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "Output folder", "Choose an output folder.")
            return

        mode = self.mode_combo.currentText()
        items = [pdf_ops.BatchPdfItem(input_path=p) for p in paths]
        fn: object
        args: tuple
        kwargs: dict

        if mode == "Compress":
            fn = pdf_ops.batch_compress_pdfs
            args = (items, output_dir)
            kwargs = {"dpi": self.dpi_spin.value(), "quality": self.quality_combo.currentText()}
        elif mode == "Watermark (Text)":
            fn = pdf_ops.batch_add_pdf_watermark
            args = (items, output_dir)
            kwargs = {
                "text": self.wm_text_edit.text(),
                "opacity": self.wm_opacity_spin.value() / 100.0,
                "font_size": self.wm_font_size_spin.value(),
                "color": self.wm_color_combo.currentData(),
                "angle": float(self.wm_angle_spin.value()),
            }
        elif mode == "Watermark (Image)":
            if not self.wm_img_edit.text():
                QMessageBox.warning(self, "Image required", "Choose a watermark image.")
                return
            fn = pdf_ops.batch_add_image_watermark
            args = (items, output_dir, self.wm_img_edit.text())
            kwargs = {
                "opacity": self.wm_img_opacity_spin.value() / 100.0,
                "position": self.wm_img_position_combo.currentText(),
            }
        else:  # Protect (Password)
            user_pwd = self.pw_user_edit.text()
            if not user_pwd:
                QMessageBox.warning(self, "Password required", "Enter a password.")
                return
            if user_pwd != self.pw_confirm_edit.text():
                QMessageBox.warning(self, "Passwords do not match", "The passwords you entered do not match.")
                return
            fn = pdf_ops.batch_protect_pdfs
            args = (items, output_dir)
            kwargs = {
                "user_password": user_pwd,
                "owner_password": self.pw_owner_edit.text() or None,
                "allow_printing": self.pw_allow_print.isChecked(),
            }

        self.items = items
        self.progress_bar.setMaximum(len(items))
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)
        self.mode_combo.setEnabled(False)

        self._worker = WorkerThread(fn, *args, **kwargs)
        self._worker.progress.connect(lambda current, total, message: self.progress_bar.setValue(current))
        self._worker.finished_ok.connect(self._on_batch_ok)
        self._worker.failed.connect(self._on_batch_failed)
        self._worker.start()

    def _refresh_item_statuses(self) -> None:
        for row, item in enumerate(self.items):
            list_item = self.list_widget.item(row)
            if list_item is None:
                continue
            if item.status == "done":
                list_item.setForeground(Qt.GlobalColor.green)
                list_item.setToolTip(item.output_path or item.input_path)
            elif item.status == "failed":
                list_item.setForeground(Qt.GlobalColor.red)
                list_item.setToolTip(item.error or item.input_path)

    def _on_batch_ok(self, results: list[pdf_ops.BatchPdfItem]) -> None:
        self.start_btn.setEnabled(True)
        self.mode_combo.setEnabled(True)
        self._refresh_item_statuses()
        done_count = sum(1 for item in results if item.status == "done")
        QMessageBox.information(
            self, "Batch Complete", f"Successfully processed {done_count} of {len(results)} file(s)."
        )

    def _on_batch_failed(self, error: str) -> None:
        self.start_btn.setEnabled(True)
        self.mode_combo.setEnabled(True)
        QMessageBox.critical(self, "Batch Error", f"Batch processing error: {error}")


def _samples_to_qimage(width: int, height: int, samples: bytes) -> QImage:
    return QImage(samples, width, height, width * 3, QImage.Format.Format_RGB888)


class PdfTab(QWidget):
    def __init__(self, parent: QWidget | None = None, settings: QSettings | None = None) -> None:
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings("FOSSEverything", "FOSSEverything")
        self.doc = None
        self.current_path = None
        self.current_page = 0
        self.zoom = 4.0
        self._progress_dialog = None
        self._worker = None
        self._page_worker = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        toolbar = AppToolBar(self.settings, "pdf_toolbar")
        self.toolbar = toolbar
        layout.addWidget(toolbar)

        toolbar.add_action("Open", self.open_pdf, tooltip_key="Open PDF")
        toolbar.add_action("Save As...", self.save_as, tooltip_key="Save As")
        toolbar.addSeparator()

        toolbar.add_action("Undo", self._undo, shortcut=QKeySequence.StandardKey.Undo)
        toolbar.add_action("Redo", self._redo, shortcut=QKeySequence("Ctrl+Y"))
        toolbar.add_action("Delete", self._delete_selected)
        toolbar.addSeparator()

        self.canvas = AnnotationCanvas()
        self.canvas.fit_mode = "width"  # like a browser: fill the width, scroll for the rest of the page
        self.canvas.text_provider = self._selected_text_and_rects
        self.canvas.selection_changed.connect(self._on_selection_changed)
        self.canvas.visible_page_changed.connect(self._on_visible_page_changed)

        self.tool_group = QActionGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_actions = {}
        for label, tool in [
            ("Select", Tool.SELECT),
            ("Rect", Tool.RECT),
            ("Highlight", Tool.HIGHLIGHT),
            ("Text", Tool.TEXT),
            ("Freehand", Tool.FREEHAND),
            ("Arrow", Tool.ARROW),
            ("Redact", Tool.REDACT),
        ]:
            action = QAction(label, self)
            if label == "Select":
                action.setToolTip(get_tooltip_for("Select tool"))
            elif label == "Rect":
                action.setToolTip(get_tooltip_for("Rect tool"))
            elif label == "Highlight":
                action.setToolTip(get_tooltip_for("Highlight"))
            elif label == "Text":
                action.setToolTip(get_tooltip_for("Text tool"))
            elif label == "Freehand":
                action.setToolTip(get_tooltip_for("Freehand tool"))
            elif label == "Arrow":
                action.setToolTip(get_tooltip_for("Arrow tool"))
            elif label == "Redact":
                action.setToolTip(get_tooltip_for("Redact"))
            action.setCheckable(True)
            action.triggered.connect(lambda checked, t=tool: self.canvas.set_tool(t))
            self.tool_group.addAction(action)
            toolbar.addAction(action)
            self.tool_actions[tool] = action
        self.tool_actions[Tool.SELECT].setChecked(True)

        self.box_select_action = toolbar.add_action(
            "Box Select", checkable=True, tooltip_key="Box select"
        )
        self.box_select_action.toggled.connect(self.canvas.set_text_select_box_mode)
        toolbar.addSeparator()

        toolbar.add_action("Color...", lambda: self.canvas.prompt_and_apply_color(self), tooltip_key="Color")

        toolbar.addWidget(QLabel(" Font: "))
        self.font_family_combo = QFontComboBox()
        self.font_family_combo.setMaximumWidth(160)
        # QFontComboBox.setCurrentFont() triggers a full system font-database match on
        # first call, costing 1s+ on Windows; defer it off the synchronous startup path.
        QTimer.singleShot(0, lambda: self.font_family_combo.setCurrentFont(QFont("Helvetica", scaled_font_size(10))))
        self.font_family_combo.currentFontChanged.connect(lambda qfont: self.canvas.apply_font_family(qfont.family()))
        toolbar.addWidget(self.font_family_combo)

        toolbar.addWidget(QLabel(" Size: "))
        self.font_size_spin = NoScrollSpinBox()
        self.font_size_spin.setToolTip(get_tooltip_for("Annotation font size"))
        self.font_size_spin.setRange(4, 200)
        self.font_size_spin.setValue(14)
        self.font_size_spin.valueChanged.connect(self._font_size_changed)
        toolbar.addWidget(self.font_size_spin)

        self.bold_action = toolbar.add_action("Bold", checkable=True)
        self.bold_action.toggled.connect(self._bold_toggled)
        self.italic_action = toolbar.add_action("Italic", checkable=True)
        self.italic_action.toggled.connect(self._italic_toggled)

        toolbar.addWidget(QLabel(" Char spacing: "))
        self.letter_spacing_spin = NoScrollSpinBox()
        self.letter_spacing_spin.setToolTip(get_tooltip_for("Annotation letter spacing"))
        self.letter_spacing_spin.setRange(50, 300)
        self.letter_spacing_spin.setValue(100)
        self.letter_spacing_spin.setSuffix("%")
        self.letter_spacing_spin.valueChanged.connect(self._letter_spacing_changed)
        toolbar.addWidget(self.letter_spacing_spin)
        toolbar.addSeparator()

        toolbar.add_action("Zoom In", lambda: self.canvas.zoom_in(), shortcut=QKeySequence("Ctrl+="))
        toolbar.add_action("Zoom Out", lambda: self.canvas.zoom_out(), shortcut=QKeySequence("Ctrl+-"))
        toolbar.add_action("Fit", lambda: self.canvas.zoom_reset(), shortcut=QKeySequence("Ctrl+0"))
        toolbar.add_action("Shortcuts", lambda: show_shortcuts_dialog(self))
        toolbar.addSeparator()

        toolbar.add_action("Merge...", self.merge_pdfs, tooltip_key="Merge PDFs")
        toolbar.add_action("Split...", self.split_pdf, tooltip_key="Split PDF")
        toolbar.add_action("Break into Pages...", self.break_into_pages, tooltip_key="Break into pages")
        toolbar.add_action("Organize Pages...", self.organize_pages, tooltip_key="Organize pages")
        toolbar.add_action("Compress...", self.compress_pdf, tooltip_key="Compress PDF")
        toolbar.add_action("Export Pages...", self.export_pages, tooltip_key="Export PDF pages")
        toolbar.add_action("Batch Process...", self.batch_process, tooltip_key="Batch process PDFs")
        toolbar.addSeparator()

        toolbar.add_action("Protect...", self.protect_pdf, tooltip_key="Protect PDF")
        toolbar.add_action("Unlock...", self.unlock_pdf, tooltip_key="Unlock PDF")
        toolbar.addSeparator()

        toolbar.add_action("Watermark...", self.add_watermark, tooltip_key="Watermark PDF")
        toolbar.add_action("Page Numbers...", self.add_page_numbers, tooltip_key="Page numbers")
        toolbar.add_action("Extract Text...", self.extract_text, tooltip_key="Extract text from PDF")
        toolbar.add_action("Make Searchable (OCR)...", self.make_searchable_pdf, tooltip_key="Make Searchable PDF")
        toolbar.add_action("Convert to Word (DOCX)...", self.convert_to_docx)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        nav_widget = QWidget()
        nav_widget.setObjectName("Page Navigation")
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(4, 0, 4, 0)
        nav_layout.setSpacing(4)
        self.status_label = QLabel("No file open")
        nav_layout.addWidget(self.status_label)
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setToolTip(get_tooltip_for("Previous page"))
        self.next_btn = QPushButton("▶")
        self.next_btn.setToolTip(get_tooltip_for("Next page"))
        self.page_spin = NoScrollSpinBox()
        self.page_spin.setToolTip(get_tooltip_for("Go to page"))
        self.page_spin.setMinimum(1)
        self.page_label = QLabel("/ 0")
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)
        self.page_spin.valueChanged.connect(self._goto_from_spin)
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.page_spin)
        nav_layout.addWidget(self.page_label)
        nav_layout.addWidget(self.next_btn)
        toolbar.addWidget(nav_widget)

        toolbar.finalize()

        layout.addWidget(self.canvas, stretch=1)

    def _undo(self) -> None:
        self.canvas.undo()

    def _redo(self) -> None:
        self.canvas.redo()

    def _delete_selected(self) -> None:
        self.canvas.delete_selected()

    def _font_size_changed(self, value: int) -> None:
        self.canvas.apply_font_size(value)

    def _bold_toggled(self, checked: bool) -> None:
        self.canvas.apply_bold(checked)

    def _italic_toggled(self, checked: bool) -> None:
        self.canvas.apply_italic(checked)

    def _letter_spacing_changed(self, value: int) -> None:
        self.canvas.apply_letter_spacing(value)

    def _on_visible_page_changed(self, index: int) -> None:
        self.current_page = index
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(index + 1)
        self.page_spin.blockSignals(False)

    def _on_selection_changed(self, item: QGraphicsItem | None) -> None:
        if isinstance(item, ResizableTextItem):
            font = item.font()
            for widget, value in (
                (self.font_size_spin, item.font_size()),
                (self.letter_spacing_spin, item.letter_spacing),
            ):
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)
            self.font_family_combo.blockSignals(True)
            self.font_family_combo.setCurrentFont(QFont(item.font_family, scaled_font_size(10)))
            self.font_family_combo.blockSignals(False)
            self.bold_action.blockSignals(True)
            self.bold_action.setChecked(font.bold())
            self.bold_action.blockSignals(False)
            self.italic_action.blockSignals(True)
            self.italic_action.setChecked(font.italic())
            self.italic_action.blockSignals(False)

    # ---------- file loading ----------

    def open_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if not path:
            return
        self.load_file(path)

    def load_file(self, path: str) -> None:
        self.doc = pdf_ops.open_pdf(path)
        self.current_path = path
        self.current_page = 0
        self.page_spin.blockSignals(True)
        self.page_spin.setMaximum(max(1, pdf_ops.page_count(self.doc)))
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)
        self.page_label.setText(f"/ {pdf_ops.page_count(self.doc)}")
        self._render_all_pages()
        self.status_label.setText(os.path.basename(path))

    def _render_all_pages(self) -> None:
        """Render the first page immediately so the document appears right
        away (like a browser's PDF viewer), then render the rest of the pages
        in the background and append them as they finish."""
        if self.doc is None:
            return
        total = pdf_ops.page_count(self.doc)
        if total == 0:
            return
        width, height, samples = pdf_ops.render_page(self.doc, 0, self.zoom)
        self.canvas.set_pages([_samples_to_qimage(width, height, samples)])
        if total == 1:
            return
        self._page_worker = WorkerThread(self._render_pages_range, self.current_path, 1, total, self.zoom)
        self._page_worker.finished_ok.connect(self._on_remaining_pages_rendered)
        self._page_worker.failed.connect(self._on_remaining_pages_failed)
        self._page_worker.start()

    @staticmethod
    def _render_pages_range(path: str, start: int, end: int, zoom: float) -> list[QImage]:
        # A fresh Document, not self.doc: PyMuPDF documents aren't safe to
        # share across threads, so background rendering opens its own handle.
        images = []
        with pdf_ops.open_pdf(path) as doc:
            for page_num in range(start, end):
                width, height, samples = pdf_ops.render_page(doc, page_num, zoom)
                images.append(_samples_to_qimage(width, height, samples))
        return images

    def _on_remaining_pages_rendered(self, images: list[QImage]) -> None:
        self.canvas.append_pages(images)

    def _on_remaining_pages_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Render failed", f"Couldn't render the rest of the document: {message}")

    def _selected_text_and_rects(self, start: QPointF, end: QPointF, box_mode: bool) -> tuple[str, list[QRectF]]:
        if box_mode:
            return self._text_in_rect(QRectF(start, end).normalized())
        return self._text_in_line_flow(start, end)

    def _text_in_rect(self, rect: QRectF) -> tuple[str, list[QRectF]]:
        if self.doc is None:
            return "", []
        texts = []
        word_rects = []
        for page_num, (top, height) in enumerate(self.canvas.page_boundaries):
            y0 = max(rect.top(), top)
            y1 = min(rect.bottom(), top + height)
            if y1 <= y0:
                continue
            pdf_rect = (
                rect.x() / self.zoom, (y0 - top) / self.zoom,
                (rect.x() + rect.width()) / self.zoom, (y1 - top) / self.zoom,
            )
            text, words = pdf_ops.text_in_rect(self.doc, page_num, pdf_rect)
            if text:
                texts.append(text)
            for x0, wy0, x1, wy1 in words:
                word_rects.append(QRectF(
                    x0 * self.zoom, top + wy0 * self.zoom,
                    (x1 - x0) * self.zoom, (wy1 - wy0) * self.zoom,
                ))
        return "\n".join(texts), word_rects

    def _scene_point_to_page(self, point: QPointF) -> tuple[int, float, float]:
        """Map a continuous-scroll scene point to (page_index, pdf_x, pdf_y)."""
        boundaries = self.canvas.page_boundaries
        for index, (top, height) in enumerate(boundaries):
            if point.y() < top + height:
                return index, point.x() / self.zoom, (point.y() - top) / self.zoom
        index = max(0, len(boundaries) - 1)
        top = boundaries[index][0] if boundaries else 0.0
        return index, point.x() / self.zoom, (point.y() - top) / self.zoom

    def _text_in_line_flow(self, start: QPointF, end: QPointF) -> tuple[str, list[QRectF]]:
        """Word-processor-style selection: flows through text from `start` to
        `end` in reading order, across pages if the drag spans more than one."""
        if self.doc is None or not self.canvas.page_boundaries:
            return "", []
        start_page, start_x, start_y = self._scene_point_to_page(start)
        end_page, end_x, end_y = self._scene_point_to_page(end)
        if (start_page, start_y, start_x) > (end_page, end_y, end_x):
            start_page, end_page = end_page, start_page
            start_x, end_x = end_x, start_x
            start_y, end_y = end_y, start_y

        texts = []
        word_rects = []
        for page_num in range(start_page, end_page + 1):
            top = self.canvas.page_boundaries[page_num][0]
            sx = sy = ex = ey = None
            if page_num == start_page:
                sx, sy = start_x, start_y
            if page_num == end_page:
                ex, ey = end_x, end_y
            text, words = pdf_ops.text_in_line_range(self.doc, page_num, sx, sy, ex, ey)
            if text:
                texts.append(text)
            for x0, wy0, x1, wy1 in words:
                word_rects.append(QRectF(
                    x0 * self.zoom, top + wy0 * self.zoom,
                    (x1 - x0) * self.zoom, (wy1 - wy0) * self.zoom,
                ))
        return "\n".join(texts), word_rects

    def prev_page(self) -> None:
        if self.doc is None or self.current_page <= 0:
            return
        self.canvas.scroll_to_page(self.current_page - 1)

    def next_page(self) -> None:
        if self.doc is None or self.current_page >= pdf_ops.page_count(self.doc) - 1:
            return
        self.canvas.scroll_to_page(self.current_page + 1)

    def _goto_from_spin(self, value: int) -> None:
        if self.doc is None:
            return
        self.canvas.scroll_to_page(value - 1)

    # ---------- save / annotation baking ----------

    def save_as(self) -> None:
        if self.doc is None:
            QMessageBox.warning(self, "No document", "Open a PDF first.")
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Save PDF As", "", "PDF Files (*.pdf)")
        if not out_path:
            return
        boundaries = self.canvas.page_boundaries
        by_page: dict[int, list[dict]] = {}
        for ann in self.canvas.get_annotations():
            page_num = self._page_index_for_y(self._annotation_top_y(ann), boundaries)
            offset = boundaries[page_num][0] if boundaries else 0.0
            scaled = self._scale_annotation(self._shift_annotation(ann, -offset), 1.0 / self.zoom)
            by_page.setdefault(page_num, []).append(scaled)
        for page_num, anns in by_page.items():
            pdf_ops.bake_annotations(self.doc, page_num, anns)
        if by_page:
            self.canvas.clear_annotations()
        pdf_ops.save_annotated_pdf(self.doc, out_path)
        QMessageBox.information(self, "Saved", f"Saved to {out_path}")

    @staticmethod
    def _annotation_top_y(ann: dict) -> float:
        """The scene y-coordinate that pins an annotation to a page, used to
        bucket continuous-scroll annotations back into per-page groups."""
        if "rect" in ann:
            return ann["rect"][1]
        if "pos" in ann:
            return ann["pos"][1]
        if "points" in ann and ann["points"]:
            return ann["points"][0][1]
        if "start" in ann:
            return ann["start"][1]
        return 0.0

    @staticmethod
    def _page_index_for_y(y: float, boundaries: list[tuple[float, float]]) -> int:
        for index, (top, height) in enumerate(boundaries):
            if y < top + height:
                return index
        return max(0, len(boundaries) - 1)

    @staticmethod
    def _shift_annotation(ann: dict, dy: float) -> dict:
        """Move an annotation from continuous-scroll scene coords to
        page-local coords by subtracting that page's vertical offset."""
        ann = dict(ann)
        if "rect" in ann:
            x, y, w, h = ann["rect"]
            ann["rect"] = (x, y + dy, w, h)
        if "pos" in ann:
            x, y = ann["pos"]
            ann["pos"] = (x, y + dy)
        if "points" in ann:
            ann["points"] = [(x, y + dy) for x, y in ann["points"]]
        if "start" in ann:
            x, y = ann["start"]
            ann["start"] = (x, y + dy)
        if "end" in ann:
            x, y = ann["end"]
            ann["end"] = (x, y + dy)
        return ann

    @staticmethod
    def _scale_annotation(ann: dict, factor: float) -> dict:
        ann = dict(ann)
        if "rect" in ann:
            x, y, w, h = ann["rect"]
            ann["rect"] = (x * factor, y * factor, w * factor, h * factor)
        if "pos" in ann:
            x, y = ann["pos"]
            ann["pos"] = (x * factor, y * factor)
        if "points" in ann:
            ann["points"] = [(x * factor, y * factor) for x, y in ann["points"]]
        if "start" in ann:
            x, y = ann["start"]
            ann["start"] = (x * factor, y * factor)
        if "end" in ann:
            x, y = ann["end"]
            ann["end"] = (x * factor, y * factor)
        return ann

    def export_pages(self) -> None:
        """Write all source PDF pages to numbered images in a worker thread."""
        if self.current_path is None:
            QMessageBox.warning(self, "No document", "Open a PDF first.")
            return
        dialog = ExportPagesDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        target_format, dpi = dialog.values()
        output_dir = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if not output_dir:
            return
        self._progress_dialog = QProgressDialog("Exporting PDF pages...", None, 0, pdf_ops.page_count(self.doc), self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()
        self._worker = WorkerThread(pdf_ops.export_pdf_pages, self.current_path, output_dir, target_format, dpi)
        self._worker.progress.connect(lambda current, total, message: self._progress_dialog.setValue(current))
        self._worker.finished_ok.connect(self._on_export_pages_done)
        self._worker.failed.connect(self._on_export_pages_failed)
        self._worker.start()

    def _on_export_pages_done(self, outputs: list[str]) -> None:
        self._progress_dialog.close()
        QMessageBox.information(self, "Export complete", f"Wrote {len(outputs)} page image(s).")

    def _on_export_pages_failed(self, message: str) -> None:
        self._progress_dialog.close()
        QMessageBox.critical(self, "Export failed", message)

    # ---------- merge / split / compress ----------

    def merge_pdfs(self) -> None:
        dialog = MergeDialog(self, initial_path=self.current_path)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        paths = dialog.get_paths()
        if len(paths) < 2:
            QMessageBox.warning(self, "Need more files", "Add at least two PDFs to merge.")
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Merged PDF", "", "PDF Files (*.pdf)")
        if not out_path:
            return
        try:
            pdf_ops.merge_pdfs(paths, out_path)
            QMessageBox.information(self, "Merged", f"Saved merged PDF to {out_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Merge failed", str(exc))

    def split_pdf(self) -> None:
        if self.current_path is None:
            QMessageBox.warning(self, "No document", "Open a PDF first.")
            return
        dialog = SplitDialog(pdf_ops.page_count(self.doc), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            ranges = dialog.parsed_ranges()
        except ValueError:
            QMessageBox.warning(self, "Invalid input", "Use a format like 1-3,5,7-9")
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if not out_dir:
            return
        try:
            outputs = pdf_ops.split_pdf(self.current_path, ranges, out_dir)
            QMessageBox.information(self, "Split complete", f"Wrote {len(outputs)} file(s).")
        except Exception as exc:
            QMessageBox.critical(self, "Split failed", str(exc))

    def break_into_pages(self) -> None:
        start_dir = os.path.dirname(self.current_path) if self.current_path else ""
        paths, _ = QFileDialog.getOpenFileNames(self, "Select PDF(s) to Break into Pages", start_dir, "PDF Files (*.pdf)")
        if not paths:
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if not out_dir:
            return
        try:
            written = sum(len(pdf_ops.break_pdf_into_pages(p, out_dir)) for p in paths)
            QMessageBox.information(self, "Split complete", f"Wrote {written} single-page file(s).")
        except Exception as exc:
            QMessageBox.critical(self, "Split failed", str(exc))

    def compress_pdf(self) -> None:
        if self.current_path is None:
            QMessageBox.warning(self, "No document", "Open a PDF first.")
            return
        dialog = CompressDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        quality, dpi = dialog.values()
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Compressed PDF", "", "PDF Files (*.pdf)")
        if not out_path:
            return

        self._progress_dialog = QProgressDialog("Compressing...", None, 0, 0, self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()

        self._worker = WorkerThread(pdf_ops.compress_pdf, self.current_path, out_path, dpi, quality)
        self._worker.finished_ok.connect(self._on_compress_done)
        self._worker.failed.connect(self._on_compress_failed)
        self._worker.start()

    def _on_compress_done(self, result: str) -> None:
        self._progress_dialog.close()
        QMessageBox.information(self, "Compressed", f"Saved to {result}")

    def _on_compress_failed(self, message: str) -> None:
        self._progress_dialog.close()
        QMessageBox.critical(self, "Compression failed", message)

    def batch_process(self) -> None:
        """Open the batch dialog to compress, watermark, or protect multiple PDFs at once."""
        dialog = BatchDialog(self)
        dialog.exec()

    def organize_pages(self) -> None:
        if self.current_path is None:
            QMessageBox.warning(self, "No document", "Open a PDF first.")
            return
        total = pdf_ops.page_count(self.doc)
        dialog = PageOrganizerDialog(total, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        ops = dialog.page_operations()
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Organized PDF", "", "PDF Files (*.pdf)")
        if not out_path:
            return
        try:
            pdf_ops.reorganize_pdf_pages(self.current_path, out_path, ops)
            QMessageBox.information(self, "Pages Organized", f"Saved organized PDF to {out_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Organization failed", str(exc))

    def protect_pdf(self) -> None:
        target_path = self.current_path
        if target_path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Select PDF to Protect", "", "PDF Files (*.pdf)")
            if not path:
                return
            target_path = path
        dialog = ProtectDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        user_pwd, owner_pwd, allow_print = dialog.values()
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Protected PDF", "", "PDF Files (*.pdf)")
        if not out_path:
            return
        try:
            pdf_ops.protect_pdf(target_path, out_path, user_pwd, owner_pwd, allow_print)
            QMessageBox.information(self, "PDF Protected", f"Password-protected PDF saved to {out_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Protection failed", str(exc))

    def unlock_pdf(self) -> None:
        target_path = self.current_path
        if target_path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Select Encrypted PDF to Unlock", "", "PDF Files (*.pdf)")
            if not path:
                return
            target_path = path
        dialog = UnlockDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        pwd = dialog.password()
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Unlocked PDF", "", "PDF Files (*.pdf)")
        if not out_path:
            return
        try:
            pdf_ops.unlock_pdf(target_path, out_path, pwd)
            QMessageBox.information(self, "PDF Unlocked", f"Decrypted PDF saved to {out_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Unlock failed", str(exc))

    def add_watermark(self) -> None:
        """Add a text watermark to the current PDF."""
        target_path = self.current_path
        if target_path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Select PDF to Watermark", "", "PDF Files (*.pdf)")
            if not path:
                return
            target_path = path
        dialog = WatermarkDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        text, opacity, font_size, color, angle = dialog.values()
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Watermarked PDF", "", "PDF Files (*.pdf)")
        if not out_path:
            return
        try:
            pdf_ops.add_pdf_watermark(target_path, out_path, text=text, opacity=opacity,
                                      font_size=font_size, color=color, angle=angle)
            QMessageBox.information(self, "Watermark Applied", f"Watermarked PDF saved to {out_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Watermark failed", str(exc))

    def extract_text(self) -> None:
        """Extract text from the current PDF to a file (direct or OCR)."""
        target_path = self.current_path
        if target_path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Select PDF to Extract Text From", "", "PDF Files (*.pdf)")
            if not path:
                return
            target_path = path
        dialog = TextExtractDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        mode, _use_sep, use_ocr, ocr_lang = dialog.values()
        ext = ".md" if mode == "markdown" else ".txt"
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Extracted Text", "",
            "Markdown Files (*.md);;Text Files (*.txt);;All Files (*.*)" if mode == "markdown"
            else "Text Files (*.txt);;Markdown Files (*.md);;All Files (*.*)"
        )
        if not out_path:
            return
        self._progress_dialog = QProgressDialog(
            "Running OCR..." if use_ocr else "Extracting text...", None, 0, 0, self
        )
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()
        self._worker = WorkerThread(self._do_extract_text, target_path, out_path, mode, use_ocr, ocr_lang)
        self._worker.finished_ok.connect(self._on_extract_text_done)
        self._worker.failed.connect(self._on_extract_text_failed)
        self._worker.start()

    @staticmethod
    def _do_extract_text(target_path: str, out_path: str, mode: str, use_ocr: bool, ocr_lang: str) -> str:
        if use_ocr:
            from app.features.ocr import ops as ocr_ops  # noqa: 13 (keeps PIL out of every PDF tab's cold-start import)
            res = ocr_ops.ocr_pdf(target_path, language=ocr_lang or "eng")
            ocr_ops.save_ocr_text(res, out_path, as_markdown=(mode == "markdown"))
        else:
            pdf_ops.save_pdf_text(target_path, out_path, mode=mode)
        return out_path

    def _on_extract_text_done(self, out_path: str) -> None:
        self._progress_dialog.close()
        QMessageBox.information(self, "Text Extracted", f"Text content extracted to {out_path}")

    def _on_extract_text_failed(self, message: str) -> None:
        self._progress_dialog.close()
        QMessageBox.critical(self, "Extraction failed", message)

    def make_searchable_pdf(self) -> None:
        """Generate a searchable PDF from a scanned PDF using local OCR."""
        target_path = self.current_path
        if target_path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Select PDF to Make Searchable", "", "PDF Files (*.pdf)")
            if not path:
                return
            target_path = path
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Searchable PDF", "", "PDF Files (*.pdf)")
        if not out_path:
            return
        from app.features.ocr import ops as ocr_ops  # noqa: 13 (keeps PIL out of every PDF tab's cold-start import)
        self._progress_dialog = QProgressDialog("Running OCR...", None, 0, 0, self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()
        self._worker = WorkerThread(ocr_ops.create_searchable_pdf, target_path, out_path, language="eng")
        self._worker.finished_ok.connect(self._on_searchable_pdf_done)
        self._worker.failed.connect(self._on_searchable_pdf_failed)
        self._worker.start()

    def _on_searchable_pdf_done(self, out_path: str) -> None:
        self._progress_dialog.close()
        QMessageBox.information(self, "Searchable PDF Created", f"Searchable PDF saved to {out_path}")

    def _on_searchable_pdf_failed(self, message: str) -> None:
        self._progress_dialog.close()
        QMessageBox.critical(self, "Searchable PDF creation failed", message)

    def convert_to_docx(self) -> None:
        """Convert the current PDF to an editable Word document, running local OCR first if it is scanned."""
        target_path = self.current_path
        if target_path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Select PDF to Convert", "", "PDF Files (*.pdf)")
            if not path:
                return
            target_path = path
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Word Document", "", "Word Document (*.docx)")
        if not out_path:
            return
        self._progress_dialog = QProgressDialog("Converting to Word...", None, 0, 0, self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()
        self._worker = WorkerThread(self._do_convert_to_docx, target_path, out_path)
        self._worker.progress.connect(lambda current, total, message: self._progress_dialog.setLabelText(message))
        self._worker.finished_ok.connect(self._on_convert_docx_done)
        self._worker.failed.connect(self._on_convert_docx_failed)
        self._worker.start()

    @staticmethod
    def _do_convert_to_docx(
        target_path: str, out_path: str, progress_cb: Optional[Callable[[int, int, str], None]] = None
    ) -> tuple[str, bool]:
        needed_ocr = pdf_ops.pdf_needs_ocr(target_path)
        pdf_ops.convert_scanned_pdf_to_docx(target_path, out_path, progress_cb=progress_cb)
        return out_path, needed_ocr

    def _on_convert_docx_done(self, result: tuple[str, bool]) -> None:
        out_path, needed_ocr = result
        self._progress_dialog.close()
        message = f"Word document saved to {out_path}"
        if needed_ocr:
            message += "\n\nThis PDF had no text layer; local OCR recovered the text."
        QMessageBox.information(self, "Converted to Word", message)

    def _on_convert_docx_failed(self, message: str) -> None:
        self._progress_dialog.close()
        QMessageBox.critical(self, "Conversion failed", message)


    def add_page_numbers(self) -> None:
        """Stamp page numbers or header/footer labels on the PDF."""
        target_path = self.current_path
        if target_path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Select PDF for Page Numbering", "", "PDF Files (*.pdf)")
            if not path:
                return
            target_path = path
        try:
            total_pages = pdf_ops.page_count(pdf_ops.open_pdf(target_path))
        except Exception:
            total_pages = 1
        dialog = PageNumberDialog(total_pages, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        format_str, pos, font_size, margin, start_num = dialog.values()
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Numbered PDF", "", "PDF Files (*.pdf)")
        if not out_path:
            return
        try:
            pdf_ops.add_page_numbers(
                target_path, out_path,
                format_str=format_str,
                position=pos,
                font_size=font_size,
                margin_x=margin,
                margin_y=margin,
                start_num=start_num,
            )
            QMessageBox.information(self, "Page Numbers Added", f"Numbered PDF saved to {out_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Page numbering failed", str(exc))

