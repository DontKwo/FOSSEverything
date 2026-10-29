"""Home workspace: visual launcher, local search, and pinned tools."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from typing import Callable, Optional

from PyQt6.QtCore import QEvent, QRectF, QSettings, QSize, Qt, pyqtSignal, QUrl
from PyQt6.QtGui import (
    QColor, QDesktopServices, QDragEnterEvent, QDropEvent, QFont, QIcon, QKeyEvent,
    QPainter, QPixmap, QPalette, QResizeEvent,
)
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidgetItem, QPushButton, QScrollArea, QSizePolicy, QStyle, QVBoxLayout, QWidget,
)

from app.core.customizable_toolbar import DragDropListWidget, build_dialog_panel
from app.core.theme import default_palette, resolved_palette, theme_signals
from app.core.tool_registry import ToolRegistry, text_matches
from app.core.tooltips import get_tooltip_for, keywords_tooltip, tooltip_search
from app.ui.ui_scaling import scaled_font_pt, scaled_font_size


@dataclass
class HomeAppOrderState:
    """Holds configuration for customizing home apps order and visibility."""
    apps: tuple['HomeApp', ...]
    custom_order: list[str]
    hidden_ids: list[str]
    pinned_ids: list[str]
    favorite_ids: list[str]
    sort_mode: str = "alphabetical"


@dataclass(frozen=True)
class HomeApp:
    """A workspace tile shown on the local FOSSEverything home screen."""

    id: str
    name: str
    category: str
    description: str
    keywords: tuple[str, ...]
    available: bool = False

    @property
    def search_text(self) -> str:
        return " ".join((self.name, self.category, self.description, *self.keywords)).lower()


HOME_APPS = (
    HomeApp("pdf", "PDF Editor", "Documents", "View, annotate, merge, split, compress, protect, watermark, number, and organize PDFs.", ("pdf", "document", "forms", "pages", "protect", "reorder", "watermark", "page numbers", "extract text"), True),
    HomeApp("images", "Image Editor", "Images", "Crop, resize, mark up, auto-enhance, filter, redact, screenshot, convert, and batch-process images.", ("image", "photo", "png", "jpg", "webp", "enhance", "filter", "screenshot", "snip"), True),
    HomeApp("media", "Video & Audio", "Media", "Trim, cut, extract audio, convert, compress, mute, and capture frames from video and audio locally.", ("video", "audio", "trim", "cut", "mp4", "mp3", "mov", "mkv", "compress", "extract audio", "snapshot"), True),
    HomeApp("ocr", "OCR & Text", "Documents", "Extract text from scans and images; create searchable PDFs completely offline.", ("ocr", "scan", "text", "markdown", "tesseract", "searchable pdf", "extract text"), True),
    HomeApp("resume", "Resume Builder", "Documents", "Build a master resume and check/uncheck bullets and reorder sections to tailor per job.", ("resume", "cv", "career", "builder", "tailor", "ats", "export pdf", "job"), True),
    HomeApp("word_counter", "Word Counter", "Documents", "Count words, sentences, reading time, and readability score for any document.", ("word count", "character count", "stats", "readability", "flesch", "reading time", "docx", "pdf"), True),
    HomeApp("playlist", "Playlist Porter", "Media", "Convert playlists between Spotify, YouTube, and YouTube Music: fetch tracks, open per-track search links, and export M3U8/CSV.", ("playlist", "spotify", "youtube", "music", "convert playlist", "m3u8", "csv", "sync"), True),
    HomeApp("converter", "File Converter", "Utilities", "Convert files single or in batch queues across images, PDFs, videos, audios, JSON, and CSV.", ("convert", "format", "export", "files", "batch convert", "queue"), True),
    HomeApp("metadata", "Metadata Tools", "Utilities", "Inspect, edit, or remove image/PDF/office/audio/video metadata before sharing.", ("metadata", "privacy", "exif", "strip", "docx", "pptx", "xlsx"), True),
    HomeApp("qr", "QR Codes & Barcodes", "Utilities", "Generate custom offline QR codes and scan/decode QR codes and barcodes from images/PDFs.", ("qr", "barcode", "wifi", "link", "generator", "offline", "logo", "svg", "scan", "decode"), True),
    HomeApp("renamer", "Batch Renamer", "Utilities", "Rename groups of files with regex, sequential numbers, prefixes, and live previews.", ("rename", "batch", "regex", "numbering", "bulk"), True),
    HomeApp("data", "Data Tools", "Data", "Format, pretty-print, minify, validate, JSONPath query, infer schema, and convert structured data.", ("json", "yaml", "csv", "xml", "format", "minify", "validate", "jsonpath", "schema"), True),
    HomeApp("markdown", "Markdown Studio", "Documents", "Side-by-side live Markdown editor and HTML preview with formatting insertion toolbar.", ("markdown", "md", "editor", "preview", "html", "table", "bold", "italic"), True),
    HomeApp("hash", "Hash & Checksum", "Utilities", "Compute file hashes and generate/verify directory checksum manifests offline.", ("hash", "checksum", "sha256", "md5", "sha512", "integrity", "verify", "manifest"), True),
    HomeApp("palette", "Color Palette", "Images", "Extract dominant color palettes and sample exact pixel colors with mouse eyedropper.", ("palette", "colors", "extract colors", "swatches", "dominant colors", "hex", "eyedropper"), True),
    HomeApp("collage", "Photo Collage", "Images", "Create customizable photo grid collages and side-by-side compositions.", ("collage", "grid", "combine photos", "side by side", "photo grid"), True),
    HomeApp("model3d", "3D Model Studio", "Utilities", "Cut, repair, measure, scale, and convert STL/OBJ/STEP 3D models locally.", ("3d", "stl", "obj", "step", "cad", "mesh", "cut plane", "slice"), True),
    HomeApp("text_tools", "Text Tools", "Utilities", "Case conversion, reversal, whitespace cleanup, line operations, regex replace, diff, and text/ASCII/binary conversion.", ("text", "case", "diff", "regex", "sort lines", "dedupe", "reverse", "camelcase", "snake_case", "ascii", "binary"), True),
    HomeApp("encoding", "Encoding / Decoding", "Utilities", "Encode and decode text and files between Base64, URL/percent-encoding, HTML entities, hex, and binary.", ("base64", "url encode", "html entities", "hex", "binary", "encode", "decode"), True),
    HomeApp("network_monitor", "Network Monitor", "Utilities", "Watch live outbound connections by process, flag new/unknown destinations, and search connection history.", ("network", "traffic", "connections", "firewall", "monitor", "process", "domain", "psutil"), True),
)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_HOME_ASSET_DIR = os.path.join(_PROJECT_ROOT, "assets", "home")


def _button_text(text: str) -> str:
    """Escape literal '&' so Qt doesn't turn it into a mnemonic underline."""
    return text.replace("&", "&&")


