"""Image tab: view, markup, crop, resize, convert, compress, batch process, and photo editing."""
import os
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import QSettings, Qt, QPointF, QTimer
from PyQt6.QtGui import QImage, QPixmap, QAction, QActionGroup, QKeySequence, QFont, QGuiApplication, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QFileDialog, QLabel,
    QMessageBox, QDialog, QFormLayout, QComboBox, QSlider, QDialogButtonBox,
    QCheckBox, QListWidget, QProgressDialog, QPushButton, QColorDialog,
    QTabWidget, QButtonGroup, QRadioButton, QFontComboBox, QInputDialog, QMenu, QTextEdit
)
from PIL import Image, ImageFont, ImageDraw

from app.ui.canvas import AnnotationCanvas, Tool, ResizableRectItem, ResizableTextItem, ResizableArrowItem, show_shortcuts_dialog
from app.ui.screenshot_dialog import ScreenshotDialog
from app.features.image import ops as image_ops
from app.core.customizable_toolbar import AppToolBar, apply_standard_icon
from app.core.spinbox import NoScrollSpinBox
from app.core.file_formats import extension_for_format, format_from_path
from app.core.tooltips import get_tooltip_for
from app.ui.ui_scaling import scaled_font_size
from app.system.workers import WorkerThread


EASY_QUALITY_PRESETS = {
    "Small file size": 40,
    "Balanced": 75,
    "Best quality": 92,
}
EASY_QUALITY_DESCRIPTIONS = {
    "Small file size": "Smallest file, more visible quality loss.",
    "Balanced": "Good trade-off for most images (recommended).",
    "Best quality": "Largest file, minimal quality loss.",
}


def _add_easy_radio_group(layout: QVBoxLayout, parent: QWidget) -> Tuple[QButtonGroup, Dict[str, QRadioButton]]:
    """Build the shared 3-option Easy-mode radio group used by both the
    single-image and batch compress dialogs. Returns (button_group, dict)."""
    layout.addWidget(QLabel("Choose a compression level:"))
    group = QButtonGroup(parent)
    radios = {}
    for name in EASY_QUALITY_PRESETS:
        rb = QRadioButton(name)
        rb.setToolTip(get_tooltip_for(name))
        group.addButton(rb)
        radios[name] = rb
        layout.addWidget(rb)
        hint = QLabel(f"    {EASY_QUALITY_DESCRIPTIONS[name]}")
        layout.addWidget(hint)
    radios["Balanced"].setChecked(True)
    return group, radios


def _easy_selected_quality(radios: Dict[str, QRadioButton]) -> int:
    for name, rb in radios.items():
        if rb.isChecked():
            return EASY_QUALITY_PRESETS[name]
    return EASY_QUALITY_PRESETS["Balanced"]


