"""Color Palette Extractor & Eyedropper workspace: extract dominant colors and pick pixel colors with mouse."""

from __future__ import annotations

from typing import Optional, Tuple
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QGuiApplication, QPalette
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QMessageBox,
    QPushButton,
    QLabel,
    QScrollArea,
    QFrame,
    QFormLayout,
    QGroupBox,
    QTabWidget,
    QSplitter,
)
from PyQt6.QtGui import QMouseEvent
from PIL import Image

from app.core.customizable_toolbar import AppToolBar
from app.core.spinbox import NoScrollSpinBox
from app.features.palette import ops as palette_ops
from app.core.theme import resolved_palette, theme_signals
from app.core.tooltips import copy_hex_tooltip, get_tooltip_for
from app.ui.ui_scaling import scaled_font_pt


class ClickableImagePreview(QLabel):
    """Interactive preview label with mouse tracking for pixel color sampling."""

    color_hovered = pyqtSignal(int, int, int, int, int)  # r, g, b, orig_x, orig_y
    color_clicked = pyqtSignal(int, int, int, int, int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.pil_image: Optional[Image.Image] = None
        self.rendered_pixmap: Optional[QPixmap] = None
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_image(self, pil_img: Image.Image, pixmap: QPixmap) -> None:
        self.pil_image = pil_img
        self.rendered_pixmap = pixmap
        self.setPixmap(pixmap)

    def _get_pixel_at(self, pos: QPoint) -> Optional[Tuple[int, int, int, int, int]]:
        if (
            not self.pil_image
            or not self.rendered_pixmap
            or self.rendered_pixmap.isNull()
        ):
            return None

        # Calculate offset where pixmap is drawn inside label (since aligned center)
        lbl_w, lbl_h = self.width(), self.height()
        pm_w, pm_h = self.rendered_pixmap.width(), self.rendered_pixmap.height()
        offset_x = (lbl_w - pm_w) // 2
        offset_y = (lbl_h - pm_h) // 2

        pm_x = pos.x() - offset_x
        pm_y = pos.y() - offset_y

        if 0 <= pm_x < pm_w and 0 <= pm_y < pm_h:
            # Map pixmap coordinates to original PIL image
            orig_x = int(pm_x * (self.pil_image.width / pm_w))
            orig_y = int(pm_y * (self.pil_image.height / pm_h))
            swatch = palette_ops.sample_pixel_color(self.pil_image, orig_x, orig_y)
            r, g, b = swatch.rgb
            return r, g, b, orig_x, orig_y
        return None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        res: Optional[Tuple[int, int, int, int, int]] = self._get_pixel_at(event.pos())
        if res:
            self.color_hovered.emit(*res)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            res = self._get_pixel_at(event.pos())
            if res:
                self.color_clicked.emit(*res)


class PaletteTab(QWidget):
    """Extract dominant colors and pick pixel colors with interactive eyedropper."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.current_img: Optional[Image.Image] = None
        self.swatches: list[palette_ops.ColorSwatch] = []
        self.sampled_swatches: list[palette_ops.ColorSwatch] = []
        self._last_hover_rgb: Optional[Tuple[int, int, int]] = None
        self._build_ui()
        theme_signals.changed.connect(self._refresh_theme_colors)

    def _refresh_theme_colors(self) -> None:
        self.image_preview.setStyleSheet(self._image_preview_stylesheet())
        self.hover_color_box.setStyleSheet(self._hover_box_stylesheet())
        muted = resolved_palette()["muted"]
        self.hover_rgb_lbl.setStyleSheet(
            f"color: {muted}; font-size: {scaled_font_pt(11)};"
        )
        self.hover_coord_lbl.setStyleSheet(
            f"color: {muted}; font-size: {scaled_font_pt(11)};"
        )
        self.status_label.setStyleSheet(f"color: {muted};")

    def _image_preview_stylesheet(self) -> str:
        base = self.palette().color(QPalette.ColorRole.Base).name()
        border = resolved_palette()["border"]
        return f"background: {base}; border: 1px solid {border}; border-radius: 8px;"

    def _hover_box_stylesheet(self) -> str:
        border = resolved_palette()["border"]
        if self._last_hover_rgb is not None:
            r, g, b = self._last_hover_rgb
            bg = f"#{r:02X}{g:02X}{b:02X}"
        else:
            bg = border
        return f"background: {bg}; border: 2px solid {border}; border-radius: 6px;"

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("Color Palette Extractor & Eyedropper")
        title.setStyleSheet("font-weight: 700;")
        root.addWidget(title)
        root.addWidget(
            QLabel(
                "Extract dominant colors automatically or click anywhere on the image with the eyedropper cursor."
            )
        )

        self._create_toolbar(root)

        # Splitter: Left Preview + Eyedropper HUD, Right Swatches Tabs
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_box = self._create_left_panel()
        splitter.addWidget(left_box)

        right_box = self._create_right_panel()
        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)

        root.addWidget(splitter, stretch=1)

        self.status_label = QLabel(
            "Open an image to extract palettes or sample colors with the mouse."
        )
        self.status_label.setStyleSheet(f"color: {resolved_palette()['muted']};")
        root.addWidget(self.status_label)

    def _create_toolbar(self, root: QVBoxLayout) -> None:
        top_row = AppToolBar(None, "palette_toolbar")
        top_row.add_action("Open Image...", self._open_image, tooltip_key="Open Image")
        top_row.addWidget(QLabel("  Colors to extract:"))
        self.n_spin = NoScrollSpinBox()
        self.n_spin.setToolTip(get_tooltip_for("Colors to Extract"))
        self.n_spin.setRange(2, 32)
        self.n_spin.setValue(8)
        top_row.addWidget(self.n_spin)
        top_row.add_action("Extract Dominant Palette", self._extract_palette)
        top_row.addSeparator()
        top_row.add_action("Copy All Extracted Hex", self._copy_all_hex)
        top_row.finalize()
        root.addWidget(top_row)

    def _create_left_panel(self) -> QWidget:
        # Left Column: Image Preview + Eyedropper Loupe
        left_box = QWidget()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)

        self.image_preview = ClickableImagePreview()
        self.image_preview.setMinimumSize(320, 240)
        self.image_preview.setStyleSheet(self._image_preview_stylesheet())
        self.image_preview.setText("Open an image to start picking colors")
        self.image_preview.setToolTip(get_tooltip_for("Eyedropper Preview"))
        self.image_preview.color_hovered.connect(self._on_color_hovered)
        self.image_preview.color_clicked.connect(self._on_color_clicked)
        left_layout.addWidget(self.image_preview, stretch=1)

        # Eyedropper live card
        self.eyedropper_card = QGroupBox("Eyedropper Tool (Hover / Click to sample)")
        eye_layout = QHBoxLayout(self.eyedropper_card)
        eye_layout.setContentsMargins(10, 8, 10, 8)
        eye_layout.setSpacing(12)

        self.hover_color_box = QLabel()
        self.hover_color_box.setFixedSize(48, 48)
        self.hover_color_box.setStyleSheet(self._hover_box_stylesheet())
        eye_layout.addWidget(self.hover_color_box)

        info_v = QVBoxLayout()
        self.hover_hex_lbl = QLabel("#------")
        self.hover_hex_lbl.setStyleSheet(
            f"font-weight: 700; font-size: {scaled_font_pt(15)};"
        )
        self.hover_rgb_lbl = QLabel("rgb(---, ---, ---)")
        self.hover_rgb_lbl.setStyleSheet(
            f"color: {resolved_palette()['muted']}; font-size: {scaled_font_pt(11)};"
        )
        self.hover_coord_lbl = QLabel("Position: (-, -)")
        self.hover_coord_lbl.setStyleSheet(
            f"color: {resolved_palette()['muted']}; font-size: {scaled_font_pt(11)};"
        )
        info_v.addWidget(self.hover_hex_lbl)
        info_v.addWidget(self.hover_rgb_lbl)
        info_v.addWidget(self.hover_coord_lbl)
        eye_layout.addLayout(info_v, stretch=1)

        copy_hover_btn = QPushButton("Copy Hex")
        copy_hover_btn.setToolTip(get_tooltip_for("Copy Hex"))
        copy_hover_btn.clicked.connect(
            lambda: self._copy_hex(self.hover_hex_lbl.text())
        )
        eye_layout.addWidget(copy_hover_btn)
        left_layout.addWidget(self.eyedropper_card)

        return left_box

    def _create_right_panel(self) -> QWidget:
        # Right Column: Palette Tabs (Extracted vs Eyedropper Sampled)
        right_box = QWidget()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        self.palette_tabs = QTabWidget()

        # Tab 1: Dominant Colors
        swatch_scroll = QScrollArea(
            widgetResizable=True, frameShape=QFrame.Shape.NoFrame
        )
        self.swatch_widget = QWidget()
        self.swatch_layout = QVBoxLayout(self.swatch_widget)
        self.swatch_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.swatch_layout.setSpacing(6)
        swatch_scroll.setWidget(self.swatch_widget)
        self.palette_tabs.addTab(swatch_scroll, "Dominant Colors")

        # Tab 2: Sampled Colors (Eyedropper)
        sampled_scroll = QScrollArea(
            widgetResizable=True, frameShape=QFrame.Shape.NoFrame
        )
        self.sampled_widget = QWidget()
        self.sampled_layout = QVBoxLayout(self.sampled_widget)
        self.sampled_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sampled_layout.setSpacing(6)
        sampled_scroll.setWidget(self.sampled_widget)

        sampled_tab_container = QWidget()
        sampled_vbox = QVBoxLayout(sampled_tab_container)
        sampled_vbox.setContentsMargins(0, 4, 0, 0)
        clear_sampled_btn = QPushButton("Clear Sampled Colors")
        clear_sampled_btn.setToolTip(get_tooltip_for("Clear Sampled Colors"))
        clear_sampled_btn.clicked.connect(self._clear_sampled)
        sampled_vbox.addWidget(clear_sampled_btn)
        sampled_vbox.addWidget(sampled_scroll, stretch=1)

        self.palette_tabs.addTab(sampled_tab_container, "Eyedropper Samples (0)")
        right_layout.addWidget(self.palette_tabs, stretch=1)

        return right_box

    def _open_image(self) -> None:
        path: str
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.gif)",
        )
        if not path:
            return
        try:
            self.current_img = Image.open(path)
            pixmap = QPixmap(path)
            scaled = pixmap.scaled(
                400,
                300,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_preview.set_image(self.current_img, scaled)
            self.status_label.setText(
                f"Loaded: {path}  ({self.current_img.width} × {self.current_img.height})"
            )
            self._extract_palette()
        except Exception as exc:
            QMessageBox.critical(self, "Open Error", str(exc))

    def _extract_palette(self) -> None:
        if self.current_img is None:
            return
        n: int = self.n_spin.value()
        try:
            self.swatches = palette_ops.extract_palette(self.current_img, n_colors=n)
            self._render_swatches()
        except Exception as exc:
            QMessageBox.critical(self, "Extraction Error", str(exc))

    def _on_color_hovered(self, r: int, g: int, b: int, x: int, y: int) -> None:
        hex_code: str = f"#{r:02X}{g:02X}{b:02X}"
        name: str = palette_ops.nearest_named_color((r, g, b))
        contrast: float = palette_ops.contrast_ratio((r, g, b), (255, 255, 255))
        self._last_hover_rgb = (r, g, b)
        self.hover_color_box.setStyleSheet(self._hover_box_stylesheet())
        self.hover_hex_lbl.setText(f"{hex_code} - {name}")
        self.hover_rgb_lbl.setText(
            f"rgb({r}, {g}, {b}) - contrast {contrast:.2f}:1 vs white"
        )
        self.hover_coord_lbl.setText(f"Pixel: ({x}, {y})")

    def _on_color_clicked(self, r: int, g: int, b: int, x: int, y: int) -> None:
        hex_code: str = f"#{r:02X}{g:02X}{b:02X}"
        swatch: palette_ops.ColorSwatch = palette_ops.ColorSwatch(
            hex_code=hex_code,
            rgb=(r, g, b),
            percentage=0.0,
            name=palette_ops.nearest_named_color((r, g, b)),
        )
        self.sampled_swatches.insert(0, swatch)
        self._render_sampled_swatches()
        self._copy_hex(hex_code)
        self.status_label.setText(
            f"Sampled pixel ({x}, {y}): {hex_code} ({swatch.css_name}) (Copied to clipboard)"
        )

    def _render_swatches(self) -> None:
        while self.swatch_layout.count():
            item = self.swatch_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for swatch in self.swatches:
            row: QWidget = self._create_swatch_row(swatch, show_pct=True)
            self.swatch_layout.addWidget(row)

        self.status_label.setText(f"Extracted {len(self.swatches)} dominant colors.")

    def _render_sampled_swatches(self) -> None:
        while self.sampled_layout.count():
            item = self.sampled_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.palette_tabs.setTabText(
            1, f"Eyedropper Samples ({len(self.sampled_swatches)})"
        )
        for swatch in self.sampled_swatches:
            row: QWidget = self._create_swatch_row(swatch, show_pct=False)
            self.sampled_layout.addWidget(row)

    def _create_swatch_row(
        self, swatch: palette_ops.ColorSwatch, show_pct: bool = True
    ) -> QWidget:
        row: QWidget = QWidget()
        row_layout: QHBoxLayout = QHBoxLayout(row)
        row_layout.setContentsMargins(6, 3, 6, 3)
        row_layout.setSpacing(10)

        palette = resolved_palette()

        # Color button
        swatch_btn = QPushButton()
        swatch_btn.setFixedSize(44, 44)
        border = palette["border"]
        swatch_btn.setStyleSheet(
            f"background: {swatch.hex_code}; border: 2px solid {border}; border-radius: 6px;"
        )
        swatch_btn.setToolTip(copy_hex_tooltip(swatch.hex_code))
        swatch_btn.clicked.connect(lambda _=False, h=swatch.hex_code: self._copy_hex(h))
        row_layout.addWidget(swatch_btn)

        # Info
        info = QVBoxLayout()
        hex_label = QLabel(f"{swatch.hex_code} · {swatch.css_name}")
        hex_label.setStyleSheet(f"font-weight: 700; font-size: {scaled_font_pt(14)};")
        rgb_label = QLabel(swatch.rgb_str)
        rgb_label.setStyleSheet(
            f"color: {palette['muted']}; font-size: {scaled_font_pt(11)};"
        )
        info.addWidget(hex_label)
        info.addWidget(rgb_label)
        if show_pct:
            pct_label = QLabel(f"{swatch.percentage}% of pixels")
            pct_label.setStyleSheet(
                f"color: {palette['muted']}; font-size: {scaled_font_pt(11)};"
            )
            info.addWidget(pct_label)
        row_layout.addLayout(info, stretch=1)

        copy_hex_btn = QPushButton("Hex")
        copy_hex_btn.setToolTip(get_tooltip_for("Copy Hex"))
        copy_hex_btn.setFixedWidth(44)
        copy_hex_btn.clicked.connect(
            lambda _=False, h=swatch.hex_code: self._copy_hex(h)
        )
        copy_rgb_btn = QPushButton("RGB")
        copy_rgb_btn.setToolTip(get_tooltip_for("Copy Hex"))
        copy_rgb_btn.setFixedWidth(44)
        copy_rgb_btn.clicked.connect(
            lambda _=False, s=swatch: self._copy_hex(s.rgb_str)
        )
        row_layout.addWidget(copy_hex_btn)
        row_layout.addWidget(copy_rgb_btn)
        return row

    def _clear_sampled(self) -> None:
        self.sampled_swatches.clear()
        self._render_sampled_swatches()

    def _copy_hex(self, text: str) -> None:
        QGuiApplication.clipboard().setText(text)

    def _copy_all_hex(self) -> None:
        if not self.swatches:
            return
        all_hex: str = ", ".join(s.hex_code for s in self.swatches)
        QGuiApplication.clipboard().setText(all_hex)
        QMessageBox.information(
            self, "Copied", f"Copied {len(self.swatches)} hex codes to clipboard!"
        )