def _home_asset_path(app_id: str) -> str | None:
    for extension in (".png", ".jpg", ".jpeg", ".webp"):
        candidate = os.path.join(_HOME_ASSET_DIR, f"{app_id}{extension}")
        if os.path.exists(candidate):
            return candidate
    return None


def _monogram_pixmap(name: str, accent: str, on_accent: str, size: int) -> QPixmap:
    """A colored circular initial badge, used when an app has no bundled artwork."""
    letter = next((ch for ch in name if ch.isalnum()), "?").upper()
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(accent))
    painter.drawEllipse(QRectF(0, 0, size, size))
    font = QFont()
    font.setPointSizeF(size * 0.4)
    font.setWeight(QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(on_accent))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, letter)
    painter.end()
    return pixmap


def _app_icon(app_id: str, fallback: QIcon, size: QSize) -> QIcon:
    asset_path = _home_asset_path(app_id)
    if asset_path:
        pixmap = QPixmap(asset_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            return QIcon(scaled)
    return fallback




class AppTile(QFrame):
    """A smart-TV-style app tile with bundled local artwork."""

    open_requested = pyqtSignal(str)
    favorite_changed = pyqtSignal(str)
    pin_changed = pyqtSignal(str)

    def __init__(self, app: HomeApp, parent: Optional[QWidget] = None, theme_palette: Optional[dict[str, str]] = None) -> None:
        super().__init__(parent)
        self.app = app
        self.theme_palette = theme_palette or resolved_palette()
        self.setObjectName("appTile")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(96)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        base = self.theme_palette["panel"]
        window = self.theme_palette["background"]
        mid = self.theme_palette["border"]
        text = self.theme_palette["text"]
        muted = self.theme_palette["muted"]
        highlight = self.theme_palette["accent"]
        radius = 12
        self.setStyleSheet(
            f"QFrame#appTile {{ background: {window}; border: 1px solid {mid}; border-radius: {radius}px; }}"
            f"QFrame#appTile:hover {{ border: 1px solid {highlight}; background: {base}; }}"
            f"QFrame#appTile:focus {{ border: 2px solid {highlight}; background: {base}; }}"
            f"QLabel {{ color: {text}; }} QPushButton {{ padding: 5px 8px; }}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)

        artwork = QLabel()
        artwork.setAlignment(Qt.AlignmentFlag.AlignCenter)
        artwork.setFixedSize(72, 72)
        artwork.setStyleSheet(f"background: {self.theme_palette['panel']}; color: {self.theme_palette['muted']}; border-radius: 8px;")
        asset_path = _home_asset_path(app.id)
        if asset_path:
            pixmap = QPixmap(asset_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                artwork.setPixmap(scaled)
                artwork.setStyleSheet(f"background: {self.theme_palette['panel']}; border-radius: 8px;")
        else:
            on_accent = self.theme_palette.get("on_accent") or default_palette("dark")["on_accent"]
            artwork.setPixmap(_monogram_pixmap(app.name, highlight, on_accent, 72))
        artwork.mousePressEvent = lambda event: self.open_requested.emit(app.id) if app.available else None
        artwork.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(artwork)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title = QLabel(app.name)
        title.setWordWrap(True)
        title.setStyleSheet(f"font-size: {scaled_font_pt(15)}; font-weight: 700;")
        title.setCursor(Qt.CursorShape.PointingHandCursor)
        title.mousePressEvent = lambda event: self.open_requested.emit(app.id) if app.available else None
        text_col.addWidget(title)
        subtitle = QLabel(app.description)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {self.theme_palette['muted']}; font-size: {scaled_font_pt(11)};")
        subtitle.setCursor(Qt.CursorShape.PointingHandCursor)
        subtitle.mousePressEvent = lambda event: self.open_requested.emit(app.id) if app.available else None
        text_col.addWidget(subtitle)
        layout.addLayout(text_col, stretch=1)

        controls = QVBoxLayout()
        self.favorite_button = QPushButton()
        self.favorite_button.clicked.connect(lambda: self.favorite_changed.emit(app.id))
        self.pin_button = QPushButton()
        self.pin_button.clicked.connect(lambda: self.pin_changed.emit(app.id))
        controls.addWidget(self.favorite_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        controls.addWidget(self.pin_button)
        layout.addLayout(controls)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mousePressEvent = lambda event: self.open_requested.emit(app.id) if app.available else None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(app.name)
        self.setToolTip(get_tooltip_for(app.name))

    def set_favorite(self, favorite: bool) -> None:
        self.favorite_button.setText("Unfavorite" if favorite else "Favorite")
        highlight = self.theme_palette["accent"]
        muted = self.theme_palette["muted"]
        self.favorite_button.setStyleSheet(f"font-size: {scaled_font_pt(11)}; color: {highlight if favorite else muted};")
        self.favorite_button.setToolTip(get_tooltip_for("Unfavorite" if favorite else "Favorite"))

    def set_pinned(self, pinned: bool) -> None:
        self.pin_button.setText("Unpin" if pinned else "Pin")
        self.pin_button.setStyleSheet(f"font-size: {scaled_font_pt(11)};")
        self.pin_button.setToolTip(get_tooltip_for("Unpin" if pinned else "Pin"))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space) and self.app.available:
            self.open_requested.emit(self.app.id)
            return
        super().keyPressEvent(event)


class ResponsiveTileGrid(QWidget):
    """Lays out app tiles in a grid, reflowing columns to fit the available width."""

    def __init__(self, tiles: list[QWidget], min_tile_width: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.tiles = tiles
        self.min_tile_width = min_tile_width
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(10)
        for tile in self.tiles:
            tile.setParent(self)
            tile.installEventFilter(self)
        self._columns = 0
        self._relayout(force=True)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._relayout()

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress and obj in self.tiles:
            key = event.key()
            if key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
                self._move_focus(obj, key)
                return True
        return super().eventFilter(obj, event)

    def _move_focus(self, tile: QWidget, key: int) -> None:
        index = self.tiles.index(tile)
        columns = max(1, self._columns)
        if key == Qt.Key.Key_Left:
            new_index = index - 1
        elif key == Qt.Key.Key_Right:
            new_index = index + 1
        elif key == Qt.Key.Key_Up:
            new_index = index - columns
        else:
            new_index = index + columns
        if 0 <= new_index < len(self.tiles):
            self.tiles[new_index].setFocus()

    def _relayout(self, force: bool = False) -> None:
        columns = max(1, self.width() // self.min_tile_width)
        if columns == self._columns and not force:
            return
        self._columns = columns
        while self.grid.count():
            self.grid.takeAt(0)
        for index, tile in enumerate(self.tiles):
            row, col = divmod(index, columns)
            self.grid.addWidget(tile, row, col)
        for col in range(columns):
            self.grid.setColumnStretch(col, 1)


class HomeAppOrderDialog(QDialog):
    """Lets the user drag apps between Visible and Other, and reorder them."""

    SORT_VALUES = ("alphabetical", "custom", "recent")
    SORT_LABELS = ("Alphabetical", "Custom order", "Recently used")

    def __init__(self, state: HomeAppOrderState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Customize apps")
        self.resize(760, 420)
        self._active_list: Optional[DragDropListWidget] = None

        by_id = {app.id: app for app in state.apps}
        order_index = {app_id: index for index, app_id in enumerate(state.custom_order)}
        ordered_ids = sorted(by_id, key=lambda aid: (order_index.get(aid, len(order_index)), by_id[aid].name.lower()))

        root_layout = QVBoxLayout(self)
        root_layout.addWidget(QLabel("Drag apps to reorder within a section, or move them to Other to tuck them away."))

        sort_row = QHBoxLayout()
        sort_row.addWidget(QLabel("Sort by"))
        self.sort_combo = QComboBox()
        self.sort_combo.setToolTip(get_tooltip_for("Sort by"))
        self.sort_combo.addItems(self.SORT_LABELS)
        self.sort_combo.setCurrentIndex(self.SORT_VALUES.index(state.sort_mode) if state.sort_mode in self.SORT_VALUES else 0)
        sort_row.addWidget(self.sort_combo)
        sort_row.addStretch()
        root_layout.addLayout(sort_row)

        list_layout = QHBoxLayout()
        self.pinned_list = DragDropListWidget()
        self.pinned_list.setDragDropMode(self.pinned_list.DragDropMode.InternalMove)
        self.favorites_list = DragDropListWidget()
        self.favorites_list.setDragDropMode(self.favorites_list.DragDropMode.InternalMove)
        self.visible_list = DragDropListWidget()
        self.visible_list.setDragDropMode(self.visible_list.DragDropMode.InternalMove)
        self.hidden_list = DragDropListWidget()
        self.hidden_list.setDragDropMode(self.hidden_list.DragDropMode.InternalMove)
        for list_widget, title in (
            (self.pinned_list, "Pinned"), (self.favorites_list, "Favorites"),
            (self.visible_list, "Visible"), (self.hidden_list, "Other"),
        ):
            list_widget.itemSelectionChanged.connect(lambda w=list_widget: self._set_active_list(w))
            list_layout.addWidget(build_dialog_panel(self, title, list_widget))
        root_layout.addLayout(list_layout)

        for app_id in ordered_ids:
            item = QListWidgetItem(by_id[app_id].name)
            item.setData(Qt.ItemDataRole.UserRole, app_id)
            if app_id in state.hidden_ids:
                self.hidden_list.addItem(item)
            elif app_id in state.pinned_ids:
                self.pinned_list.addItem(item)
            elif app_id in state.favorite_ids:
                self.favorites_list.addItem(item)
            else:
                self.visible_list.addItem(item)

        button_row = QHBoxLayout()
        hide_btn = QPushButton("Move to Other >")
        show_btn = QPushButton("< Move to Visible")
        up_btn = QPushButton("Move up")
        down_btn = QPushButton("Move down")
        done_btn = QPushButton("Done")
        hide_btn.setToolTip(get_tooltip_for("Move to Other"))
        show_btn.setToolTip(get_tooltip_for("Move to Visible"))
        up_btn.setToolTip(get_tooltip_for("Move up"))
        down_btn.setToolTip(get_tooltip_for("Move down"))
        done_btn.setToolTip(get_tooltip_for("Done"))
        hide_btn.clicked.connect(lambda: self._move(self._active_list or self.visible_list, self.hidden_list))
        show_btn.clicked.connect(lambda: self._move(self.hidden_list, self.visible_list))
        up_btn.clicked.connect(lambda: self._move_selected(-1))
        down_btn.clicked.connect(lambda: self._move_selected(1))
        done_btn.clicked.connect(self.accept)
        for btn in (hide_btn, show_btn, up_btn, down_btn, done_btn):
            button_row.addWidget(btn)
        root_layout.addLayout(button_row)

    def _set_active_list(self, list_widget: DragDropListWidget) -> None:
        if list_widget.currentRow() >= 0:
            self._active_list = list_widget

    def _move(self, source: DragDropListWidget, target: DragDropListWidget) -> None:
        if source is target:
            return
        row = source.currentRow()
        if row < 0:
            return
        item = source.takeItem(row)
        if item is not None:
            target.addItem(item)

    def _move_selected(self, delta: int) -> None:
        list_widget = self._active_list or self.visible_list
        row = list_widget.currentRow()
        new_row = row + delta
        if row < 0 or not (0 <= new_row < list_widget.count()):
            return
        item = list_widget.takeItem(row)
        list_widget.insertItem(new_row, item)
        list_widget.setCurrentRow(new_row)

    @staticmethod
    def _list_order(list_widget: DragDropListWidget) -> list[str]:
        return [list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(list_widget.count())]

    def pinned_order(self) -> list[str]:
        return self._list_order(self.pinned_list)

    def favorites_order(self) -> list[str]:
        return self._list_order(self.favorites_list)

    def visible_order(self) -> list[str]:
        return self._list_order(self.visible_list)

    def hidden_order(self) -> list[str]:
        return self._list_order(self.hidden_list)

    def sort_mode(self) -> str:
        return self.SORT_VALUES[self.sort_combo.currentIndex()]


class HomePage(QWidget):
    """Searchable launcher for available and planned FOSSEverything workspaces."""

    workspace_requested = pyqtSignal(str)

    def __init__(self, registry: ToolRegistry, parent: Optional[QWidget] = None, settings: Optional[QSettings] = None, route_callback: Optional[Callable[[list[str]], None]] = None) -> None:
        super().__init__(parent)
        self.registry = registry
        self.settings = settings if settings is not None else QSettings("FOSSEverything", "FOSSEverything")
        self.route_callback = route_callback
        self.theme_palette = resolved_palette(self.settings)
        theme_signals.changed.connect(self._refresh)
        self.recent_max = max(1, int(self.settings.value("home/recent_max", 10)))
        self._purge_demo_recent_history()
        self.favorites = self._saved_ids("home/favorites")
        self.pinned = self._saved_ids("home/pinned")
        self.custom_order = self._saved_json("home/custom_order", [])
        self.hidden_ids = self._saved_json("home/hidden_ids", [])
        self.app_usage = self._saved_json("home/app_usage", {})
        if not isinstance(self.custom_order, list):
            self.custom_order = []
        if not isinstance(self.hidden_ids, list):
            self.hidden_ids = []
        if not isinstance(self.app_usage, dict):
            self.app_usage = {}
        self.sort_mode = str(self.settings.value("home/sort_mode", "alphabetical"))
        if self.sort_mode not in {"alphabetical", "custom", "recent"}:
            self.sort_mode = "alphabetical"
        self.filter_mode = self.settings.value("home/filter_mode", "all")
        if bool(self.settings.value("home/start_on_favorites", False, type=bool)):
            self.filter_mode = "favorites"
        self.view_mode = str(self.settings.value("home/view_mode", "tiles"))
        if self.view_mode not in {"tiles", "compact"}:
            self.view_mode = "tiles"
        self.favorites_view_override = str(self.settings.value("home/favorites_view_override", ""))
        if self.favorites_view_override not in {"", "tiles"}:
            self.favorites_view_override = ""
        self.recent_files = self._saved_list("home/recent_files")
        self.recent_outputs = self._saved_list("home/recent_outputs")
        self.setAcceptDrops(True)

        self.setStyleSheet(
            f"QWidget {{ background: {self.theme_palette['background']}; color: {self.theme_palette['text']}; }}"
            f"QLabel {{ color: {self.theme_palette['text']}; }}"
            f"QLineEdit {{ background: {self.theme_palette['panel']}; color: {self.theme_palette['text']}; border: 1px solid {self.theme_palette['border']}; padding: 5px 10px; }}"
            f"QPushButton {{ background: {self.theme_palette['panel']}; color: {self.theme_palette['text']}; border: 1px solid {self.theme_palette['border']}; }}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 28)
        self.heading = QLabel("What do you want to do")
        self.heading.setWordWrap(True)
        self.heading.setStyleSheet(f"font-size: {scaled_font_pt(30)}; font-weight: 700;")
        root.addWidget(self.heading)
        self.subtitle = QLabel("Search every available tool by name, button, description, or intent. Everything runs locally.")
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet(f"font-size: {scaled_font_pt(14)}; color: {self.theme_palette['muted']};")
        root.addWidget(self.subtitle)

        self.search = QLineEdit(placeholderText="Search tools: merge PDFs, shrink an image, crop, convert...")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumHeight(42)
        self.search.setStyleSheet(f"font-size: {scaled_font_pt(14)}; padding: 5px 10px; background: {self.theme_palette['panel']}; color: {self.theme_palette['text']}; border: 1px solid {self.theme_palette['border']};")
        self.search.textChanged.connect(self._apply_filter)
        root.addWidget(self.search)

        self.filter_bar = QHBoxLayout()
        self.filter_buttons = {}
        for label, mode in (("All", "all"), ("Favorites", "favorites"), ("Other", "other"), ("Recent files", "recent_files"), ("Recent outputs", "recent_outputs")):
            button = QPushButton(label)
            button.setStyleSheet(f"font-size: {scaled_font_pt(12)};")
            button.setToolTip(get_tooltip_for(label))
            button.setCheckable(True)
            button.clicked.connect(lambda _checked, value=mode: self._set_filter_mode(value))
            self.filter_buttons[mode] = button
            self.filter_bar.addWidget(button)
        self.filter_bar.addStretch()
        customize_apps_btn = QPushButton("Customize apps...")
        customize_apps_btn.setToolTip(get_tooltip_for("Customize apps"))
        customize_apps_btn.setStyleSheet(f"font-size: {scaled_font_pt(12)};")
        customize_apps_btn.clicked.connect(self._open_customize_apps)
        self.filter_bar.addWidget(customize_apps_btn)
        root.addLayout(self.filter_bar)

        self.summary = QLabel()
        self.summary.setStyleSheet(f"font-size: {scaled_font_pt(12)}; color: {self.theme_palette['muted']}; padding-top: 5px;")
        self.summary.setVisible(False)
        root.addWidget(self.summary)

        self.scroll = QScrollArea(widgetResizable=True, frameShape=QFrame.Shape.NoFrame)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 12, 0, 0)
        self.content_layout.setSpacing(16)
        self.scroll.setWidget(self.content)
        root.addWidget(self.scroll, stretch=1)
        self._refresh()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile()]
        if urls:
            self._handle_dropped_paths(urls)
            event.acceptProposedAction()

    def _handle_dropped_paths(self, paths: list[str]) -> None:
        if not paths:
            return
        for path in paths:
            self.record_recent_file(path)
        if self.route_callback:
            self.route_callback(paths)

    def focus_search(self) -> None:
        self.search.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _saved_ids(self, key: str) -> list[str]:
        value = self.settings.value(key, "")
        return [item for item in str(value).split(",") if item]

    def _save_ids(self, key: str, values: list[str]) -> None:
        self.settings.setValue(key, ",".join(values))

    def _saved_list(self, key: str) -> list[str]:
        value = self.settings.value(key, "")
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return [item for item in str(value).split("|") if item.strip()]

    def _save_list(self, key: str, values: list[str]) -> None:
        self.settings.setValue(key, "|".join(values[: self.recent_max]))

    def _saved_json(self, key: str, default: list | dict) -> list | dict:
        raw = self.settings.value(key, "")
        if not raw:
            return default
        try:
            return json.loads(str(raw))
        except (TypeError, ValueError):
            return default

    _default_recent_seed = {
        "home/recent_files": {"C:/docs/photo.png", "C:/docs/report.pdf", "C:/docs/a.pdf", "C:/docs/b.pdf"},  # noqa: 26 (demo sentinels matched to purge stale seed data, not real paths)
        "home/recent_outputs": {"C:/out/result.pdf"},  # noqa: 26 (demo sentinels matched to purge stale seed data, not real paths)
    }

    def _purge_demo_recent_history(self) -> None:
        demo_paths = set().union(*self._default_recent_seed.values())
        for key in ("home/recent_files", "home/recent_outputs"):
            values = self._saved_list(key)
            cleaned = [item for item in values if item and item not in demo_paths]
            if cleaned != values:
                self._save_list(key, cleaned)
            if len(cleaned) > self.recent_max:
                self._save_list(key, cleaned[: self.recent_max])

    def _record_recent(self, key: str, value: str) -> list[str]:
        cleaned = str(value).strip()
        if not cleaned:
            return []
        existing = self._saved_list(key)
        updated = []
        seen = set()
        for item in [cleaned, *existing]:
            item = str(item).strip()
            if item and item not in seen:
                updated.append(item)
                seen.add(item)
            if len(updated) >= self.recent_max:
                break
        self.settings.setValue(key, "|".join(updated))
        return updated

    def record_recent_file(self, path: str) -> list[str]:
        self.recent_files = self._record_recent("home/recent_files", path)
        self._refresh()
        return self.recent_files

    def record_recent_output(self, path: str) -> list[str]:
        self.recent_outputs = self._record_recent("home/recent_outputs", path)
        self._refresh()
        return self.recent_outputs

    def set_view_mode(self, mode: str) -> None:
        mode = "tiles" if mode not in {"tiles", "compact"} else mode
        if self.view_mode == mode:
            return
        self.view_mode = mode
        self.settings.setValue("home/view_mode", mode)
        self._refresh()

    def _set_filter_mode(self, mode: str) -> None:
        self.filter_mode = mode
        self.settings.setValue("home/filter_mode", mode)
        self._refresh_filter_buttons()
        self._refresh()

    def _refresh_filter_buttons(self) -> None:
        for mode, button in self.filter_buttons.items():
            button.setChecked(mode == self.filter_mode)
            button.setStyleSheet(f"font-size: {scaled_font_pt(12)};")

    def _toggle_favorite(self, app_id: str) -> None:
        self.favorites = self._toggle_id(self.favorites, app_id)
        self._save_ids("home/favorites", self.favorites)
        self._refresh()

    def _toggle_pin(self, app_id: str) -> None:
        self.pinned = self._toggle_id(self.pinned, app_id)
        self._save_ids("home/pinned", self.pinned)
        self._refresh()

    @staticmethod
    def _toggle_id(items: list[str], item: str) -> list[str]:
        return [value for value in items if value != item] if item in items else [item, *items]

    def _clear_content(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _refresh(self) -> None:
        self._apply_theme()
        self._apply_filter()

    def _apply_theme(self) -> None:
        self.theme_palette = resolved_palette(self.settings)
        self.setStyleSheet(
            f"QWidget {{ background: {self.theme_palette['background']}; color: {self.theme_palette['text']}; }}"
            f"QLabel {{ color: {self.theme_palette['text']}; }}"
            f"QLineEdit {{ background: {self.theme_palette['panel']}; color: {self.theme_palette['text']}; border: 1px solid {self.theme_palette['border']}; padding: 5px 10px; }}"
            f"QPushButton {{ background: {self.theme_palette['panel']}; color: {self.theme_palette['text']}; border: 1px solid {self.theme_palette['border']}; }}"
        )
        self.heading.setStyleSheet(f"font-size: {scaled_font_pt(30)}; font-weight: 700; color: {self.theme_palette['text']};")
        self.subtitle.setStyleSheet(f"font-size: {scaled_font_pt(14)}; color: {self.theme_palette['muted']};")
        self.summary.setStyleSheet(f"font-size: {scaled_font_pt(12)}; color: {self.theme_palette['muted']}; padding-top: 5px;")
        self.search.setStyleSheet(f"font-size: {scaled_font_pt(14)}; padding: 5px 10px; background: {self.theme_palette['panel']}; color: {self.theme_palette['text']}; border: 1px solid {self.theme_palette['border']};")

    def _apply_filter(self) -> None:
        self._clear_content()
        self._refresh_filter_buttons()
        query = self.search.text().strip()
        if query:
            apps = [app for app in HOME_APPS if text_matches(app.search_text, query)]
            self.summary.setText("Searches matching apps first, then tools, then UI tips.")
            if apps:
                self._add_section("Matching workspaces", apps)
            elif not self.registry.search(query):
                self.content_layout.addWidget(QLabel("No matching tools or workspaces yet."))
            self._add_search_results(query)
        else:
            if self.filter_mode == "favorites":
                self.summary.setText("Showing only your favorited tools.")
                apps = [app for app in HOME_APPS if app.id in self.favorites and app.id not in self.hidden_ids]
                if apps:
                    self._add_section("Favorites", self._sort_apps(apps), section_key="favorites")
                else:
                    self.content_layout.addWidget(QLabel("No favorite apps yet. Tap the heart on any app tile to pin it here."))
            elif self.filter_mode == "other":
                self.summary.setText("Apps you've tucked away. Use Customize apps to bring them back.")
                apps = [app for app in HOME_APPS if app.id in self.hidden_ids]
                if apps:
                    self._add_section("Other", self._sort_apps(apps))
                else:
                    self.content_layout.addWidget(QLabel("No apps in Other yet. Use Customize apps to move some here."))
            else:
                self.summary.setText("Pin favorites to keep them at the top. Artwork placeholders are ready for future icons/images.")
                if self.filter_mode == "recent_files":
                    self._add_recent_section("Recent files", self.recent_files, "file")
                elif self.filter_mode == "recent_outputs":
                    self._add_recent_section("Recent outputs", self.recent_outputs, "output")
                visible_pool = [app for app in HOME_APPS if app.id not in self.hidden_ids]
                ordered = self._sort_apps(visible_pool)
                pinned = [app for app in ordered if app.id in self.pinned]
                remaining = [app for app in ordered if app.id not in self.pinned]
                if pinned:
                    self._add_section("Pinned", pinned)
                self._add_section("All apps", remaining)
        self.content_layout.addStretch()

    def _home_sort_key(self, app: HomeApp) -> tuple[bool, str]:
        return (app.id not in self.favorites, app.name.lower())

    def _sort_apps(self, apps: list[HomeApp]) -> list[HomeApp]:
        if self.sort_mode == "custom":
            rank = {app_id: index for index, app_id in enumerate(self.custom_order)}
            default_rank = len(rank)
            return sorted(apps, key=lambda a: (rank.get(a.id, default_rank), a.name.lower()))
        if self.sort_mode == "recent":
            recent_ids = sorted(self.app_usage, key=lambda aid: self.app_usage[aid], reverse=True)
            rank = {app_id: index for index, app_id in enumerate(recent_ids)}
            default_rank = len(rank)
            return sorted(apps, key=lambda a: (rank.get(a.id, default_rank), a.name.lower()))
        return sorted(apps, key=self._home_sort_key)

    def _add_section(self, title: str, apps: list[HomeApp], section_key: str = "") -> None:
        use_tiles = self.view_mode == "tiles" or (section_key == "favorites" and self.favorites_view_override == "tiles")
        if use_tiles:
            self._add_tile_section(title, apps)
        else:
            self._add_compact_section(title, apps)

    def _on_workspace_requested(self, app_id: str) -> None:
        self.app_usage[app_id] = datetime.now(timezone.utc).isoformat()
        self.settings.setValue("home/app_usage", json.dumps(self.app_usage))
        self.workspace_requested.emit(app_id)

    def _open_customize_apps(self) -> None:
        state = HomeAppOrderState(
            apps=HOME_APPS,
            custom_order=self.custom_order,
            hidden_ids=self.hidden_ids,
            pinned_ids=self.pinned,
            favorite_ids=self.favorites,
            sort_mode=self.sort_mode
        )
        dialog = HomeAppOrderDialog(state, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.pinned = dialog.pinned_order()
            self.favorites = dialog.favorites_order()
            self.custom_order = self.pinned + self.favorites + dialog.visible_order() + dialog.hidden_order()
            self.hidden_ids = dialog.hidden_order()
            self.sort_mode = dialog.sort_mode()
            self._save_ids("home/pinned", self.pinned)
            self._save_ids("home/favorites", self.favorites)
            self.settings.setValue("home/custom_order", json.dumps(self.custom_order))
            self.settings.setValue("home/hidden_ids", json.dumps(self.hidden_ids))
            self.settings.setValue("home/sort_mode", self.sort_mode)
            self._refresh()

    def _add_search_results(self, query: str) -> None:
        matches = self.registry.search(query, limit=25)
        tooltip_matches = tooltip_search(query, limit=15)

        if not matches and not tooltip_matches:
            return

        if matches:
            section = QWidget()
            layout = QVBoxLayout(section)
            layout.setContentsMargins(0, 0, 0, 0)
            label = QLabel("Best matching tools")
            label.setStyleSheet("font-weight: 700;")
            layout.addWidget(label)
            for match in matches:
                tool = match.tool
                button = QPushButton(_button_text(f"{tool.title}  --  {tool.category}\n{tool.description}"))
                button.setToolTip(keywords_tooltip(tool.keywords))
                button.setMinimumHeight(52)
                button.setStyleSheet("text-align: left; padding: 8px 12px;")
                button.clicked.connect(tool.activate)
                layout.addWidget(button)
            self.content_layout.addWidget(section)

        if tooltip_matches:
            tooltip_section = QWidget()
            tooltip_layout = QVBoxLayout(tooltip_section)
            tooltip_layout.setContentsMargins(0, 0, 0, 0)
            tooltip_label = QLabel("Matching UI tips")
            tooltip_label.setStyleSheet("font-weight: 700;")
            tooltip_layout.addWidget(tooltip_label)
            for entry in tooltip_matches:
                button = QPushButton(_button_text(f"{entry.label}\n{entry.description}"))
                button.setToolTip(entry.description)
                button.setMinimumHeight(52)
                button.setStyleSheet("text-align: left; padding: 8px 12px;")
                button.setEnabled(False)
                tooltip_layout.addWidget(button)
            self.content_layout.addWidget(tooltip_section)

    def _add_recent_section(self, title: str, entries: list[str], entry_type: str) -> None:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(title)
        label.setStyleSheet("font-weight: 700;")
        layout.addWidget(label)
        if not entries:
            layout.addWidget(QLabel(f"No {entry_type} entries yet."))
            self.content_layout.addWidget(section)
            return
        for entry in entries:
            button = QPushButton(_button_text(entry))
            button.setToolTip(get_tooltip_for("Open recent file"))
            button.setStyleSheet("text-align: left; padding: 8px 10px;")
            button.clicked.connect(lambda _checked=False, path=entry: self._open_recent_path(path))
            layout.addWidget(button)
        self.content_layout.addWidget(section)

    def _add_compact_section(self, title: str, apps: list[HomeApp]) -> None:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(title)
        label.setStyleSheet("font-weight: 700;")
        layout.addWidget(label)
        fallback_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        icon_size = QSize(20, 20)
        for app in apps:
            button = QPushButton(_app_icon(app.id, fallback_icon, icon_size), _button_text(app.name))
            button.setIconSize(icon_size)
            button.setToolTip(app.description)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet("text-align: left; padding: 8px 10px;")
            button.clicked.connect(lambda _checked=False, app_id=app.id: self._on_workspace_requested(app_id))
            layout.addWidget(button)
        self.content_layout.addWidget(section)

    def _open_recent_path(self, path: str) -> None:
        if not path:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _add_tile_section(self, title: str, apps: list[HomeApp]) -> None:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(title)
        label.setStyleSheet("font-weight: 700;")
        layout.addWidget(label)
        tiles = []
        for app in apps:
            tile = AppTile(app, theme_palette=self.theme_palette)
            tile.set_favorite(app.id in self.favorites)
            tile.set_pinned(app.id in self.pinned)
            tile.open_requested.connect(self._on_workspace_requested)
            tile.favorite_changed.connect(self._toggle_favorite)
            tile.pin_changed.connect(self._toggle_pin)
            tiles.append(tile)
        min_tile_width = scaled_font_size(360)
        grid = ResponsiveTileGrid(tiles, min_tile_width)
        layout.addWidget(grid)
        self.content_layout.addWidget(section)
