"""Image Collage Builder workspace: grid-compose multiple images locally."""
from __future__ import annotations

import os
from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QGuiApplication, QPalette
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QPushButton, QLabel, QFileDialog, QMessageBox, QListWidget,
    QListWidgetItem, QGroupBox, QColorDialog, QCheckBox, QSplitter, QProgressDialog
)
from PIL import Image

from app.core.customizable_toolbar import AppToolBar
from app.core.spinbox import NoScrollSpinBox
from app.features.collage import ops as collage_ops
from app.core.theme import resolved_palette, theme_signals
from app.core.tooltips import get_tooltip_for
from app.system.workers import WorkerThread


def _pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    pil_img = pil_img.convert("RGB")
    raw = pil_img.tobytes("raw", "RGB")
    qimg = QImage(raw, pil_img.width, pil_img.height, pil_img.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg)


class CollageTab(QWidget):
    """Compose multiple images into a grid collage locally."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.bg_color = (240, 240, 240)
        self.current_collage = None
        self._build_ui()
        theme_signals.changed.connect(self._refresh_theme_colors)

    def _refresh_theme_colors(self) -> None:
        self.size_label.setStyleSheet(f"color: {resolved_palette()['muted']};")

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Image Collage Builder")
        title.setStyleSheet("font-weight: 700;")
        root.addWidget(title)
        root.addWidget(QLabel("Arrange multiple images into a grid. Export as PNG, JPEG, or WEBP."))

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)

        img_group = QGroupBox("Images")
        img_layout = QVBoxLayout(img_group)

        btn_row = AppToolBar(None, "collage_images_toolbar")
        btn_row.add_action("Add Images...", self._add_images, tooltip_key="Add Images")
        btn_row.add_action("Remove Selected", self._remove_selected, tooltip_key="Remove Selected")
        btn_row.add_action("Clear All", self._clear_images, tooltip_key="Clear All")
        btn_row.finalize()
        img_layout.addWidget(btn_row)

        self.image_list = QListWidget()
        self.image_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.image_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        img_layout.addWidget(self.image_list)
        left_layout.addWidget(img_group)

        grid_group = QGroupBox("Layout Settings")
        grid_form = QFormLayout(grid_group)

        self.layout_combo = QComboBox()
        self.layout_combo.setToolTip(get_tooltip_for("Layout"))
        self.layout_combo.addItems(list(collage_ops.LAYOUT_PRESETS.keys()))
        self.layout_combo.currentIndexChanged.connect(self._on_layout_changed)
        grid_form.addRow("Layout:", self.layout_combo)

        self.cols_spin = NoScrollSpinBox()
        self.cols_spin.setToolTip(get_tooltip_for("Columns"))
        self.cols_spin.setRange(1, 10)
        self.cols_spin.setValue(2)
        grid_form.addRow("Columns:", self.cols_spin)

        self.cell_w_spin = NoScrollSpinBox()
        self.cell_w_spin.setToolTip(get_tooltip_for("Cell Width"))
        self.cell_w_spin.setRange(50, 2000)
        self.cell_w_spin.setValue(400)
        self.cell_w_spin.setSuffix(" px")
        grid_form.addRow("Cell Width:", self.cell_w_spin)

        self.cell_h_spin = NoScrollSpinBox()
        self.cell_h_spin.setToolTip(get_tooltip_for("Cell Height"))
        self.cell_h_spin.setRange(50, 2000)
        self.cell_h_spin.setValue(400)
        self.cell_h_spin.setSuffix(" px")
        grid_form.addRow("Cell Height:", self.cell_h_spin)

        self.padding_spin = NoScrollSpinBox()
        self.padding_spin.setToolTip(get_tooltip_for("Padding"))
        self.padding_spin.setRange(0, 100)
        self.padding_spin.setValue(12)
        self.padding_spin.setSuffix(" px")
        grid_form.addRow("Padding:", self.padding_spin)

        self.fit_combo = QComboBox()
        self.fit_combo.setToolTip(get_tooltip_for("Fit Mode"))
        self.fit_combo.addItems(["cover", "contain", "stretch"])
        grid_form.addRow("Fit Mode:", self.fit_combo)

        self.bg_btn = QPushButton("Pick Background Color")
        self.bg_btn.setToolTip(get_tooltip_for("Pick Background Color"))
        self.bg_btn.clicked.connect(self._pick_bg_color)
        grid_form.addRow("Background:", self.bg_btn)

        left_layout.addWidget(grid_group)

        self.captions_check = QCheckBox("Add filenames as captions")
        self.captions_check.setToolTip(get_tooltip_for("Add filenames as captions"))
        left_layout.addWidget(self.captions_check)

        gen_btn = QPushButton("Generate Collage Preview")
        gen_btn.setToolTip(get_tooltip_for("Generate Collage Preview"))
        gen_btn.setStyleSheet("font-weight: 700; padding: 10px;")
        gen_btn.clicked.connect(self._generate_collage)
        left_layout.addWidget(gen_btn)

        splitter.addWidget(left_panel)

        # Right: preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)

        preview_label_head = QLabel("Collage Preview")
        preview_label_head.setStyleSheet("font-weight: 700;")
        right_layout.addWidget(preview_label_head)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        palette = self.palette()
        self.preview_label.setStyleSheet(
            f"background: {palette.color(QPalette.ColorRole.Base).name()}; "
            f"border: 1px solid {palette.color(QPalette.ColorRole.Mid).name()}; border-radius: 8px;"
        )
        self.preview_label.setMinimumSize(300, 300)
        self.preview_label.setText("Add images and click Generate Collage Preview")
        right_layout.addWidget(self.preview_label, stretch=1)

        save_row = QHBoxLayout()
        self.save_btn = QPushButton("Save Collage...")
        self.save_btn.setToolTip(get_tooltip_for("Save Collage"))
        self.save_btn.setStyleSheet("font-weight: 600; padding: 8px 16px;")
        self.save_btn.clicked.connect(self._save_collage)
        self.size_label = QLabel("")
        self.size_label.setStyleSheet(f"color: {resolved_palette()['muted']};")
        save_row.addWidget(self.save_btn)
        save_row.addWidget(self.size_label, stretch=1)
        right_layout.addLayout(save_row)

        splitter.addWidget(right_panel)
        splitter.setSizes([380, 620])
        root.addWidget(splitter, stretch=1)

    def _on_layout_changed(self, index: int) -> None:
        preset = list(collage_ops.LAYOUT_PRESETS.values())[index]
        cols = preset.get("cols")
        if cols:
            self.cols_spin.setValue(cols)

    def _add_images(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add Images", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff)"
        )
        for path in paths:
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.image_list.addItem(item)

    def _remove_selected(self) -> None:
        for item in self.image_list.selectedItems():
            self.image_list.takeItem(self.image_list.row(item))

    def _clear_images(self) -> None:
        self.image_list.clear()

    def _pick_bg_color(self) -> None:
        qc = QColorDialog.getColor(parent=self)
        if qc.isValid():
            self.bg_color = (qc.red(), qc.green(), qc.blue())

    def _gather_paths(self) -> list[str]:
        return [
            self.image_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.image_list.count())
        ]

    def _generate_collage(self) -> None:
        paths = self._gather_paths()
        if not paths:
            QMessageBox.warning(self, "No Images", "Add at least one image first.")
            return
        cfg = collage_ops.CollageConfig(
            cols=self.cols_spin.value(),
            thumb_width=self.cell_w_spin.value(),
            thumb_height=self.cell_h_spin.value(),
            padding=self.padding_spin.value(),
            bg_color=self.bg_color,
            fit_mode=self.fit_combo.currentText(),
        )
        captions = None
        if self.captions_check.isChecked():
            captions = [os.path.basename(p) for p in paths]

        self._progress_dialog = QProgressDialog("Generating collage...", None, 0, 0, self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()
        self._worker = WorkerThread(collage_ops.make_collage, paths, cfg, captions)
        self._worker.finished_ok.connect(self._on_collage_done)
        self._worker.failed.connect(self._on_collage_failed)
        self._worker.start()

    def _on_collage_done(self, collage: Image.Image) -> None:
        self._progress_dialog.close()
        self.current_collage = collage
        pixmap = _pil_to_qpixmap(self.current_collage)
        scaled = pixmap.scaled(600, 500, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.preview_label.setPixmap(scaled)
        self.size_label.setText(f"Collage size: {self.current_collage.width}x{self.current_collage.height}px")

    def _on_collage_failed(self, message: str) -> None:
        self._progress_dialog.close()
        QMessageBox.critical(self, "Collage Error", message)

    def _save_collage(self) -> None:
        if self.current_collage is None:
            QMessageBox.warning(self, "Nothing to save", "Generate a collage preview first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Collage", "collage.png",
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;WEBP Image (*.webp)"
        )
        if not path:
            return
        try:
            ext = path.rsplit(".", 1)[-1].upper() if "." in path else "PNG"
            fmt = "JPEG" if ext in ("JPG", "JPEG") else ext
            self.current_collage.save(path, format=fmt)
            QMessageBox.information(self, "Saved", f"Collage saved to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))