def _load_pil_font(size: int, family: str = "Helvetica", bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
    """Best-effort scalable font lookup so baked text reflects the chosen
    size, family, and bold/italic styling."""
    name = (family or "").lower()
    if "courier" in name or "mono" in name or "consolas" in name:
        candidates = {
            (False, False): ["cour.ttf", "Courier New.ttf", "DejaVuSansMono.ttf"],
            (True, False): ["courbd.ttf", "Courier New Bold.ttf", "DejaVuSansMono-Bold.ttf"],
            (False, True): ["couri.ttf", "Courier New Italic.ttf", "DejaVuSansMono-Oblique.ttf"],
            (True, True): ["courbi.ttf", "Courier New Bold Italic.ttf", "DejaVuSansMono-BoldOblique.ttf"],
        }[(bold, italic)]
    elif "times" in name or "serif" in name or "georgia" in name:
        candidates = {
            (False, False): ["times.ttf", "Times New Roman.ttf", "DejaVuSerif.ttf"],
            (True, False): ["timesbd.ttf", "Times New Roman Bold.ttf", "DejaVuSerif-Bold.ttf"],
            (False, True): ["timesi.ttf", "Times New Roman Italic.ttf", "DejaVuSerif-Italic.ttf"],
            (True, True): ["timesbi.ttf", "Times New Roman Bold Italic.ttf", "DejaVuSerif-BoldItalic.ttf"],
        }[(bold, italic)]
    else:
        candidates = {
            (False, False): ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"],
            (True, False): ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"],
            (False, True): ["ariali.ttf", "Arial Italic.ttf", "DejaVuSans-Oblique.ttf"],
            (True, True): ["arialbi.ttf", "Arial Bold Italic.ttf", "DejaVuSans-BoldOblique.ttf"],
        }[(bold, italic)]

    search_dirs = [
        "", "/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/truetype/msttcorefonts/",
        "/System/Library/Fonts/Supplemental/", "C:\\Windows\\Fonts\\",  # noqa: 26 (standard per-OS font directories, not user-configurable paths)
    ]
    for directory in search_dirs:
        for filename in candidates:
            try:
                return ImageFont.truetype(directory + filename, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_text_with_spacing(draw: ImageDraw.ImageDraw, pos: Tuple[float, float], text: str, font: ImageFont.FreeTypeFont, color: Tuple[int, ...], letter_spacing: int) -> None:
    """Draw text with extra gap between characters."""
    if letter_spacing == 100:
        draw.text(pos, text, fill=color, font=font)
        return
    x, y = pos
    font_size = getattr(font, "size", 14)
    extra = (letter_spacing - 100) / 100.0 * font_size * 0.5
    for ch in text:
        draw.text((x, y), ch, fill=color, font=font)
        x += font.getlength(ch) + extra


def _pil_to_qimage(image: Image.Image) -> QImage:
    """Convert a Pillow image to a detached QImage safe for Qt rendering."""
    if image.mode == "RGBA":
        raw = image.tobytes("raw", "RGBA")
        qimage = QImage(raw, image.width, image.height, image.width * 4, QImage.Format.Format_RGBA8888)
    else:
        rgb = image.convert("RGB")
        raw = rgb.tobytes("raw", "RGB")
        qimage = QImage(raw, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888)
    return qimage.copy()


def _qimage_to_pil(qimage: QImage) -> Image.Image:
    """Copy a Qt image layer into Pillow-owned RGBA pixel storage."""
    image = qimage.convertToFormat(QImage.Format.Format_RGBA8888)
    pixels = image.bits().asstring(image.sizeInBytes())
    return Image.frombytes("RGBA", (image.width(), image.height()), pixels, "raw", "RGBA")


class ResizeDialog(QDialog):
    def __init__(self, current_size: Tuple[int, int], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Resize Image")
        layout = QFormLayout(self)
        self.width_spin = NoScrollSpinBox()
        self.width_spin.setRange(1, 20000)
        self.width_spin.setValue(current_size[0])
        self.width_spin.setToolTip(get_tooltip_for("Image Width"))
        self.height_spin = NoScrollSpinBox()
        self.height_spin.setRange(1, 20000)
        self.height_spin.setValue(current_size[1])
        self.height_spin.setToolTip(get_tooltip_for("Image Height"))
        self.keep_aspect = QCheckBox("Keep aspect ratio")
        self.keep_aspect.setChecked(True)
        self.keep_aspect.setToolTip(get_tooltip_for("Keep aspect ratio"))
        layout.addRow("Width:", self.width_spin)
        layout.addRow("Height:", self.height_spin)
        layout.addRow(self.keep_aspect)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> Tuple[int, int, bool]:
        return self.width_spin.value(), self.height_spin.value(), self.keep_aspect.isChecked()


class PhotoAdjustDialog(QDialog):
    """Adjust tone, color, sharpness, warmth, blur, and presets for photo or layer."""

    def __init__(self, opacity: float = 1.0, show_opacity: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Adjust Photo Tone & Colors")
        self.resize(380, 440)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Custom / Manual")
        self.preset_combo.addItems(image_ops.FILTER_PRESETS)
        self.preset_combo.setToolTip(get_tooltip_for("Preset Look"))
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        form.addRow("Preset Look:", self.preset_combo)

        self.brightness = NoScrollSpinBox()
        self.brightness.setRange(0, 300)
        self.brightness.setValue(100)
        self.brightness.setSuffix("%")
        self.brightness.setToolTip(get_tooltip_for("Brightness"))
        form.addRow("Brightness:", self.brightness)

        self.contrast = NoScrollSpinBox()
        self.contrast.setRange(0, 300)
        self.contrast.setValue(100)
        self.contrast.setSuffix("%")
        self.contrast.setToolTip(get_tooltip_for("Contrast"))
        form.addRow("Contrast:", self.contrast)

        self.saturation = NoScrollSpinBox()
        self.saturation.setRange(0, 300)
        self.saturation.setValue(100)
        self.saturation.setSuffix("%")
        self.saturation.setToolTip(get_tooltip_for("Saturation"))
        form.addRow("Saturation:", self.saturation)

        self.warmth = NoScrollSpinBox()
        self.warmth.setRange(-100, 100)
        self.warmth.setValue(0)
        self.warmth.setToolTip(get_tooltip_for("Warmth"))
        form.addRow("Warmth (Tint):", self.warmth)

        self.sharpness = NoScrollSpinBox()
        self.sharpness.setRange(0, 300)
        self.sharpness.setValue(100)
        self.sharpness.setSuffix("%")
        self.sharpness.setToolTip(get_tooltip_for("Sharpness"))
        form.addRow("Sharpness:", self.sharpness)

        self.blur = NoScrollSpinBox()
        self.blur.setRange(0, 50)
        self.blur.setValue(0)
        self.blur.setSuffix(" px")
        self.blur.setToolTip(get_tooltip_for("Blur (Soft focus)"))
        form.addRow("Blur (Soft focus):", self.blur)

        self.show_opacity = show_opacity
        self.opacity = NoScrollSpinBox()
        self.opacity.setRange(0, 100)
        self.opacity.setValue(round(opacity * 100))
        self.opacity.setSuffix("%")
        self.opacity.setToolTip(get_tooltip_for("Layer Opacity"))
        if show_opacity:
            form.addRow("Layer Opacity:", self.opacity)

        self.grayscale = QCheckBox("Black && White (Grayscale)")
        self.grayscale.setToolTip(get_tooltip_for("Grayscale"))
        form.addRow(self.grayscale)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_preset_changed(self, name: str) -> None:
        if name == "Auto Enhance":
            self.brightness.setValue(105)
            self.contrast.setValue(115)
            self.saturation.setValue(110)
            self.sharpness.setValue(115)
            self.warmth.setValue(0)
            self.grayscale.setChecked(False)
        elif name == "Vivid":
            self.brightness.setValue(100)
            self.contrast.setValue(125)
            self.saturation.setValue(135)
            self.sharpness.setValue(130)
            self.warmth.setValue(0)
            self.grayscale.setChecked(False)
        elif name == "Warm Tone":
            self.brightness.setValue(102)
            self.contrast.setValue(105)
            self.saturation.setValue(115)
            self.warmth.setValue(40)
            self.grayscale.setChecked(False)
        elif name == "Cool Tone":
            self.brightness.setValue(100)
            self.contrast.setValue(105)
            self.saturation.setValue(105)
            self.warmth.setValue(-40)
            self.grayscale.setChecked(False)
        elif name == "Grayscale":
            self.grayscale.setChecked(True)
        elif name == "High Contrast B&W":
            self.contrast.setValue(140)
            self.sharpness.setValue(120)
            self.grayscale.setChecked(True)
        elif name == "Sepia":
            self.warmth.setValue(50)
            self.contrast.setValue(110)
            self.saturation.setValue(60)
            self.grayscale.setChecked(False)
        elif name == "Vintage / Fade":
            self.brightness.setValue(110)
            self.contrast.setValue(85)
            self.saturation.setValue(85)
            self.warmth.setValue(20)
            self.grayscale.setChecked(False)

    def values(self) -> Dict[str, Any]:
        return {
            "preset": self.preset_combo.currentText(),
            "brightness": self.brightness.value(),
            "contrast": self.contrast.value(),
            "saturation": self.saturation.value(),
            "warmth": self.warmth.value(),
            "sharpness": self.sharpness.value(),
            "blur": self.blur.value(),
            "opacity": self.opacity.value(),
            "grayscale": self.grayscale.isChecked(),
        }


class AspectCropDialog(QDialog):
    """Aspect ratio selection dialog."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Crop to Aspect Ratio")
        layout = QFormLayout(self)
        self.combo = QComboBox()
        for name in image_ops.ASPECT_RATIO_PRESETS:
            self.combo.addItem(name)
        self.combo.setToolTip(get_tooltip_for("Aspect Ratio"))
        layout.addRow("Aspect Ratio:", self.combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def selected_ratio(self) -> Tuple[int, int]:
        name = self.combo.currentText()
        return image_ops.ASPECT_RATIO_PRESETS.get(name, (1, 1))


class BorderDialog(QDialog):
    """Border & Polaroid framing dialog."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Border / Frame")
        layout = QFormLayout(self)
        self.border_width = NoScrollSpinBox()
        self.border_width.setRange(1, 400)
        self.border_width.setValue(30)
        self.border_width.setSuffix(" px")
        self.border_width.setToolTip(get_tooltip_for("Border Width"))
        self.polaroid_check = QCheckBox("Polaroid style (extra bottom padding)")
        self.polaroid_check.setToolTip(get_tooltip_for("Polaroid style (extra bottom padding)"))
        self.color = QColor(255, 255, 255)
        self.color_btn = QPushButton("Choose Color...")
        self.color_btn.setToolTip(get_tooltip_for("Choose Color"))
        self.color_btn.clicked.connect(self._pick_color)
        layout.addRow("Border Width:", self.border_width)
        layout.addRow("Frame Color:", self.color_btn)
        layout.addRow(self.polaroid_check)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(self.color, self, "Frame Color")
        if color.isValid():
            self.color = color

    def values(self) -> Tuple[int, Tuple[int, int, int], bool]:
        return self.border_width.value(), (self.color.red(), self.color.green(), self.color.blue()), self.polaroid_check.isChecked()


class CompressConvertDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Compress / Convert")
        self.resize(380, 320)
        layout = QVBoxLayout(self)

        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(image_ops.SINGLE_IMAGE_EXPORT_FORMATS)
        self.format_combo.setToolTip(get_tooltip_for("Export Format"))
        format_row.addWidget(self.format_combo)
        layout.addLayout(format_row)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        easy_widget = QWidget()
        easy_layout = QVBoxLayout(easy_widget)
        self.easy_group, self.easy_radios = _add_easy_radio_group(easy_layout, self)
        easy_layout.addStretch()
        self.tabs.addTab(easy_widget, "Easy")

        adv_widget = QWidget()
        adv_layout = QFormLayout(adv_widget)
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(10, 100)
        self.quality_slider.setValue(85)
        self.quality_label = QLabel("85")
        self.quality_slider.valueChanged.connect(lambda v: self.quality_label.setText(str(v)))
        q_row = QHBoxLayout()
        q_row.addWidget(self.quality_slider)
        q_row.addWidget(self.quality_label)
        adv_layout.addRow("Quality:", q_row)
        self.tabs.addTab(adv_widget, "Advanced")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> Tuple[str, int]:
        fmt = self.format_combo.currentText()
        if self.tabs.currentIndex() == 0:  # Easy tab
            return fmt, _easy_selected_quality(self.easy_radios)
        return fmt, self.quality_slider.value()


class BackgroundRemovalDialog(QDialog):
    """Choose an on-device cutout model with understandable tradeoffs."""

    def __init__(self, selected_model: str = "bria-rmbg", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Remove Background")
        self.resize(460, 250)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("All models run locally. A selected model may download once, then remains on this computer."))
        form = QFormLayout()
        self.model_combo = QComboBox()
        self.model_combo.setToolTip(get_tooltip_for("Background Removal Model"))
        safe_model = image_ops._normalize_model_name(selected_model)
        if safe_model not in image_ops.BACKGROUND_REMOVAL_MODELS:
            safe_model = "bria-rmbg"
        choice_entries = [
            ("Default", "bria-rmbg"),
            ("Balanced", "bria-rmbg"),
            ("Fast", "u2netp"),
            ("Detailed", "isnet-general-use"),
            ("Best quality", "birefnet-general"),
            ("Portrait", "birefnet-portrait"),
        ]
        for label, model_name in choice_entries:
            description = image_ops.BACKGROUND_REMOVAL_MODELS[model_name][1]
            self.model_combo.addItem(f"{label} ({model_name}) -- {description}", model_name)
        current_index = self.model_combo.findData(safe_model)
        self.model_combo.setCurrentIndex(max(0, current_index))
        form.addRow("Model:", self.model_combo)
        layout.addLayout(form)
        self.detail = QLabel()
        self.detail.setWordWrap(True)
        self.detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.detail.setStyleSheet("")
        self.model_combo.currentIndexChanged.connect(self._update_detail)
        layout.addWidget(self.detail)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._update_detail()

    def _update_detail(self) -> None:
        model_name = self.model_combo.currentData()
        label, description = image_ops.BACKGROUND_REMOVAL_MODELS[model_name]
        self.detail.setText(f"{label}: {description}")

    def selected_model(self) -> str:
        value = self.model_combo.currentData()
        value = image_ops._normalize_model_name(value)
        if value not in image_ops.BACKGROUND_REMOVAL_MODELS:
            return "bria-rmbg"
        return value


class BatchDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Batch Process Images")
        self.resize(440, 480)
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        layout.addWidget(QLabel("Files to process:"))
        layout.addWidget(self.list_widget)
        add_btn = QPushButton("Add Files...")
        add_btn.setToolTip(get_tooltip_for("Add Files"))
        add_btn.clicked.connect(self._add_files)
        layout.addWidget(add_btn)

        top_form = QFormLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItem("Keep original")
        self.format_combo.addItems(image_ops.SUPPORTED_FORMATS)
        self.format_combo.setToolTip(get_tooltip_for("Batch Convert Format"))
        top_form.addRow("Convert to:", self.format_combo)
        layout.addLayout(top_form)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        easy_widget = QWidget()
        easy_layout = QVBoxLayout(easy_widget)
        self.easy_group, self.easy_radios = _add_easy_radio_group(easy_layout, self)
        easy_layout.addStretch()
        self.tabs.addTab(easy_widget, "Easy")

        adv_widget = QWidget()
        adv_form = QFormLayout(adv_widget)
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(10, 100)
        self.quality_slider.setValue(85)
        adv_form.addRow("Quality:", self.quality_slider)
        self.tabs.addTab(adv_widget, "Advanced")

        bottom_form = QFormLayout()
        self.resize_check = QCheckBox("Resize")
        self.resize_check.setToolTip(get_tooltip_for("Resize"))
        self.width_spin = NoScrollSpinBox()
        self.width_spin.setRange(1, 20000)
        self.width_spin.setValue(1920)
        self.width_spin.setToolTip(get_tooltip_for("Batch Max Width"))
        self.height_spin = NoScrollSpinBox()
        self.height_spin.setRange(1, 20000)
        self.height_spin.setValue(1080)
        self.height_spin.setToolTip(get_tooltip_for("Batch Max Height"))
        bottom_form.addRow(self.resize_check)
        bottom_form.addRow("Max width:", self.width_spin)
        bottom_form.addRow("Max height:", self.height_spin)
        layout.addLayout(bottom_form)

        bg_form = QFormLayout()
        self.remove_background_check = QCheckBox("Remove background (local AI model)")
        self.remove_background_check.setToolTip(get_tooltip_for("Remove Background"))
        bg_form.addRow(self.remove_background_check)
        self.bg_model_combo = QComboBox()
        self.bg_model_combo.setToolTip(get_tooltip_for("Background Removal Model"))
        saved_model = QSettings("FOSSEverything", "FOSSEverything").value("background_removal/model", "bria-rmbg")
        safe_model = image_ops._normalize_model_name(saved_model)
        if safe_model not in image_ops.BACKGROUND_REMOVAL_MODELS:
            safe_model = "bria-rmbg"
        for model_name, (label, description) in image_ops.BACKGROUND_REMOVAL_MODELS.items():
            self.bg_model_combo.addItem(f"{label} ({model_name}) -- {description}", model_name)
        self.bg_model_combo.setCurrentIndex(max(0, self.bg_model_combo.findData(safe_model)))
        self.bg_model_combo.setEnabled(False)
        self.remove_background_check.toggled.connect(self.bg_model_combo.setEnabled)
        bg_form.addRow("Model:", self.bg_model_combo)
        layout.addLayout(bg_form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)"
        )
        for p in paths:
            self.list_widget.addItem(p)

    def get_options(self) -> Dict[str, Any]:
        paths = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        fmt = self.format_combo.currentText()
        fmt = None if fmt == "Keep original" else fmt
        resize_to = None
        if self.resize_check.isChecked():
            resize_to = (self.width_spin.value(), self.height_spin.value())
        if self.tabs.currentIndex() == 0:  # Easy tab
            quality = _easy_selected_quality(self.easy_radios)
        else:
            quality = self.quality_slider.value()
        return {
            "paths": paths,
            "target_format": fmt,
            "quality": quality,
            "resize_to": resize_to,
            "remove_background_enabled": self.remove_background_check.isChecked(),
            "bg_model": image_ops._normalize_model_name(self.bg_model_combo.currentData()),
        }


class ImageTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None, settings: Optional[QSettings] = None) -> None:
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings("FOSSEverything", "FOSSEverything")
        self.pil_image = None
        self.current_path = None
        self._progress_dialog = None
        self._worker = None
        self._edit_history = []
        self._edit_future = []
        self._restoring_edit = False
        self._crop_target_layer = None
        self._active_crop_frame = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.canvas = AnnotationCanvas()
        self.canvas.selection_changed.connect(self._on_selection_changed)
        self.canvas.image_layer_changed.connect(self._commit_edit)
        self.canvas.image_layer_context_requested.connect(self._show_layer_context_menu)
        self.canvas.content_changed.connect(self._commit_edit)
        self.canvas.crop_drawn.connect(self._apply_drawn_layer_crop)
        self.canvas.crop_frame_adjusted.connect(self._apply_crop_frame)
        self.canvas.file_dropped.connect(self.load_file_path)

        toolbar = AppToolBar(self.settings, "image_toolbar")
        toolbar.setMovable(False)
        self.toolbar = toolbar
        layout.addWidget(toolbar)

        toolbar.add_action("Open", self.open_image, tooltip_key="Open image")
        toolbar.add_action("Save As...", self.save_as, tooltip_key="Save As")
        toolbar.add_action("Screenshot...", self.take_screenshot, tooltip_key="Take screenshot")
        toolbar.add_action("Copy", self.copy_to_clipboard, shortcut=QKeySequence.StandardKey.Copy)
        toolbar.addSeparator()

        toolbar.add_action("Undo", self.undo_edit, shortcut=QKeySequence.StandardKey.Undo)
        toolbar.add_action("Redo", self.redo_edit, shortcut=QKeySequence("Ctrl+Y"))
        toolbar.add_action("Delete", self.delete_selected_layer)
        toolbar.addSeparator()

        self.tool_group = QActionGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_actions = {}
        tool_tooltip_keys = {
            "Select": "Select tool",
            "Rect": "Rect tool",
            "Text": "Text tool",
            "Freehand": "Freehand tool",
            "Arrow": "Arrow tool",
        }
        for label, tool in [
            ("Select", Tool.SELECT),
            ("Rect", Tool.RECT),
            ("Text", Tool.TEXT),
            ("Freehand", Tool.FREEHAND),
            ("Arrow", Tool.ARROW),
        ]:
            action = toolbar.add_action(label, checkable=True, tooltip_key=tool_tooltip_keys[label])
            action.triggered.connect(lambda checked, t=tool: self.canvas.set_tool(t))
            self.tool_group.addAction(action)
            self.tool_actions[tool] = action
        self.tool_actions[Tool.SELECT].setChecked(True)
        toolbar.addSeparator()

        toolbar.add_action("Color...", lambda: self.canvas.prompt_and_apply_color(self), tooltip_key="Color")

        toolbar.addWidget(QLabel(" Font: "))
        self.font_family_combo = QFontComboBox()
        self.font_family_combo.setMaximumWidth(150)
        # QFontComboBox.setCurrentFont() triggers a full system font-database match on
        # first call, costing 1s+ on Windows; defer it off the synchronous startup path.
        QTimer.singleShot(0, lambda: self.font_family_combo.setCurrentFont(QFont("Helvetica", scaled_font_size(10))))
        self.font_family_combo.currentFontChanged.connect(lambda qfont: self.canvas.apply_font_family(qfont.family()))
        toolbar.addWidget(self.font_family_combo)

        toolbar.addWidget(QLabel(" Size: "))
        self.font_size_spin = NoScrollSpinBox()
        self.font_size_spin.setRange(4, 200)
        self.font_size_spin.setValue(14)
        self.font_size_spin.setToolTip(get_tooltip_for("Font Size"))
        self.font_size_spin.valueChanged.connect(self.canvas.apply_font_size)
        toolbar.addWidget(self.font_size_spin)

        self.bold_action = toolbar.add_action("Bold", checkable=True)
        self.bold_action.toggled.connect(self.canvas.apply_bold)
        self.italic_action = toolbar.add_action("Italic", checkable=True)
        self.italic_action.toggled.connect(self.canvas.apply_italic)

        toolbar.addWidget(QLabel(" Spacing: "))
        self.letter_spacing_spin = NoScrollSpinBox()
        self.letter_spacing_spin.setRange(50, 300)
        self.letter_spacing_spin.setValue(100)
        self.letter_spacing_spin.setSuffix("%")
        self.letter_spacing_spin.setToolTip(get_tooltip_for("Letter Spacing"))
        self.letter_spacing_spin.valueChanged.connect(self.canvas.apply_letter_spacing)
        toolbar.addWidget(self.letter_spacing_spin)
        toolbar.addSeparator()

        toolbar.add_action("Zoom In", lambda: self.canvas.zoom_in(), shortcut=QKeySequence("Ctrl+="))
        toolbar.add_action("Zoom Out", lambda: self.canvas.zoom_out(), shortcut=QKeySequence("Ctrl+-"))
        toolbar.add_action("Fit", lambda: self.canvas.zoom_reset(), shortcut=QKeySequence("Ctrl+0"))
        toolbar.add_action("Shortcuts", lambda: show_shortcuts_dialog(self))
        toolbar.addSeparator()

        toolbar.add_action("Auto Enhance", self.auto_enhance, tooltip_key="Auto enhance")
        toolbar.add_action("Adjust Tone...", self.adjust_photo, tooltip_key="Adjust")
        toolbar.addSeparator()

        toolbar.add_action("Rotate CW", self.rotate_90_cw, shortcut=QKeySequence("Ctrl+R"), tooltip_key="Rotate clockwise")
        toolbar.add_action("Rotate CCW", self.rotate_90_ccw, shortcut=QKeySequence("Ctrl+Shift+R"), tooltip_key="Rotate counterclockwise")
        toolbar.add_action("Rotate Angle...", self.rotate_custom, tooltip_key="Custom rotate")
        toolbar.add_action("Flip H", self.flip_horizontal, tooltip_key="Flip horizontal")
        toolbar.add_action("Flip V", self.flip_vertical, tooltip_key="Flip vertical")
        toolbar.addSeparator()

        toolbar.add_action("Crop Drawn", self.apply_crop, tooltip_key="Crop")
        toolbar.add_action("Crop Presets...", self.crop_preset, tooltip_key="Crop preset")
        toolbar.add_action("Circle Avatar Crop", self.circle_crop, tooltip_key="Circle crop")
        toolbar.add_action("Resize...", self.resize_image, tooltip_key="Resize")
        toolbar.add_action("Add Border...", self.add_border, tooltip_key="Add border / frame")
        toolbar.addSeparator()

        toolbar.add_action("Blur Selection", self.blur_selection, tooltip_key="Blur")
        toolbar.add_action("Pixelate Selection", self.pixelate_selection, tooltip_key="Pixelate")
        toolbar.add_action("Remove Background", self.remove_background, tooltip_key="Remove background")
        toolbar.addSeparator()

        toolbar.add_action("Add Layer...", self.add_image_layer, tooltip_key="Add layer")
        toolbar.add_action("Batch...", self.batch_process, tooltip_key="Batch process images")
        toolbar.add_action("Extract Text (OCR)...", self.extract_ocr_text, tooltip_key="OCR image")
        toolbar.add_action("ASCII Art...", self.export_ascii_art)
        toolbar.add_action("Build GIF...", self.build_gif_from_files)
        toolbar.add_action("Extract GIF Frames...", self.extract_gif_frames_to_files)
        toolbar.add_action("GIF to Video...", self.convert_gif_to_video)

        toolbar.finalize()

        layout.addWidget(self.canvas, stretch=1)

        self.status_label = QLabel("No image open - drag and drop an image or click Open")
        layout.addWidget(self.status_label)

    def _apply_crop_frame(self, crop_item: Optional[Any]) -> None:
        """Handler for crop guide adjustments."""
        if crop_item is not None:
            r = crop_item.rect()
            self.status_label.setText(f"Crop guide: {int(r.width())}x{int(r.height())} - Click 'Crop Drawn' or 'Blur Selection'")

    def _on_selection_changed(self, item: Optional[Any]) -> None:
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

    # ---------- whole-composition undo / redo ----------

    def _snapshot_edit(self) -> Optional[Dict[str, Any]]:
        if self.pil_image is None:
            return None
        layers = []
        for layer in self.canvas.image_layers():
            layers.append({
                "image": _qimage_to_pil(layer.pixmap().toImage()),
                "pos": (layer.pos().x(), layer.pos().y()),
                "opacity": layer.opacity(),
            })
        return {
            "base": self.pil_image.copy(),
            "layers": layers,
            "annotations": self.canvas.get_annotations(),
        }

    def _reset_edit_history(self) -> None:
        snapshot = self._snapshot_edit()
        self._edit_history = [snapshot] if snapshot else []
        self._edit_future = []

    def _commit_edit(self) -> None:
        if self._restoring_edit or self.pil_image is None:
            return
        snapshot = self._snapshot_edit()
        if snapshot is None:
            return
        self._edit_history.append(snapshot)
        self._edit_history = self._edit_history[-30:]
        self._edit_future = []

    def undo_edit(self) -> None:
        if len(self._edit_history) < 2:
            return
        self._edit_future.append(self._edit_history.pop())
        self._restore_edit(self._edit_history[-1])

    def redo_edit(self) -> None:
        if not self._edit_future:
            return
        snapshot = self._edit_future.pop()
        self._edit_history.append(snapshot)
        self._restore_edit(snapshot)

    def _restore_edit(self, snapshot: Dict[str, Any]) -> None:
        self._restoring_edit = True
        try:
            self.pil_image = snapshot["base"].copy()
            self._refresh_canvas()
            for layer_data in snapshot["layers"]:
                layer = self.canvas.add_image_layer(_pil_to_qimage(layer_data["image"]))
                layer.setPos(*layer_data["pos"])
                layer.setOpacity(layer_data["opacity"])
            self.canvas.load_annotations(snapshot["annotations"])
        finally:
            self._restoring_edit = False

    def _show_layer_context_menu(self, layer: Any, screen_pos: QPointF) -> None:
        """Right-click command surface for direct per-image editing."""
        layer.setSelected(True)
        menu = QMenu(self)
        menu.addAction("Adjust tone && colors", self.adjust_selected_layer)
        menu.addAction("Auto enhance", self.auto_enhance)
        menu.addSeparator()
        menu.addAction("Resize layer", self.resize_selected_layer)
        menu.addAction("Rotate layer", self.rotate_selected_layer)
        menu.addAction("Crop layer with drag handles", self.begin_selected_layer_crop)
        menu.addAction("Circular avatar crop", self.circle_crop)
        menu.addSeparator()
        menu.addAction("Flip horizontally", self.flip_selected_layer)
        menu.addAction("Flip vertically", self.flip_selected_layer_vertically)
        menu.addSeparator()
        menu.addAction("Duplicate", self.duplicate_selected_layer)
        menu.addAction("Bring to front", self.bring_layer_to_front)
        menu.addAction("Send to back", self.send_layer_to_back)
        menu.addSeparator()
        menu.addAction("Delete", self.delete_selected_layer)
        menu.exec(screen_pos)

    # ---------- load / display ----------

    def open_image(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Images", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff *.gif *.heic *.heif *.avif *.svg *.psd *.cr2 *.cr3 *.nef *.arw *.dng *.raf *.orf *.rw2 *.pef *.srw)"
        )
        if not paths:
            return
        self.load_file_path(paths[0], additional_paths=paths[1:])

    def load_pil_image(self, pil_image: Image.Image, label: str = "Screenshot") -> None:
        """Load an in-memory PIL image directly into the canvas."""
        self.pil_image = pil_image.convert("RGBA")
        self.current_path = None
        self._refresh_canvas()
        self._reset_edit_history()
        self.status_label.setText(
            f"{label} - {self.pil_image.size[0]}x{self.pil_image.size[1]}"
        )

    def take_screenshot(self) -> None:
        """Open interactive screenshot dialog and load result directly into the canvas."""
        dialog = ScreenshotDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.captured_image:
            self.load_pil_image(dialog.captured_image, "Screenshot")

    def load_file(self, path: str) -> None:
        self.load_file_path(path)

    def load_file_path(self, path: str, additional_paths: Optional[List[str]] = None) -> None:
        """Open a primary image and optional secondary layers directly from a path."""
        self.current_path = path
        images = []
        paths = [path, *(additional_paths or [])]
        for p in paths:
            try:
                source = image_ops.load_image(p)
                images.append((p, source.convert("RGBA")))
            except Exception as exc:
                QMessageBox.critical(self, "Could not open image", f"Error opening {p}: {exc}")
                return
        if not images:
            return

        if len(images) == 1:
            self.pil_image = images[0][1]
        else:
            self.pil_image = Image.new(
                "RGBA",
                (max(image.width for _, image in images), max(image.height for _, image in images)),
                (0, 0, 0, 0),
            )
        self._refresh_canvas()
        if len(images) > 1:
            for index, (_, image) in enumerate(images):
                layer = self.canvas.add_image_layer(_pil_to_qimage(image))
                layer.setPos(index * 24, index * 24)
        self._reset_edit_history()
        self.status_label.setText(
            f"{os.path.basename(path)} - {self.pil_image.size[0]}x{self.pil_image.size[1]}"
        )

    def copy_to_clipboard(self) -> None:
        """Copy the composite image to the system clipboard."""
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        self._bake_annotations_into_pil()
        qimg = _pil_to_qimage(self.pil_image)
        QGuiApplication.clipboard().setImage(qimg)
        self._refresh_canvas()
        self._commit_edit()
        self.status_label.setText("Copied image to clipboard (ready to paste in Slack/Discord/Docs)")

    def _refresh_canvas(self) -> None:
        self.canvas._suspend_history = True
        try:
            self.canvas.set_image(_pil_to_qimage(self.pil_image))
        finally:
            self.canvas._suspend_history = False

    def _bake_annotations_into_pil(self) -> None:
        """Rasterize current canvas annotations onto self.pil_image permanently."""
        self.canvas._suspend_history = True
        try:
            image_layers = self.canvas.image_layers()
            if image_layers:
                composite = self.pil_image.convert("RGBA")
                for layer in image_layers:
                    position = layer.scenePos()
                    overlay = _qimage_to_pil(layer.pixmap().toImage())
                    if layer.opacity() < 1:
                        alpha = overlay.getchannel("A").point(lambda value: round(value * layer.opacity()))
                        overlay.putalpha(alpha)
                    composite.paste(overlay, (round(position.x()), round(position.y())), overlay)
                self.pil_image = composite
                self.canvas.clear_image_layers()

            anns = [a for a in self.canvas.get_annotations() if a["type"] not in ("crop", "redact")]
            if anns:
                img = self.pil_image.copy()
                draw = ImageDraw.Draw(img, "RGBA")
                for ann in anns:
                    color = tuple(ann.get("qcolor", (220, 40, 40, 255)))
                    if ann["type"] == "rect":
                        x, y, w, h = ann["rect"]
                        draw.rectangle([x, y, x + w, y + h], outline=color, width=ann.get("width", 2))
                    elif ann["type"] == "text":
                        font = _load_pil_font(
                            ann.get("font_size", 14),
                            family=ann.get("font_family", "Helvetica"),
                            bold=ann.get("bold", False),
                            italic=ann.get("italic", False),
                        )
                        _draw_text_with_spacing(
                            draw, ann["pos"], ann["text"], font, color,
                            ann.get("letter_spacing", 100),
                        )
                    elif ann["type"] == "freehand":
                        pts = ann["points"]
                        if len(pts) > 1:
                            draw.line(pts, fill=color, width=ann.get("width", 2))
                    elif ann["type"] == "arrow":
                        start = ann.get("start", (0, 0))
                        end = ann.get("end", (0, 0))
                        width = ann.get("width", 3)
                        draw.line([start, end], fill=color, width=width)
                        x1, y1 = start
                        x2, y2 = end
                        dx, dy = x2 - x1, y2 - y1
                        length = (dx * dx + dy * dy) ** 0.5
                        if length > 4:
                            head_len = min(22.0, max(8.0, length * 0.25))
                            ux, uy = dx / length, dy / length
                            perp_x, perp_y = -uy, ux
                            wing_w = head_len * 0.45
                            base_x = x2 - ux * head_len
                            base_y = y2 - uy * head_len
                            w1 = (base_x + perp_x * wing_w, base_y + perp_y * wing_w)
                            w2 = (base_x - perp_x * wing_w, base_y - perp_y * wing_w)
                            draw.line([w1, (x2, y2), w2], fill=color, width=width)
                self.pil_image = img
            self.canvas.clear_annotations()
        finally:
            self.canvas._suspend_history = False

    # ---------- image layers & positioning ----------

    def add_image_layer(self) -> None:
        if self.pil_image is None:
            QMessageBox.warning(self, "No base image", "Open an image before adding another image layer.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Add Image Layer", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)"
        )
        if not path:
            return
        try:
            with Image.open(path) as source:
                layer = source.convert("RGBA")
            self.canvas.add_image_layer(_pil_to_qimage(layer))
            self._commit_edit()
            self.status_label.setText(f"Added image layer: {os.path.basename(path)} - drag to reposition")
        except Exception as exc:
            QMessageBox.critical(self, "Could not add image layer", str(exc))

    def bring_layer_to_front(self) -> None:
        if not self.canvas.bring_selected_image_layer_to_front():
            QMessageBox.information(self, "Select an image layer", "Click an added image layer first.")
        else:
            self._commit_edit()

    def send_layer_to_back(self) -> None:
        if not self.canvas.send_selected_image_layer_to_back():
            QMessageBox.information(self, "Select an image layer", "Click an added image layer first.")
        else:
            self._commit_edit()

    def duplicate_selected_layer(self) -> None:
        layer = self._selected_layer_or_message()
        if layer is None:
            return
        duplicate = self.canvas.add_image_layer(layer.pixmap().toImage())
        duplicate.setPos(layer.pos().x() + 20, layer.pos().y() + 20)
        duplicate.setOpacity(layer.opacity())
        self._commit_edit()
        self.status_label.setText("Duplicated selected image layer")

    def _selected_layer_or_message(self) -> Optional[Any]:
        layer = self.canvas.selected_image_layer()
        if layer is None:
            QMessageBox.information(self, "Select an image layer", "Click an added image layer first.")
        return layer

    @staticmethod
    def _replace_layer_image(layer: Any, image: Image.Image, keep_center: bool = True) -> None:
        """Swap one layer's pixel content while preserving its canvas place."""
        old_size = layer.pixmap().size()
        old_pos = layer.pos()
        layer.setPixmap(QPixmap.fromImage(_pil_to_qimage(image)))
        if keep_center:
            new_size = layer.pixmap().size()
            layer.setPos(
                old_pos.x() + (old_size.width() - new_size.width()) / 2,
                old_pos.y() + (old_size.height() - new_size.height()) / 2,
            )

    def resize_selected_layer(self) -> None:
        layer = self._selected_layer_or_message()
        if layer is None:
            return
        dialog = ResizeDialog((layer.pixmap().width(), layer.pixmap().height()), self)
        dialog.setWindowTitle("Resize Image Layer")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        width, height, keep_aspect = dialog.values()
        image = _qimage_to_pil(layer.pixmap().toImage())
        self._replace_layer_image(layer, image_ops.resize_image(image, width, height, keep_aspect))
        self._commit_edit()
        self.status_label.setText("Resized selected image layer")

    def rotate_selected_layer(self) -> None:
        layer = self._selected_layer_or_message()
        if layer is None:
            return
        degrees, accepted = QInputDialog.getDouble(
            self, "Rotate Image Layer", "Degrees clockwise:", 90, -360, 360, 1
        )
        if not accepted or degrees == 0:
            return
        image = _qimage_to_pil(layer.pixmap().toImage())
        self._replace_layer_image(layer, image_ops.rotate_image(image, degrees))
        self._commit_edit()
        self.status_label.setText(f"Rotated selected image layer {degrees:g}°")

    def begin_selected_layer_crop(self) -> None:
        """Enter direct crop mode: drag the crop box over the selected layer."""
        layer = self._selected_layer_or_message()
        if layer is None:
            return
        self._crop_target_layer = layer
        self.canvas.set_tool(Tool.CROP)
        self.status_label.setText("Drag a crop rectangle on the selected layer. It will crop when you release.")

    def _apply_drawn_layer_crop(self, scene_rect: Optional[Tuple[float, float, float, float]]) -> None:
        layer = self._crop_target_layer
        self._crop_target_layer = None
        self.canvas.set_tool(Tool.SELECT)
        self.tool_actions[Tool.SELECT].setChecked(True)
        self.canvas.clear_crop_guide()
        if layer is None or layer.scene() is None or scene_rect is None:
            return
        x, y, width, height = scene_rect
        layer_x, layer_y = layer.scenePos().x(), layer.scenePos().y()
        left = max(0, round(x - layer_x))
        top = max(0, round(y - layer_y))
        right = min(layer.pixmap().width(), round(x + width - layer_x))
        bottom = min(layer.pixmap().height(), round(y + height - layer_y))
        if right - left < 1 or bottom - top < 1:
            self.status_label.setText("Crop selection did not overlap the selected image layer")
            return
        image = _qimage_to_pil(layer.pixmap().toImage())
        layer.setPos(layer.pos().x() + left, layer.pos().y() + top)
        self._replace_layer_image(layer, image_ops.crop_image(image, (left, top, right, bottom)), keep_center=False)
        self._commit_edit()
        self.status_label.setText("Cropped selected image layer - Undo restores it")

    def flip_selected_layer(self) -> None:
        layer = self._selected_layer_or_message()
        if layer is None:
            return
        image = _qimage_to_pil(layer.pixmap().toImage())
        self._replace_layer_image(layer, image_ops.flip_image(image, horizontal=True), keep_center=False)
        self._commit_edit()
        self.status_label.setText("Flipped selected image layer horizontally")

    def flip_selected_layer_vertically(self) -> None:
        layer = self._selected_layer_or_message()
        if layer is None:
            return
        image = _qimage_to_pil(layer.pixmap().toImage())
        self._replace_layer_image(layer, image_ops.flip_image(image, horizontal=False), keep_center=False)
        self._commit_edit()
        self.status_label.setText("Flipped selected image layer vertically")

    def adjust_selected_layer(self) -> None:
        layer = self._selected_layer_or_message()
        if layer is None:
            return
        dialog = PhotoAdjustDialog(opacity=layer.opacity(), show_opacity=True, parent=self)
        dialog.setWindowTitle("Adjust Selected Layer")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        vals = dialog.values()
        image = _qimage_to_pil(layer.pixmap().toImage())
        if vals["preset"] != "Custom / Manual":
            adjusted = image_ops.apply_filter_preset(image, vals["preset"])
        else:
            adjusted = image_ops.adjust_image(
                image, brightness=vals["brightness"], contrast=vals["contrast"],
                saturation=vals["saturation"], sharpness=vals["sharpness"],
                blur_radius=vals["blur"], grayscale=vals["grayscale"], warmth=vals["warmth"]
            )
        self._replace_layer_image(layer, adjusted, keep_center=False)
        layer.setOpacity(vals["opacity"] / 100)
        self._commit_edit()
        self.status_label.setText("Adjusted selected image layer")

    def delete_selected_layer(self) -> None:
        """Delete the selected layer or annotation, then save an undo point."""
        if self.canvas.selected_image_layer() is not None:
            self.canvas.delete_selected()
            self._commit_edit()
            return
        self.canvas.delete_selected()

    # ---------- photo editing operations ----------

    def auto_enhance(self) -> None:
        """1-click color, contrast, and histogram balance."""
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        layer = self.canvas.selected_image_layer()
        if layer is not None:
            image = _qimage_to_pil(layer.pixmap().toImage())
            self._replace_layer_image(layer, image_ops.auto_enhance(image), keep_center=False)
            self._commit_edit()
            self.status_label.setText("Auto-enhanced selected layer")
        else:
            self._bake_annotations_into_pil()
            self.pil_image = image_ops.auto_enhance(self.pil_image)
            self._refresh_canvas()
            self._commit_edit()
            self.status_label.setText("Auto-enhanced photo colors and contrast")

    def adjust_photo(self) -> None:
        """Adjust brightness, contrast, saturation, sharpness, warmth, and presets."""
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        layer = self.canvas.selected_image_layer()
        dialog = PhotoAdjustDialog(opacity=layer.opacity() if layer else 1.0, show_opacity=layer is not None, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        vals = dialog.values()
        preset = vals["preset"]
        if layer is not None:
            image = _qimage_to_pil(layer.pixmap().toImage())
            if preset != "Custom / Manual":
                adjusted = image_ops.apply_filter_preset(image, preset)
            else:
                adjusted = image_ops.adjust_image(
                    image, brightness=vals["brightness"], contrast=vals["contrast"],
                    saturation=vals["saturation"], sharpness=vals["sharpness"],
                    blur_radius=vals["blur"], grayscale=vals["grayscale"], warmth=vals["warmth"]
                )
            self._replace_layer_image(layer, adjusted, keep_center=False)
            layer.setOpacity(vals["opacity"] / 100)
            self._commit_edit()
            self.status_label.setText("Adjusted selected image layer")
        else:
            self._bake_annotations_into_pil()
            if preset != "Custom / Manual":
                self.pil_image = image_ops.apply_filter_preset(self.pil_image, preset)
            else:
                self.pil_image = image_ops.adjust_image(
                    self.pil_image, brightness=vals["brightness"], contrast=vals["contrast"],
                    saturation=vals["saturation"], sharpness=vals["sharpness"],
                    blur_radius=vals["blur"], grayscale=vals["grayscale"], warmth=vals["warmth"]
                )
            self._refresh_canvas()
            self._commit_edit()
            self.status_label.setText("Adjusted photo tones and colors")

    def rotate_90_cw(self) -> None:
        """Rotate 90° clockwise."""
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        layer = self.canvas.selected_image_layer()
        if layer is not None:
            image = _qimage_to_pil(layer.pixmap().toImage())
            self._replace_layer_image(layer, image_ops.rotate_image(image, 90), keep_center=False)
            self._commit_edit()
            self.status_label.setText("Rotated selected layer 90° clockwise")
        else:
            self._bake_annotations_into_pil()
            self.pil_image = image_ops.rotate_image(self.pil_image, 90)
            self._refresh_canvas()
            self._commit_edit()
            self.status_label.setText("Rotated photo 90° clockwise")

    def rotate_90_ccw(self) -> None:
        """Rotate 90° counter-clockwise."""
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        layer = self.canvas.selected_image_layer()
        if layer is not None:
            image = _qimage_to_pil(layer.pixmap().toImage())
            self._replace_layer_image(layer, image_ops.rotate_image(image, -90), keep_center=False)
            self._commit_edit()
            self.status_label.setText("Rotated selected layer 90° counter-clockwise")
        else:
            self._bake_annotations_into_pil()
            self.pil_image = image_ops.rotate_image(self.pil_image, -90)
            self._refresh_canvas()
            self._commit_edit()
            self.status_label.setText("Rotated photo 90° counter-clockwise")

    def rotate_custom(self) -> None:
        """Rotate or straighten by custom degree angle."""
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        degrees, accepted = QInputDialog.getDouble(
            self, "Rotate / Straighten", "Degrees clockwise (negative for counter-clockwise):", 0, -360, 360, 1
        )
        if not accepted or degrees == 0:
            return
        layer = self.canvas.selected_image_layer()
        if layer is not None:
            image = _qimage_to_pil(layer.pixmap().toImage())
            self._replace_layer_image(layer, image_ops.rotate_image(image, degrees), keep_center=False)
            self._commit_edit()
            self.status_label.setText(f"Rotated selected layer {degrees:g}°")
        else:
            self._bake_annotations_into_pil()
            self.pil_image = image_ops.rotate_image(self.pil_image, degrees)
            self._refresh_canvas()
            self._commit_edit()
            self.status_label.setText(f"Rotated photo {degrees:g}°")

    def flip_horizontal(self) -> None:
        """Flip left-to-right."""
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        layer = self.canvas.selected_image_layer()
        if layer is not None:
            image = _qimage_to_pil(layer.pixmap().toImage())
            self._replace_layer_image(layer, image_ops.flip_image(image, horizontal=True), keep_center=False)
            self._commit_edit()
            self.status_label.setText("Flipped selected layer horizontally")
        else:
            self._bake_annotations_into_pil()
            self.pil_image = image_ops.flip_image(self.pil_image, horizontal=True)
            self._refresh_canvas()
            self._commit_edit()
            self.status_label.setText("Flipped photo horizontally")

    def flip_vertical(self) -> None:
        """Flip top-to-bottom."""
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        layer = self.canvas.selected_image_layer()
        if layer is not None:
            image = _qimage_to_pil(layer.pixmap().toImage())
            self._replace_layer_image(layer, image_ops.flip_image(image, horizontal=False), keep_center=False)
            self._commit_edit()
            self.status_label.setText("Flipped selected layer vertically")
        else:
            self._bake_annotations_into_pil()
            self.pil_image = image_ops.flip_image(self.pil_image, horizontal=False)
            self._refresh_canvas()
            self._commit_edit()
            self.status_label.setText("Flipped photo vertically")

    def circle_crop(self) -> None:
        """Crop to centered circle avatar cutout."""
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        layer = self.canvas.selected_image_layer()
        if layer is not None:
            image = _qimage_to_pil(layer.pixmap().toImage())
            self._replace_layer_image(layer, image_ops.circle_crop_image(image), keep_center=True)
            self._commit_edit()
            self.status_label.setText("Applied circular crop to selected layer")
        else:
            self._bake_annotations_into_pil()
            self.pil_image = image_ops.circle_crop_image(self.pil_image)
            self._refresh_canvas()
            self._commit_edit()
            self.status_label.setText("Applied circular avatar crop - save as PNG/WEBP to preserve transparency")

    def crop_preset(self) -> None:
        """Crop to predefined aspect ratio (1:1, 4:5, 16:9, etc.)."""
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        dialog = AspectCropDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        ratio_w, ratio_h = dialog.selected_ratio()
        self._bake_annotations_into_pil()
        box = image_ops.aspect_ratio_crop_box(self.pil_image.width, self.pil_image.height, ratio_w, ratio_h)
        self.pil_image = image_ops.crop_image(self.pil_image, box)
        self._refresh_canvas()
        self._commit_edit()
        self.status_label.setText(f"Cropped to aspect ratio {ratio_w}:{ratio_h}")

    def add_border(self) -> None:
        """Add solid frame or Polaroid frame."""
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        dialog = BorderDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        size, color, polaroid = dialog.values()
        self._bake_annotations_into_pil()
        self.pil_image = image_ops.add_border(self.pil_image, border_size=size, color=color, polaroid=polaroid)
        self._refresh_canvas()
        self._commit_edit()
        self.status_label.setText("Added frame border to image")

    def blur_selection(self) -> None:
        """Blur region marked by crop guide for privacy/redaction."""
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        crop_rect = self.canvas.current_crop_rect()
        if crop_rect is None:
            QMessageBox.information(self, "Mark area to blur", "Drag a box on the canvas using Rect tool or crop guide to mark the sensitive area first.")
            return
        x, y, w, h = crop_rect
        box = (int(x), int(y), int(x + w), int(y + h))
        self._bake_annotations_into_pil()
        self.pil_image = image_ops.blur_region(self.pil_image, box, radius=18)
        self._refresh_canvas()
        self._commit_edit()
        self.status_label.setText("Blurred sensitive region")

    def pixelate_selection(self) -> None:
        """Pixelate region marked by crop guide for redaction."""
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        crop_rect = self.canvas.current_crop_rect()
        if crop_rect is None:
            QMessageBox.information(self, "Mark area to pixelate", "Drag a box on the canvas using Rect tool or crop guide to mark the sensitive area first.")
            return
        x, y, w, h = crop_rect
        box = (int(x), int(y), int(x + w), int(y + h))
        self._bake_annotations_into_pil()
        self.pil_image = image_ops.pixelate_region(self.pil_image, box, pixel_size=12)
        self._refresh_canvas()
        self._commit_edit()
        self.status_label.setText("Pixelated sensitive region")

    # ---------- save ----------

    def save_as(self) -> None:
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        self._bake_annotations_into_pil()
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Image As", "", "PNG (*.png);;JPEG (*.jpg *.jpeg);;WEBP (*.webp);;TIFF (*.tiff);;BMP (*.bmp);;GIF (*.gif);;PDF (*.pdf)"
        )
        if not out_path:
            return
        image_ops.save_image(self.pil_image, out_path, format=format_from_path(out_path))
        self._refresh_canvas()
        QMessageBox.information(self, "Saved", f"Saved to {out_path}")

    def export_ascii_art(self) -> None:
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        self._bake_annotations_into_pil()
        width, ok = QInputDialog.getInt(self, "ASCII Art", "Output width (characters):", 100, 20, 400, 10)
        if not ok:
            return
        presets = list(image_ops.ASCII_CHARSET_PRESETS.keys())
        preset_name, ok = QInputDialog.getItem(self, "ASCII Art", "Character set:", presets, 0, False)
        if not ok:
            return
        contrast, ok = QInputDialog.getInt(self, "ASCII Art", "Contrast (100 = unchanged):", 100, 10, 300, 10)
        if not ok:
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Export ASCII Art", "ascii_art.txt", "Text File (*.txt)")
        if not out_path:
            return
        try:
            charset = image_ops.ASCII_CHARSET_PRESETS[preset_name]
            image_ops.save_ascii_art(self.pil_image, out_path, width=width, charset=charset, contrast=float(contrast))
            QMessageBox.information(self, "Saved", f"ASCII art saved to {out_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def convert_gif_to_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Animated GIF", "", "GIF Image (*.gif)")
        if not path:
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Video", "animation.mp4", "MP4 Video (*.mp4)")
        if not out_path:
            return
        try:
            image_ops.gif_to_video(path, out_path)
            QMessageBox.information(self, "Saved", f"Video saved to {out_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Conversion Failed", str(exc))

    def extract_gif_frames_to_files(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Animated GIF", "", "GIF Image (*.gif)")
        if not path:
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Choose Output Folder for Frames")
        if not out_dir:
            return
        try:
            frames = image_ops.extract_gif_frames(path)
            base = os.path.splitext(os.path.basename(path))[0]
            for idx, frame in enumerate(frames):
                image_ops.save_image(frame, os.path.join(out_dir, f"{base}_frame_{idx:03d}.png"), format="PNG")
            QMessageBox.information(self, "Extracted", f"Extracted {len(frames)} frame(s) to {out_dir}")
        except Exception as exc:
            QMessageBox.critical(self, "Extraction Failed", str(exc))

    def build_gif_from_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Frames (in order)", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)"
        )
        if not paths:
            return
        duration_ms, ok = QInputDialog.getInt(self, "Build GIF", "Frame duration (milliseconds):", 100, 10, 5000, 10)
        if not ok:
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Animated GIF", "animation.gif", "GIF Image (*.gif)")
        if not out_path:
            return
        try:
            frames = [image_ops.load_image(p) for p in paths]
            image_ops.frames_to_gif(frames, out_path, duration_ms=duration_ms)
            QMessageBox.information(self, "Saved", f"Animated GIF saved to {out_path} ({len(frames)} frame(s))")
        except Exception as exc:
            QMessageBox.critical(self, "Build Failed", str(exc))

    # ---------- crop / resize ----------

    def apply_crop(self) -> None:
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        crop_rect = self.canvas.current_crop_rect()
        if crop_rect is None:
            QMessageBox.warning(self, "No crop selected", "Draw a crop rectangle first.")
            return
        self._bake_annotations_into_pil()
        x, y, w, h = crop_rect
        box = (int(x), int(y), int(x + w), int(y + h))
        self.pil_image = image_ops.crop_image(self.pil_image, box)
        self._refresh_canvas()
        self._commit_edit()
        self.status_label.setText(f"Cropped to {self.pil_image.width}x{self.pil_image.height}")

    def resize_image(self) -> None:
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        dialog = ResizeDialog(self.pil_image.size, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        width, height, keep_aspect = dialog.values()
        self._bake_annotations_into_pil()
        self.pil_image = image_ops.resize_image(self.pil_image, width, height, keep_aspect)
        self._refresh_canvas()
        self._commit_edit()
        self.status_label.setText(f"Resized image to {self.pil_image.width}x{self.pil_image.height}")

    def compress_convert(self) -> None:  # noqa: 21 (invoked dynamically via tool registry getattr dispatch)
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        dialog = CompressConvertDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        fmt, quality = dialog.values()
        ext = extension_for_format(fmt)
        out_path, _ = QFileDialog.getSaveFileName(self, "Save As", "", f"*{ext}")
        if not out_path:
            return
        self._bake_annotations_into_pil()
        self._commit_edit()
        image_ops.save_image(self.pil_image, out_path, format=fmt, quality=quality)
        QMessageBox.information(self, "Saved", f"Saved {fmt} to {out_path}")

    # ---------- local AI image tools ----------

    def remove_background(self) -> None:
        """Run the optional local model without freezing the image editor."""
        if self.pil_image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        settings = QSettings("FOSSEverything", "FOSSEverything")
        saved_model = settings.value("background_removal/model", "bria-rmbg")
        dialog = BackgroundRemovalDialog(image_ops._normalize_model_name(saved_model), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        model_name = dialog.selected_model()
        if model_name not in image_ops.BACKGROUND_REMOVAL_MODELS:
            model_name = "bria-rmbg"
        settings.setValue("background_removal/model", model_name)
        acknowledged = settings.value("background_removal/model_notice_seen", False, type=bool)
        if not acknowledged:
            answer = QMessageBox.question(
                self,
                "Remove background locally",
                "This uses a local AI model. Your image is never uploaded. "
                "The model may download once on first use, then is reused on this computer. Continue",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            settings.setValue("background_removal/model_notice_seen", True)

        self._bake_annotations_into_pil()
        self._progress_dialog = QProgressDialog("Working...", None, 0, 0, self)
        self._progress_dialog.setWindowTitle("Working...")
        self._progress_dialog.setLabelText("Working...\nRemoving background locally. This may take a moment while the model loads.")
        self._progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._progress_dialog.setMinimumDuration(0)
        self._progress_dialog.setCancelButton(None)
        self._progress_dialog.setAutoClose(False)
        self._progress_dialog.show()
        QGuiApplication.processEvents()
        self._worker = WorkerThread(image_ops.remove_background, self.pil_image.copy(), model_name)
        self._worker.finished_ok.connect(self._on_remove_background_done)
        self._worker.failed.connect(self._on_remove_background_failed)
        self._worker.start()

    def _on_remove_background_done(self, image: Image.Image) -> None:
        self._progress_dialog.close()
        self.pil_image = image.convert("RGBA")
        self._refresh_canvas()
        self._commit_edit()
        self.status_label.setText("Background removed - save as PNG or WEBP to keep transparency")

    def _on_remove_background_failed(self, message: str) -> None:
        self._progress_dialog.close()
        self._commit_edit()
        QMessageBox.critical(self, "Background removal failed", message)

    # ---------- batch ----------

    def batch_process(self) -> None:
        dialog = BatchDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        options = dialog.get_options()
        if not options["paths"]:
            QMessageBox.warning(self, "No files", "Add at least one file.")
            return
        if options["remove_background_enabled"]:
            settings = QSettings("FOSSEverything", "FOSSEverything")
            settings.setValue("background_removal/model", options["bg_model"])
            acknowledged = settings.value("background_removal/model_notice_seen", False, type=bool)
            if not acknowledged:
                answer = QMessageBox.question(
                    self,
                    "Remove background locally",
                    "This uses a local AI model. Your images are never uploaded. "
                    "The model may download once on first use, then is reused on this computer. Continue",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
                settings.setValue("background_removal/model_notice_seen", True)
        out_dir = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if not out_dir:
            return

        self._progress_dialog = QProgressDialog(
            "Processing images...", None, 0, len(options["paths"]), self
        )
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()

        batch_options = image_ops.BatchOptions(
            target_format=options["target_format"],
            quality=options["quality"],
            resize_to=options["resize_to"],
            remove_background_enabled=options["remove_background_enabled"],
            bg_model=options["bg_model"],
        )
        self._worker = WorkerThread(
            image_ops.batch_process,
            options["paths"],
            out_dir,
            batch_options,
        )
        self._worker.progress.connect(lambda i, t, name: self._progress_dialog.setValue(i))
        self._worker.finished_ok.connect(self._on_batch_done)
        self._worker.failed.connect(self._on_batch_failed)
        self._worker.start()

    def _on_batch_done(self, output_paths: list) -> None:
        self._progress_dialog.close()
        QMessageBox.information(self, "Batch complete", f"Processed {len(output_paths)} file(s).")

    def _on_batch_failed(self, message: str) -> None:
        self._progress_dialog.close()
        QMessageBox.critical(self, "Batch failed", message)

    def extract_ocr_text(self) -> None:
        """Extract text from the active image or drawn crop region via OCR."""
        img = None
        # Check if there is an active crop frame to extract text from a specific region
        if self._active_crop_frame is not None:
            r = self._active_crop_frame.rect()
            comp = self.canvas.render_composite_image()
            if comp:
                x0 = max(0, int(r.left()))
                y0 = max(0, int(r.top()))
                x1 = min(comp.width, int(r.right()))
                y1 = min(comp.height, int(r.bottom()))
                if x1 > x0 and y1 > y0:
                    img = comp.crop((x0, y0, x1, y1))
        if img is None:
            img = self.canvas.render_composite_image() or self.pil_image

        if img is None:
            QMessageBox.warning(self, "No Image", "Open or paste an image first.")
            return

        from app.features.ocr import ops as ocr_ops  # noqa: 13 (keeps pymupdf out of every image tab's cold-start import)
        self._progress_dialog = QProgressDialog("Running OCR...", None, 0, 0, self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()
        self._ocr_worker = WorkerThread(ocr_ops.ocr_image, img, language="eng")
        self._ocr_worker.finished_ok.connect(self._on_extract_ocr_text_done)
        self._ocr_worker.failed.connect(self._on_extract_ocr_text_failed)
        self._ocr_worker.start()

    def _on_extract_ocr_text_failed(self, message: str) -> None:
        self._progress_dialog.close()
        QMessageBox.critical(self, "OCR Failed", message)

    def _on_extract_ocr_text_done(self, res: dict) -> None:
        self._progress_dialog.close()
        txt = res.get("text", "").strip()
        if not txt:
            QMessageBox.information(self, "OCR Result", "No text was detected in the image.")
            return

        # Show text in a modal dialog with copy / save
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle("Extracted Text (OCR)")
            dlg.resize(500, 360)
            layout = QVBoxLayout(dlg)

            stats = QLabel(f"Detected {len(res.get('words', []))} words / {len(txt)} characters:")
            stats.setStyleSheet("font-weight: 600;")
            layout.addWidget(stats)

            editor = QTextEdit()
            editor.setPlainText(txt)
            font = QFont("Consolas" if os.name == "nt" else "Monospace", scaled_font_size(10))
            editor.setFont(font)
            layout.addWidget(editor, stretch=1)

            btn_row = QHBoxLayout()
            copy_btn = QPushButton("Copy to Clipboard")
            copy_btn.setToolTip(get_tooltip_for("Copy to Clipboard"))
            def _copy() -> None:
                cb = QGuiApplication.clipboard()
                if cb:
                    cb.setText(editor.toPlainText())
                    QMessageBox.information(dlg, "Copied", "Text copied to clipboard.")
            copy_btn.clicked.connect(_copy)
            btn_row.addWidget(copy_btn)

            save_btn = QPushButton("Save As .txt...")
            apply_standard_icon(save_btn, "Save As .txt...")
            save_btn.setToolTip(get_tooltip_for("Save as .txt"))
            def _save() -> None:
                path, _ = QFileDialog.getSaveFileName(dlg, "Save Text", "extracted_text.txt", "Text Files (*.txt)")
                if path:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(editor.toPlainText())
                    QMessageBox.information(dlg, "Saved", f"Saved to {path}")
            save_btn.clicked.connect(_save)
            btn_row.addWidget(save_btn)

            close_btn = QPushButton("Close")
            close_btn.setToolTip(get_tooltip_for("Close"))
            close_btn.clicked.connect(dlg.accept)
            btn_row.addStretch(1)
            btn_row.addWidget(close_btn)

            layout.addLayout(btn_row)
            dlg.exec()
        except Exception as exc:
            QMessageBox.critical(self, "OCR Failed", str(exc))

