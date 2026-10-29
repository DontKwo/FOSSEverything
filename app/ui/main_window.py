"""Main application shell and global discovery for every FOSSEverything feature."""
import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import QPoint, QSettings, Qt
from PyQt6.QtGui import QAction, QColor, QFont, QKeySequence, QPainter, QPixmap, QPolygon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMenu, QStackedWidget, QStyle, QSystemTrayIcon, QWidget, QFileDialog,
    QVBoxLayout, QSplitter
)

from app.system import shell_integration
from app.ui.home_page import HomePage
from app.core.search_palette import ToolSearchPalette
from app.core.theme import (
    DEFAULT_BUTTON_RADIUS,
    THEME_PRESET_ORDER,
    default_palette as _theme_default_palette,
    load_ui_palette as _theme_load_ui_palette,
    notify_theme_changed,
    parse_color_value,
    rgba as theme_rgba,
)
from app.core.tool_registry import ToolDefinition, ToolRegistry
from app.core.tooltips import get_tooltip_for
from app.core.workspace_registry import WorkspaceDefinition, WorkspaceRegistry
from app.ui.settings_hub import SettingsHub


class MainWindow(QMainWindow):
    # Every feature tab is built on first use, not at startup, so cold start only
    # pays for the one workspace the user (or a routed file) actually needs.
    _TAB_MAKERS: dict[str, str] = {
        "pdf": "_make_pdf_tab",
        "images": "_make_images_tab",
        "media": "_make_media_tab",
        "resume": "_make_resume_tab",
        "converter": "_make_converter_tab",
        "ocr": "_make_ocr_tab",
        "word_counter": "_make_word_counter_tab",
        "playlist": "_make_playlist_tab",
        "metadata": "_make_metadata_tab",
        "qr": "_make_qr_tab",
        "renamer": "_make_renamer_tab",
        "data": "_make_data_tab",
        "markdown": "_make_markdown_tab",
        "hash": "_make_hash_tab",
        "palette": "_make_palette_tab",
        "collage": "_make_collage_tab",
        "model3d": "_make_model3d_tab",
        "text_tools": "_make_text_tools_tab",
        "encoding": "_make_encoding_tab",
        "network_monitor": "_make_network_monitor_tab",
    }

    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()
        self.settings = settings if settings is not None else QSettings("FOSSEverything", "FOSSEverything")
        self.current_theme = str(self.settings.value("app/theme", "dark"))
        try:
            self.font_scale = float(self.settings.value("app/font_scale", 1.0))
        except (TypeError, ValueError):
            self.font_scale = 1.0
        if not math.isfinite(self.font_scale) or self.font_scale <= 0:
            self.font_scale = 1.0
        default_accent = self._default_palette(self.current_theme)["accent"]
        self.accent_color = str(self.settings.value("app/accent_color", default_accent))
        if not self._parse_color_value(self.accent_color, default_accent).isValid():
            self.accent_color = default_accent
        self.button_radius = int(self.settings.value("app/button_radius", DEFAULT_BUTTON_RADIUS))
        self.ui_palette = self._load_ui_palette()
        self.setWindowTitle("FOSSEverything - Local Desktop Power Tool")

        self._setup_window()
        self._setup_central_widget()
        self._setup_actions_and_menus()

        self._apply_font_scale()

        self._force_quit = False
        self.tray_icon: QSystemTrayIcon | None = None
        self._setup_tray_icon()

    def _setup_actions_and_menus(self) -> None:
        self.shortcut_defs: dict[str, dict[str, Any]] = {}

        self.home_action = QAction("Home", self)
        self.home_action.setToolTip(get_tooltip_for("Home"))
        self.home_action.triggered.connect(self.go_home)
        self._register_shortcut("home", self.home_action, "Alt+H", "Go to Home")

        self.settings_action = QAction("Settings", self)
        self.settings_action.setToolTip(get_tooltip_for("Settings"))
        self.settings_action.triggered.connect(self._open_settings_hub)
        self._register_shortcut("settings", self.settings_action, "Ctrl+,", "Open Settings")

        search_action = QAction("Find a tool...", self)
        search_action.setToolTip(get_tooltip_for("Find a tool"))
        search_action.triggered.connect(self.open_tool_search)
        self._register_shortcut("find_tool", search_action, "Ctrl+K", "Find a tool")

        self.fullscreen_action = QAction("Toggle fullscreen", self)
        self.fullscreen_action.setToolTip(get_tooltip_for("Toggle fullscreen"))
        self.fullscreen_action.triggered.connect(self._toggle_fullscreen)
        self._register_shortcut("toggle_fullscreen", self.fullscreen_action, "F11", "Toggle fullscreen")

        self.font_increase_action = QAction("Increase text size", self)
        self.font_increase_action.setToolTip(get_tooltip_for("Increase text size"))
        self.font_increase_action.triggered.connect(lambda: self.adjust_font_scale(0.12))
        self._register_shortcut("font_increase", self.font_increase_action, "Ctrl+=", "Increase text size")

        self.font_decrease_action = QAction("Decrease text size", self)
        self.font_decrease_action.setToolTip(get_tooltip_for("Decrease text size"))
        self.font_decrease_action.triggered.connect(lambda: self.adjust_font_scale(-0.12))
        self._register_shortcut("font_decrease", self.font_decrease_action, "Ctrl+-", "Decrease text size")

        self.font_reset_action = QAction("Reset text size", self)
        self.font_reset_action.setToolTip(get_tooltip_for("Reset text size"))
        self.font_reset_action.triggered.connect(lambda: self.adjust_font_scale(None))
        self._register_shortcut("font_reset", self.font_reset_action, "Ctrl+0", "Reset text size")

        self.menuBar().addAction(self.home_action)
        self.menuBar().addAction(self.settings_action)

        tools_menu = self.menuBar().addMenu("Tools")
        tools_menu.addAction(search_action)

    def _setup_central_widget(self) -> None:
        self.tabs = QStackedWidget()
        self._tab_cache: dict[str, QWidget] = {}

        self.tool_registry = ToolRegistry()
        self.workspace_registry = WorkspaceRegistry()
        self._register_workspaces()
        self._register_current_tools()
        # Built lazily (see the home_page property below) so a routed file-association
        # launch skips the ~19-tile home screen's construction cost entirely.
        self._home_page: HomePage | None = None
        self._install_recent_file_hooks()

        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.addWidget(self.tabs)
        self.setCentralWidget(central_widget)

    def _setup_window(self) -> None:
        remember_window = bool(self.settings.value("app/remember_window", True, type=bool))
        maximize_on_start = bool(self.settings.value("app/maximize_on_start", True, type=bool))

        geometry_restored = False
        if remember_window:
            saved_geometry = self.settings.value("app/window_geometry")
            if saved_geometry is not None:
                geometry_restored = bool(self.restoreGeometry(saved_geometry))

        if not geometry_restored:
            screen = QApplication.primaryScreen()
            if screen is not None:
                geometry = screen.availableGeometry()
                if geometry.width() > 0 and geometry.height() > 0:
                    self.resize(geometry.width(), geometry.height())
            else:
                self.resize(1200, 800)

        if maximize_on_start and not geometry_restored:
            self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

        self.setMinimumSize(760, 520)

    def _get_tab(self, tab_id: str) -> QWidget:
        tab = self._tab_cache.get(tab_id)
        if tab is None:
            tab = getattr(self, self._TAB_MAKERS[tab_id])()
            self._tab_cache[tab_id] = tab
            self.tabs.addWidget(tab)
        return tab

    # Invoked dynamically via getattr(self, self._TAB_MAKERS[tab_id])(); each import stays
    # local so a tab's dependencies (e.g. model3d's pyvista/vtk chain) load only when needed.
    def _make_pdf_tab(self) -> QWidget:  # noqa: 21
        from app.features.pdf.tab import PdfTab  # noqa: 13
        return PdfTab(settings=self.settings)

    def _make_images_tab(self) -> QWidget:  # noqa: 21
        from app.features.image.tab import ImageTab  # noqa: 13
        return ImageTab(settings=self.settings)

    def _make_media_tab(self) -> QWidget:  # noqa: 21
        from app.features.media.tab import MediaTab  # noqa: 13
        return MediaTab()

    def _make_resume_tab(self) -> QWidget:  # noqa: 21
        from app.features.resume.tab import ResumeTab  # noqa: 13
        return ResumeTab()

    def _make_converter_tab(self) -> QWidget:  # noqa: 21
        from app.features.converter.tab import ConverterTab  # noqa: 13
        return ConverterTab()

    def _make_ocr_tab(self) -> QWidget:  # noqa: 21
        from app.features.ocr.tab import OcrTab  # noqa: 13
        return OcrTab(settings=self.settings)

    def _make_word_counter_tab(self) -> QWidget:  # noqa: 21
        from app.features.word_counter.tab import WordCounterTab  # noqa: 13
        return WordCounterTab()

    def _make_playlist_tab(self) -> QWidget:  # noqa: 21
        from app.features.playlist.tab import PlaylistTab  # noqa: 13
        return PlaylistTab()

    def _make_metadata_tab(self) -> QWidget:  # noqa: 21
        from app.features.metadata.tab import MetadataTab  # noqa: 13
        return MetadataTab()

    def _make_qr_tab(self) -> QWidget:  # noqa: 21
        from app.features.qr.tab import QrTab  # noqa: 13
        return QrTab()

    def _make_renamer_tab(self) -> QWidget:  # noqa: 21
        from app.features.renamer.tab import RenamerTab  # noqa: 13
        return RenamerTab()

    def _make_data_tab(self) -> QWidget:  # noqa: 21
        from app.features.data.tab import DataTab  # noqa: 13
        return DataTab(settings=self.settings)

    def _make_markdown_tab(self) -> QWidget:  # noqa: 21
        from app.features.markdown.tab import MarkdownTab  # noqa: 13
        return MarkdownTab()

    def _make_hash_tab(self) -> QWidget:  # noqa: 21
        from app.features.hash.tab import HashTab  # noqa: 13
        return HashTab(settings=self.settings)

    def _make_palette_tab(self) -> QWidget:  # noqa: 21
        from app.features.palette.tab import PaletteTab  # noqa: 13
        return PaletteTab()

    def _make_collage_tab(self) -> QWidget:  # noqa: 21
        from app.features.collage.tab import CollageTab  # noqa: 13
        return CollageTab()

    def _make_model3d_tab(self) -> QWidget:  # noqa: 21
        from app.features.model3d.tab import Model3DTab  # noqa: 13
        return Model3DTab()

    def _make_text_tools_tab(self) -> QWidget:  # noqa: 21
        from app.features.text_tools.tab import TextToolsTab  # noqa: 13
        return TextToolsTab(settings=self.settings)

    def _make_encoding_tab(self) -> QWidget:  # noqa: 21
        from app.features.encoding.tab import EncodingTab  # noqa: 13
        return EncodingTab(settings=self.settings)

    def _make_network_monitor_tab(self) -> QWidget:  # noqa: 21
        from app.features.network_monitor.tab import NetworkMonitorTab  # noqa: 13
        return NetworkMonitorTab(settings=self.settings)

    @property
    def home_page(self) -> HomePage:
        if self._home_page is None:
            self._home_page = HomePage(self.tool_registry, route_callback=self._route_dropped_files, settings=self.settings)
            self._home_page.workspace_requested.connect(self.open_workspace)
            self.tabs.addWidget(self._home_page)
        return self._home_page

    # Only tabs actually read elsewhere (shell_integration.route_file, tests) get a
    # property; others are reached exclusively through open_workspace/_get_tab.
    @property
    def pdf_tab(self) -> QWidget:
        return self._get_tab("pdf")

    @property
    def image_tab(self) -> QWidget:
        return self._get_tab("images")

    @property
    def media_tab(self) -> QWidget:
        return self._get_tab("media")

    @property
    def converter_tab(self) -> QWidget:
        return self._get_tab("converter")

    @property
    def ocr_tab(self) -> QWidget:
        return self._get_tab("ocr")

    @property
    def word_counter_tab(self) -> QWidget:
        return self._get_tab("word_counter")

    @property
    def data_tab(self) -> QWidget:
        return self._get_tab("data")

    @property
    def markdown_tab(self) -> QWidget:
        return self._get_tab("markdown")

    @property
    def hash_tab(self) -> QWidget:
        return self._get_tab("hash")

    @property
    def model3d_tab(self) -> QWidget:
        return self._get_tab("model3d")

    def _setup_tray_icon(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = self.windowIcon()
        if icon.isNull():
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip(get_tooltip_for("Tray icon"))
        menu = QMenu(self)
        open_action = menu.addAction("Open FOSSEverything")
        open_action.triggered.connect(self._restore_from_tray)
        quit_action = menu.addAction("Quit FOSSEverything")
        quit_action.triggered.connect(self._quit_from_tray)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._restore_from_tray()

    def _restore_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self) -> None:
        self._force_quit = True
        self.close()
        QApplication.quit()

    def _register_shortcut(self, shortcut_id: str, action: QAction, default: str, label: str) -> None:
        saved = str(self.settings.value(f"shortcuts/{shortcut_id}", default))
        action.setShortcut(QKeySequence(saved))
        self.shortcut_defs[shortcut_id] = {"action": action, "default": default, "label": label}
        self.addAction(action)

    def _install_recent_file_hooks(self) -> None:
        if getattr(QFileDialog, "_foss_recent_hooks_installed", False):
            return

        original_open = QFileDialog.getOpenFileName
        original_open_multi = QFileDialog.getOpenFileNames
        original_save = QFileDialog.getSaveFileName

        def _record_open_result(result: Any) -> Any:
            if not result:
                return result
            paths = result[0] if isinstance(result, tuple) else result
            if isinstance(paths, (list, tuple)):
                for path in paths:
                    if path:
                        self.home_page.record_recent_file(path)
            elif paths:
                self.home_page.record_recent_file(paths)
            return result

        def _wrapped_get_open_file_name(*args: Any, **kwargs: Any) -> Any:
            result = original_open(*args, **kwargs)
            return _record_open_result(result)

        def _wrapped_get_open_file_names(*args: Any, **kwargs: Any) -> Any:
            result = original_open_multi(*args, **kwargs)
            return _record_open_result(result)

        def _wrapped_get_save_file_name(*args: Any, **kwargs: Any) -> Any:
            result = original_save(*args, **kwargs)
            if result and result[0]:
                self.home_page.record_recent_output(result[0])
            return result

        QFileDialog.getOpenFileName = staticmethod(_wrapped_get_open_file_name)
        QFileDialog.getOpenFileNames = staticmethod(_wrapped_get_open_file_names)
        QFileDialog.getSaveFileName = staticmethod(_wrapped_get_save_file_name)
        QFileDialog._foss_original_get_open_file_name = original_open
        QFileDialog._foss_original_get_save_file_name = original_save
        QFileDialog._foss_recent_hooks_installed = True

    def _register_workspaces(self) -> None:
        for workspace in (
            WorkspaceDefinition("pdf", "PDF Studio", "Documents", (".pdf",)),
            WorkspaceDefinition("images", "Image Studio", "Images", (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff")),
            WorkspaceDefinition("media", "Media Studio", "Media", (".mp4", ".mov", ".mkv", ".avi", ".webm", ".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg")),
            WorkspaceDefinition("data", "Data Studio", "Data", (".json", ".yaml", ".yml", ".csv", ".xml", ".tsv")),
            WorkspaceDefinition("ocr", "OCR & Text", "Documents", (".png", ".jpg", ".jpeg", ".pdf", ".bmp")),
            WorkspaceDefinition("hash", "Hash & Verify", "Utilities", (".bin", ".dat", ".txt", ".json", ".csv")),
            WorkspaceDefinition("playlist", "Playlist Porter", "Media", (".m3u", ".m3u8")),
            WorkspaceDefinition("word_counter", "Word Counter", "Documents", (".txt", ".pdf", ".docx")),
            WorkspaceDefinition("markdown", "Markdown Studio", "Documents", (".md", ".markdown")),
            WorkspaceDefinition("converter", "File Converter", "Utilities", ()),
            WorkspaceDefinition("model3d", "3D Model Studio", "Utilities", (".stl", ".obj", ".ply", ".step", ".stp", ".iges", ".igs")),
            WorkspaceDefinition("text_tools", "Text Tools", "Utilities", ()),
            WorkspaceDefinition("encoding", "Encoding / Decoding", "Utilities", ()),
            WorkspaceDefinition("network_monitor", "Network Monitor", "Utilities", ()),
        ):
            self.workspace_registry.register(workspace)

    def _register_current_tools(self) -> None:
        """Register existing features so the shell, not individual tabs, owns discovery."""
        self._register_document_tools()
        self._register_media_and_graphics_tools()
        self._register_utility_tools()

    def _register_document_tools(self) -> None:
        self._register_tab_tools("pdf", "PDF", "pdf", [
            ("open_pdf", "Open PDF", ("open", "view", "document"), "Open and view a PDF."),
            ("merge_pdfs", "Merge PDFs", ("combine", "join", "append"), "Combine PDF files in your chosen order."),
            ("split_pdf", "Split PDF", ("extract pages", "separate", "pages"), "Write selected page ranges to separate PDFs."),
            ("organize_pages", "Organize, reorder, rotate, or delete PDF pages", ("reorder", "rotate page", "delete page", "duplicate", "extract"), "Visual page manager for rotating, reordering, duplicating, or removing pages."),
            ("protect_pdf", "Protect PDF with password", ("password", "encrypt", "protect", "lock", "security"), "Encrypt a PDF with user and owner passwords."),
            ("unlock_pdf", "Unlock or decrypt PDF", ("unlock", "decrypt", "remove password"), "Remove password protection from an encrypted PDF."),
            ("add_watermark", "Add text watermark to PDF", ("watermark", "stamp", "confidential", "draft", "diagonal"), "Stamp a customizable diagonal text watermark on all pages."),
            ("add_page_numbers", "Add page numbers & headers/footers to PDF", ("page numbers", "header", "footer", "numbering", "bates"), "Stamp page numbers or header/footer labels on PDF pages."),
            ("extract_text", "Extract text from PDF", ("extract text", "pdf to text", "pdf to markdown", "copy text"), "Extract selectable text to TXT or Markdown files."),
            ("compress_pdf", "Compress PDF", ("reduce size", "shrink"), "Create a smaller PDF locally."),
            ("export_pages", "Export PDF pages as images", ("pdf to png", "pdf to jpg", "convert", "rasterize"), "Export every PDF page as a numbered image."),
            ("save_as", "Save annotated PDF", ("export", "markup", "redact"), "Bake current annotations into a PDF."),
        ])
        self._register_tab_tools("ocr", "OCR Studio", "ocr", [
            ("_browse_file", "Open document / image for OCR", ("ocr", "scan", "extract text", "tesseract", "recognize text", "read text"), "Extract text from any image or PDF file using local offline OCR."),
            ("_export_searchable_pdf", "Generate Searchable PDF (OCR)", ("searchable pdf", "make searchable", "ocr pdf", "invisible text"), "Generate a searchable PDF with invisible OCR text layer."),
            ("_run_batch_ocr", "Batch OCR documents / images", ("batch ocr", "bulk ocr", "bulk text extract"), "Run OCR on multiple images or PDFs in batch."),
        ])
        self._register_tab_tools("resume", "Resume Studio", "resume", [
            ("_open_resume", "Open Master Resume JSON", ("resume", "cv", "career", "job", "tailor", "master resume"), "Open and edit your master resume locally."),
            ("_save_preset", "Save job tailoring preset", ("preset", "tailoring", "job profile", "profile"), "Save tailored configuration preset for a specific job title."),
            ("_analyze_ats", "Analyze ATS keyword match", ("ats", "keywords", "match score", "job description"), "Analyze resume against a job description for ATS keyword match score."),
            ("_export_pdf", "Export tailored resume to PDF", ("export pdf", "resume pdf", "cv pdf"), "Generate a clean ATS-friendly PDF resume."),
            ("_export_md", "Export tailored resume to Markdown", ("export md", "resume markdown"), "Export active tailored resume to Markdown."),
        ])
        self._register_tab_tools("word_counter", "Word Counter", "word_counter", [
            ("_browse_file", "Open document for Word Count & Analytics", ("word count", "character count", "stats", "readability", "flesch", "reading time", "density"), "Count words, sentences, reading time, and readability score for any PDF, Word, or text document."),
            ("_paste_clipboard", "Paste and analyze text stats", ("paste text", "count clipboard", "word count paste"), "Paste text from clipboard for instant live word count and document analytics."),
        ])
        self._register_tab_tools("markdown", "Markdown Studio", "markdown", [
            ("_browse_file", "Open Markdown file", ("markdown", "md", "open", "editor"), "Open a Markdown file for side-by-side live editing and preview."),
            ("_export_html", "Export Markdown as HTML", ("export html", "markdown to html", "convert markdown"), "Render the current Markdown to a standalone local HTML file."),
        ])
        self._register_tab_tools("text_tools", "Text Tools", "text_tools", [
            ("_regex_find_replace", "Regex find and replace text", ("regex", "find replace", "pattern", "search replace"), "Apply a regular expression find-and-replace across the current text."),
            ("_diff_checker", "Compare two blocks of text (diff)", ("diff", "compare text", "text difference"), "Compare the current text against another block and show a unified diff."),
        ])

    def _register_media_and_graphics_tools(self) -> None:
        self._register_tab_tools("image", "Images", "images", [
            ("open_image", "Open image", ("view", "photo", "picture"), "Open an image for local editing."),
            ("take_screenshot", "Take screenshot or snip region", ("screenshot", "screen capture", "snip", "desktop capture", "grab"), "Capture full desktop screen or interactively snip a custom area into the canvas."),
            ("auto_enhance", "Auto enhance photo", ("enhance", "auto", "contrast", "fix photo", "levels"), "Automatically improve contrast, color balance, and sharpness."),
            ("adjust_photo", "Adjust photo tone and colors", ("brightness", "contrast", "saturation", "sharpness", "warmth", "tint", "filter", "sepia", "preset"), "Adjust brightness, contrast, saturation, sharpness, warmth, and artistic presets."),
            ("rotate_90_cw", "Rotate image 90° clockwise", ("rotate", "turn", "clockwise", "orientation"), "Rotate photo 90 degrees clockwise."),
            ("rotate_90_ccw", "Rotate image 90° counter-clockwise", ("rotate", "turn", "counter-clockwise"), "Rotate photo 90 degrees counter-clockwise."),
            ("rotate_custom", "Straighten or rotate image", ("straighten", "angle", "degree", "level", "horizon"), "Rotate image by custom angle or straighten horizon."),
            ("flip_horizontal", "Flip image horizontally", ("flip", "mirror", "horizontal", "reflect"), "Mirror image left to right."),
            ("flip_vertical", "Flip image vertically", ("flip", "vertical", "upside down"), "Flip image top to bottom."),
            ("apply_crop", "Crop image", ("trim", "resize canvas"), "Crop the current image to a drawn region."),
            ("crop_preset", "Crop to aspect ratio preset", ("aspect ratio", "1:1", "16:9", "4:5", "9:16", "instagram", "story", "wallpaper"), "Crop image to standard photo and social aspect ratios."),
            ("circle_crop", "Circular avatar crop", ("circle", "avatar", "profile", "round", "cutout"), "Crop centered circle with transparent background for avatars."),
            ("resize_image", "Resize image", ("dimensions", "scale"), "Change image dimensions."),
            ("add_border", "Add image border or Polaroid frame", ("border", "frame", "polaroid", "padding", "margin"), "Add solid color border or Polaroid-style frame."),
            ("blur_selection", "Blur sensitive area", ("blur", "censor", "privacy", "redact face", "hide"), "Apply heavy Gaussian blur to marked selection."),
            ("pixelate_selection", "Pixelate sensitive area", ("pixelate", "mosaic", "redact", "hide number", "censor"), "Apply mosaic pixelation to marked selection."),
            ("compress_convert", "Compress or convert image", ("jpg", "png", "webp", "reduce size"), "Export an image in another format or quality."),
            ("remove_background", "Remove image background", ("transparent", "cutout", "erase background", "ai"), "Remove an image background locally and preserve transparency."),
            ("add_image_layer", "Add image layer", ("combine images", "collage", "overlay", "multiple images", "canvas"), "Place another image on the current canvas and reposition it."),
            ("bring_layer_to_front", "Bring image layer to front", ("layer", "stack", "z order", "forward"), "Move the selected image layer in front of other image layers."),
            ("send_layer_to_back", "Send image layer to back", ("layer", "stack", "z order", "backward"), "Move the selected image layer behind other image layers."),
            ("duplicate_selected_layer", "Duplicate image layer", ("layer", "copy", "duplicate"), "Create a copy of the selected image layer."),
            ("resize_selected_layer", "Resize image layer", ("layer", "scale", "dimensions"), "Resize only the selected image layer."),
            ("rotate_selected_layer", "Rotate image layer", ("layer", "turn", "rotate"), "Rotate only the selected image layer."),
            ("begin_selected_layer_crop", "Crop image layer", ("layer", "trim", "cut"), "Drag a crop rectangle to crop only the selected image layer."),
            ("adjust_selected_layer", "Adjust image layer", ("layer", "brightness", "contrast", "saturation", "sharpness", "blur", "opacity", "grayscale"), "Adjust brightness, contrast, saturation, sharpness, blur, opacity, or grayscale for one image layer."),
            ("copy_to_clipboard", "Copy image to clipboard", ("copy", "clipboard", "paste"), "Copy full composite image to clipboard."),
            ("batch_process", "Batch process images", ("bulk", "folder", "convert many"), "Resize, compress, or convert a group of images."),
            ("save_as", "Save image", ("export", "markup"), "Bake annotations and save the image."),
        ])
        self._register_tab_tools("media", "Media Studio", "media", [
            ("_browse_file", "Open audio or video file", ("video", "audio", "media", "mp4", "mp3", "mov", "wav", "mkv", "player"), "Open video or audio file for trimming, conversion, or compression."),
            ("_run_trim", "Trim video or audio clip", ("trim", "cut", "clip", "slice", "split video", "shorten"), "Cut video or audio with frame-accurate or lossless stream-copy trimming."),
            ("_run_extract_audio", "Extract audio from video", ("extract audio", "video to mp3", "audio track", "rip audio", "wav", "aac"), "Extract soundtrack or audio stream from video to MP3, WAV, AAC, FLAC, or M4A."),
            ("_run_convert", "Convert video or audio format", ("convert video", "transcode", "mp4 to mkv", "mov to mp4", "webm"), "Convert video and audio between MP4, MKV, MOV, WEBM, AVI, MP3, and WAV."),
            ("_run_compress", "Compress video file size", ("compress video", "shrink video", "discord 8mb", "small video", "reduce video size"), "Compress video with quality presets (Discord/Email 8MB, 720p Web, 1080p)."),
            ("_run_mute", "Mute video (remove audio)", ("mute", "strip audio", "silent video", "remove sound"), "Strip audio tracks from video locally."),
            ("_run_capture_frame", "Capture video frame as image", ("snapshot", "frame grab", "thumbnail", "screenshot video", "save frame"), "Save current video frame at native resolution to PNG or JPG."),
        ])
        self._register_tab_tools("palette", "Palette Extractor", "palette", [
            ("_open_image", "Extract color palette from image", ("palette", "colors", "extract colors", "swatches", "dominant colors", "hex"), "Extract dominant colors, hex codes, and RGB values from any image."),
            ("_copy_all_hex", "Copy color palette hex codes", ("copy hex", "color palette", "css colors"), "Copy all extracted color hex codes to the clipboard."),
        ])
        self._register_tab_tools("collage", "Collage Maker", "collage", [
            ("_add_images", "Create photo collage / grid", ("collage", "photo grid", "combine photos", "side by side", "quad"), "Arrange multiple photos into clean grid collages and side-by-side compositions."),
            ("_generate_collage", "Render photo collage", ("render collage", "export grid", "make collage"), "Render and export photo collage to PNG, JPEG, or WEBP."),
        ])
        self._register_tab_tools("model3d", "3D Model Studio", "model3d", [
            ("_browse_file", "Open 3D model (STL/OBJ/STEP)", ("3d", "mesh", "cad", "stl", "obj", "step", "iges", "ply"), "Open an STL, OBJ, PLY, STEP, or IGES 3D model."),
            ("_apply_cut", "Cut 3D model with plane", ("cut", "slice", "plane", "split model", "cross section"), "Slice the loaded model with a single cut plane into two exportable pieces."),
            ("_repair_mesh", "Repair mesh (fill holes, fix normals)", ("repair", "fix mesh", "watertight", "fill holes"), "Fill holes, remove degenerate faces, and fix normals on the loaded mesh."),
            ("_export_current", "Export 3D model", ("export", "save", "stl", "obj", "step", "convert"), "Export the current model or cut piece as STL, OBJ, PLY, STEP, or IGES."),
        ])
        self._register_tab_tools("playlist", "Playlist Porter (NOT WORKING: YouTube Music)", "playlist", [
            ("_browse_playlist_file", "Open playlist file to convert", ("playlist", "spotify", "youtube", "music", "convert playlist", "m3u8", "csv"), "Spotify playlist import works; YouTube Music is not working right now."),
        ])

    def _register_utility_tools(self) -> None:
        self._register_tab_tools("converter", "Converter", "converter", [
            ("choose_file", "Convert file format", ("convert", "format", "export", "pdf to image", "image to pdf"), "Convert supported images, PDFs, JSON, YAML, and CSV locally."),
            ("_batch_add_files", "Batch convert files", ("batch convert", "convert folder", "bulk convert", "multi file convert"), "Convert multiple files in a queue to a chosen output format."),
        ])
        self.tool_registry.register(ToolDefinition(
            id="metadata.manage", title="View, edit, or remove file metadata", category="Metadata",
            keywords=("metadata", "exif", "privacy", "strip", "remove location", "author"),
            description="Inspect supported image/PDF metadata, edit supported fields, or save a clean local copy.",
            activate=lambda _checked=False: self.open_workspace("metadata"),
        ))
        self._register_tab_tools("qr", "QR Studio", "qr", [
            ("save_qr_image", "Generate and save QR code", ("qr", "code", "barcode", "wifi qr", "vcard", "link", "logo"), "Generate a custom offline QR code with custom logo/colors and save as PNG/PDF."),
            ("export_svg", "Export QR code as vector SVG", ("svg", "vector qr", "scalable qr", "svg export"), "Export crisp, scalable vector SVG QR code."),
            ("copy_to_clipboard", "Copy QR code to clipboard", ("copy qr", "clipboard", "paste qr"), "Copy generated QR code directly to clipboard."),
        ])
        self._register_tab_tools("renamer", "Renamer", "renamer", [
            ("_add_files", "Batch rename files", ("rename", "batch", "regex", "numbering", "prefix", "bulk rename"), "Rename groups of files using regex, numbers, prefixes, or case transforms."),
        ])
        self._register_tab_tools("data", "Data Studio", "data", [
            ("_format_data", "Format and pretty-print data", ("format", "json", "yaml", "xml", "pretty", "beautify", "indent"), "Format and pretty-print JSON, YAML, or XML data."),
            ("_minify_data", "Minify JSON or XML", ("minify", "shrink", "compress json", "remove whitespace"), "Minify JSON or XML text by stripping whitespace."),
            ("_validate_text", "Validate syntax", ("validate", "syntax", "lint", "check json", "check yaml"), "Validate JSON, YAML, or XML syntax and report line errors."),
            ("_run_jsonpath_query", "Query JSON with JSONPath", ("jsonpath", "query json", "jq", "filter json", "eval query"), "Evaluate JSONPath queries to filter and extract data from JSON/YAML structures."),
            ("_infer_schema", "Infer JSON Schema", ("schema", "json schema", "infer schema", "generate schema"), "Infer a standard JSON Schema (Draft-07) from current data."),
            ("_convert_format", "Convert data format", ("convert data", "json to yaml", "yaml to json", "csv to json", "json to csv"), "Convert structured data between JSON, YAML, and CSV."),
            ("_open_cron_dialog", "Cron expression generator", ("cron", "schedule", "crontab", "job scheduler", "next run"), "Parse a cron expression into a human-readable description and preview its next run times."),
        ])
        self._register_tab_tools("encoding", "Encoding / Decoding", "encoding", [
            ("_encode_text", "Encode text (Base64/URL/HTML/Hex)", ("base64", "url encode", "html entities", "hex encode", "encode"), "Encode text using Base64, URL/percent-encoding, HTML entities, or hex."),
            ("_decode_text", "Decode text (Base64/URL/HTML/Hex)", ("base64 decode", "url decode", "html decode", "hex decode", "decode"), "Decode text encoded with Base64, URL/percent-encoding, HTML entities, or hex."),
            ("_encode_file", "Encode file to Base64/Hex/Binary", ("encode file", "file to base64", "file to hex"), "Encode an arbitrary local file to Base64, hex, or binary text."),
            ("_decode_to_file", "Decode text to file", ("decode file", "base64 to file", "hex to file"), "Decode Base64, hex, or binary text back to a saved local file."),
        ])
        self._register_tab_tools("hash", "Hash & Checksum", "hash", [
            ("_select_file", "Compute file checksum / hash", ("hash", "checksum", "sha256", "md5", "sha512", "integrity"), "Calculate SHA-256, MD5, SHA-512, and other cryptographic hashes of local files."),
            ("_verify_hash", "Verify file checksum against hash", ("verify hash", "check integrity", "sha256 verify", "compare hash"), "Verify file integrity against an expected hash or checksum."),
        ])
        self._register_tab_tools("network_monitor", "Network Monitor", "network_monitor", [
            ("_wipe_history", "Wipe network connection history", ("wipe", "clear history", "delete history", "reset"), "Permanently delete all logged connections and known destinations."),
            ("_set_retention", "Set network history retention period", ("retention", "history length", "days", "prune"), "Choose how many days of connection history to keep before old records are pruned."),
        ])

    def _register_tab_tools(self, prefix: str, category: str, tab_id: str, tools: list[tuple[str, str, tuple[str, ...], str]]) -> None:
        for method_name, title, keywords, description in tools:
            self.tool_registry.register(ToolDefinition(
                id=f"{prefix}.{method_name}", title=title, category=category,
                keywords=keywords, description=description,
                activate=lambda _checked=False, tab_id=tab_id, method_name=method_name: self._activate_tab_tool(self._get_tab(tab_id), method_name),
            ))

    def _activate_tab_tool(self, tab: QWidget, method_name: str) -> None:
        self.tabs.setCurrentWidget(tab)
        getattr(tab, method_name)()

    def _route_dropped_files(self, file_paths: list[str]) -> None:
        for file_path in file_paths:
            workspace = self.workspace_registry.find_for_path(file_path)
            if workspace is not None:
                self.open_workspace(workspace.id)
            shell_integration.route_file(self, file_path)

    def _default_palette(self, theme_name: str | None = None) -> dict[str, str]:
        theme_name = self.current_theme if theme_name is None else theme_name
        return _theme_default_palette(theme_name)

    def _load_ui_palette(self) -> dict[str, str]:
        return _theme_load_ui_palette(self.settings)

    def _save_ui_palette(self) -> None:
        if self.ui_palette:
            self.settings.setValue("app/ui_palette", json.dumps(self.ui_palette))
        else:
            self.settings.setValue("app/ui_palette", "")

    def _resolved_palette(self) -> dict[str, str]:
        palette = self._default_palette(self.current_theme).copy()
        palette.update(self.ui_palette)
        return palette

    def _parse_color_value(self, value: Any, fallback: str) -> QColor:
        return parse_color_value(value, fallback)

    def _rgba(self, color_value: str, alpha: float) -> str:
        return theme_rgba(color_value, alpha)

    def _apply_custom_palette(self, values: dict[str, str]) -> None:
        parsed_palette: dict[str, str] = {}
        defaults = self._default_palette(self.current_theme)
        for key, raw_value in values.items():
            if key not in defaults:
                continue
            color = self._parse_color_value(raw_value, defaults[key])
            if color.isValid():
                parsed_palette[key] = color.name()

        if parsed_palette:
            self.ui_palette.update(parsed_palette)
        else:
            self.ui_palette = {}

        if "accent" in self.ui_palette and self.ui_palette["accent"]:
            self.accent_color = self.ui_palette["accent"]
            self.settings.setValue("app/accent_color", self.accent_color)

        self._save_ui_palette()
        self._apply_theme()

    def set_button_radius(self, radius: int) -> int:
        self.button_radius = max(0, int(radius))
        self.settings.setValue("app/button_radius", self.button_radius)
        return self.button_radius

    def adjust_font_scale(self, delta: float | None) -> None:
        if delta is None:
            self.font_scale = 1.0
        else:
            self.font_scale = float(self.font_scale)
            if not math.isfinite(self.font_scale) or self.font_scale <= 0:
                self.font_scale = 1.0
            self.font_scale = max(0.8, min(1.8, self.font_scale + delta))
        self.settings.setValue("app/font_scale", self.font_scale)
        self._apply_font_scale()

    def _apply_font_scale(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        if not math.isfinite(self.font_scale) or self.font_scale <= 0:
            self.font_scale = 1.0

        font_size = max(9.0, 10.0 * self.font_scale)
        font = QFont(app.font())
        font.setStyleStrategy(font.StyleStrategy.PreferDefault)
        font.setPointSizeF(font_size)
        if font.pointSizeF() <= 0:
            font = QFont()
            font.setStyleStrategy(font.StyleStrategy.PreferDefault)
            font.setPointSizeF(font_size)

        app.setFont(font)
        self.setFont(font)
        for widget in app.allWidgets():
            widget.setFont(font)
        self._apply_theme()

    def set_theme(self, theme_name: str) -> None:
        theme_name = theme_name if theme_name in THEME_PRESET_ORDER else "dark"
        self.current_theme = theme_name
        self.settings.setValue("app/theme", theme_name)

        default_palette = self._default_palette(theme_name)
        self.accent_color = default_palette["accent"]
        self.settings.setValue("app/accent_color", self.accent_color)

        self.ui_palette = {}
        self._save_ui_palette()

        self._apply_theme()

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _arrow_icon_path(self, direction: str, color: str) -> str:
        cache_dir = Path(tempfile.gettempdir()) / "fosseverything_ui_icons"
        cache_dir.mkdir(exist_ok=True)
        key = hashlib.md5(f"{direction}-{color}".encode()).hexdigest()
        path = cache_dir / f"arrow_{key}.png"
        if not path.exists():
            size = 10
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(color))
            painter.setPen(Qt.PenStyle.NoPen)
            if direction == "down":
                points = [QPoint(2, 3), QPoint(8, 3), QPoint(5, 7)]
            else:
                points = [QPoint(2, 7), QPoint(8, 7), QPoint(5, 3)]
            painter.drawPolygon(QPolygon(points))
            painter.end()
            pixmap.save(str(path), "PNG")
        return path.as_posix()

    def _apply_theme(self) -> None:
        compact = bool(self.settings.value("app/compact_mode", False, type=bool))
        if compact:
            cfg = {"padding_x": 8, "padding_y": 4, "radius": 10, "spacing": 6, "toolbar_spacing": 3, "menu_padding_x": 8, "menu_padding_y": 3}
        else:
            cfg = {"padding_x": 12, "padding_y": 7, "radius": 10, "spacing": 10, "toolbar_spacing": 6, "menu_padding_x": 12, "menu_padding_y": 6}
        palette = self._resolved_palette()

        self._apply_stylesheet(cfg, palette)

        app = QApplication.instance()
        if app is not None:
            self._apply_qpalette(app, palette)

        notify_theme_changed()

    def _apply_stylesheet(self, cfg: dict[str, int], palette: dict[str, str]) -> None:
        accent = self.accent_color if self.accent_color else palette["accent"]
        accent_hover = self._rgba(accent, 0.18)
        text_color = palette["text"]
        bg_main = palette["background"]
        bg_panel = palette["panel"]
        input_bg = palette["input"]
        border = palette["border"]
        muted = palette["muted"]
        menu_bg = palette["menu"]
        toolbar_bg = palette["toolbar"]
        button_bg = palette["button"]
        tab_bg = palette["tab"]
        on_accent = (
            palette.get("on_accent")
            or self._default_palette(self.current_theme).get("on_accent")
            or self._default_palette("dark")["on_accent"]
        )
        selection_text = (
            palette.get("selection_text")
            or self._default_palette(self.current_theme).get("selection_text")
            or self._default_palette("dark")["selection_text"]
        )
        font_size = max(10.0, 10.0 * self.font_scale)
        radius = self.button_radius
        panel_radius = min(radius, 8)
        down_arrow_icon = self._arrow_icon_path("down", text_color)
        disabled_text = self._rgba(muted, 0.6)
        disabled_bg = self._rgba(border, 0.35)
        disabled_border = self._rgba(border, 0.6)

        css = f"""
            QWidget {{ background: {bg_main}; color: {text_color}; font-size: {font_size}pt; border-radius: 0px; }}
            QMainWindow, QTabWidget, QLabel, QFrame, QGroupBox, QAbstractItemView {{ background: {bg_main}; color: {text_color}; }}
            QTabBar::tab {{ background: {tab_bg}; color: {text_color}; border: 1px solid {border}; border-radius: {radius}px; padding: {cfg['padding_y'] + 2}px {cfg['padding_x'] + 4}px; font-size: {font_size}pt; }}
            QTabBar::tab:selected {{ background: {bg_panel}; border-bottom: 1px solid {accent}; color: {text_color}; }}
            QTabBar::tab:!selected:hover {{ background: {accent_hover}; border-color: {accent}; }}
            QPushButton, QToolButton {{ background: {button_bg}; color: {text_color}; border: 1px solid {border}; border-radius: {radius}px; padding: {cfg['padding_y']}px {cfg['padding_x']}px; font-size: {font_size}pt; }}
            QPushButton:hover, QToolButton:hover {{ background: {accent_hover}; border-color: {accent}; color: {text_color}; }}
            QPushButton:pressed, QToolButton:pressed, QPushButton:checked, QToolButton:checked {{ background: {accent}; border-color: {accent}; color: {on_accent}; }}
            QPushButton:focus, QToolButton:focus, QPushButton:checked:focus, QToolButton:checked:focus {{ border-color: {accent}; outline: none; }}
            QPushButton:disabled, QToolButton:disabled {{ background: {disabled_bg}; color: {disabled_text}; border-color: {disabled_border}; }}
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: {input_bg}; color: {text_color}; border: 1px solid {border}; border-radius: {radius}px; padding: {cfg['padding_y']}px {cfg['padding_x']-2}px; font-size: {font_size}pt; }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {accent}; }}
            QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{ background: {disabled_bg}; color: {disabled_text}; border-color: {disabled_border}; }}
            QLineEdit::selection, QTextEdit::selection, QPlainTextEdit::selection, QListWidget::item:selected, QTableWidget::item:selected, QTreeWidget::item:selected, QAbstractItemView::item:selected {{ background: {accent}; color: {selection_text}; }}
            QListWidget::item:hover:!selected, QTableWidget::item:hover:!selected, QTreeWidget::item:hover:!selected {{ background: {accent_hover}; }}
            QComboBox::drop-down {{ subcontrol-origin: border; subcontrol-position: top right; width: 22px; background: {button_bg}; border-left: 1px solid {border}; }}
            QComboBox::down-arrow {{ image: url({down_arrow_icon}); width: 10px; height: 10px; }}
            QCheckBox, QRadioButton {{ color: {text_color}; font-size: {font_size}pt; spacing: 8px; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {border}; background: {input_bg}; border-radius: 3px; }}
            QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
            QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {accent}; }}
            QRadioButton::indicator {{ width: 16px; height: 16px; border: 1px solid {border}; background: {input_bg}; border-radius: 8px; }}
            QRadioButton::indicator:checked {{ background: {accent}; border-color: {accent}; }}
            QScrollArea {{ background: {bg_main}; border: none; }}
            QMenuBar {{ background: {menu_bg}; color: {text_color}; border: 1px solid {border}; border-radius: 0px; font-size: {font_size}pt; }}
            QMenuBar::item {{ background: {menu_bg}; color: {text_color}; padding: {cfg['menu_padding_y']}px {cfg['menu_padding_x']}px; margin: 0px; }}
            QMenuBar::item:selected {{ background: {accent_hover}; color: {text_color}; }}
            QMenu {{ background: {bg_panel}; color: {text_color}; border: 1px solid {border}; border-radius: {panel_radius}px; padding: 4px; }}
            QMenu::item {{ background: transparent; color: {text_color}; padding: {cfg['menu_padding_y']}px {cfg['menu_padding_x']}px; border-radius: {max(panel_radius - 2, 0)}px; }}
            QMenu::item:selected {{ background: {accent_hover}; color: {text_color}; }}
            QMenu::separator {{ height: 1px; background: {border}; margin: 4px 6px; }}
            QToolBar {{ background: {toolbar_bg}; border: 1px solid {border}; border-radius: 0px; spacing: {cfg['toolbar_spacing']}px; padding: 2px; margin: 0px; font-size: {font_size}pt; }}
            QToolButton {{ background: {button_bg}; border: 1px solid {border}; border-radius: {radius}px; color: {text_color}; margin: 0px; padding: {cfg['padding_y']}px {cfg['padding_x']}px; }}
            QGroupBox {{ border: 1px solid {border}; border-radius: {panel_radius}px; margin-top: 12px; padding-top: 14px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {text_color}; }}
            QLabel {{ color: {text_color}; font-size: {font_size}pt; }}
            QLabel:disabled {{ color: {disabled_text}; }}
            QStatusBar {{ color: {muted}; }}
            QToolTip {{ background: {bg_panel}; color: {text_color}; border: 1px solid {border}; border-radius: 4px; padding: 4px 8px; }}
            QAbstractItemView {{ background: {bg_panel}; color: {text_color}; selection-background-color: {accent}; selection-color: {selection_text}; border: 1px solid {border}; border-radius: {panel_radius}px; alternate-background-color: {toolbar_bg}; }}
            QComboBox QAbstractItemView {{ border-radius: {panel_radius}px; background: {bg_panel}; color: {text_color}; }}
            QHeaderView::section {{ background: {toolbar_bg}; color: {text_color}; border: none; border-right: 1px solid {border}; border-bottom: 1px solid {border}; padding: {cfg['padding_y']}px {cfg['padding_x'] - 4}px; font-weight: 600; }}
            QHeaderView::section:hover {{ background: {accent_hover}; }}
            QTableCornerButton::section {{ background: {toolbar_bg}; border: 1px solid {border}; }}
            QProgressBar {{ background: {input_bg}; color: {text_color}; border: 1px solid {border}; border-radius: {panel_radius}px; text-align: center; min-height: 16px; }}
            QProgressBar::chunk {{ background: {accent}; border-radius: {max(panel_radius - 2, 0)}px; }}
            QSplitter::handle {{ background: {border}; }}
            QSplitter::handle:horizontal {{ width: 3px; }}
            QSplitter::handle:vertical {{ height: 3px; }}
            QSplitter::handle:hover {{ background: {accent}; }}
            QSlider::groove:horizontal {{ background: {border}; height: 4px; border-radius: 2px; }}
            QSlider::groove:vertical {{ background: {border}; width: 4px; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: {accent}; width: 14px; margin: -6px 0; border-radius: 7px; }}
            QSlider::handle:vertical {{ background: {accent}; height: 14px; margin: 0 -6px; border-radius: 7px; }}
            QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 2px; }}
            QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {border}; min-height: 24px; border-radius: 5px; }}
            QScrollBar::handle:vertical:hover {{ background: {accent}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; background: none; border: none; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
            QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
            QScrollBar::handle:horizontal {{ background: {border}; min-width: 24px; border-radius: 5px; }}
            QScrollBar::handle:horizontal:hover {{ background: {accent}; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; background: none; border: none; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
        """
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(css)
        else:
            self.setStyleSheet(css)
        self.menuBar().setStyleSheet(f"QMenuBar {{ background: {menu_bg}; color: {text_color}; border: 1px solid {border}; border-radius: 0px; }} QMenuBar::item {{ background: {menu_bg}; color: {text_color}; }} QMenuBar::item:selected {{ background: {accent_hover}; color: {text_color}; }} QMenu {{ background: {bg_panel}; color: {text_color}; border: 1px solid {border}; border-radius: 0px; }} QMenu::item {{ background: transparent; color: {text_color}; padding: {cfg['menu_padding_y']}px {cfg['menu_padding_x']}px; }} QMenu::item:selected {{ background: {accent_hover}; color: {text_color}; }}")

    def _apply_qpalette(self, app: QApplication, palette: dict[str, str]) -> None:
        bg_main = palette["background"]
        bg_panel = palette["panel"]
        input_bg = palette["input"]
        border = palette["border"]
        muted = palette["muted"]
        button_bg = palette["button"]
        text_color = palette["text"]
        accent = self.accent_color if self.accent_color else palette["accent"]
        selection_text = (
            palette.get("selection_text")
            or self._default_palette(self.current_theme).get("selection_text")
            or self._default_palette("dark")["selection_text"]
        )

        qpalette = app.palette()
        qpalette.setColor(qpalette.ColorRole.Window, QColor(bg_main))
        qpalette.setColor(qpalette.ColorRole.WindowText, QColor(text_color))
        qpalette.setColor(qpalette.ColorRole.Base, QColor(input_bg))
        qpalette.setColor(qpalette.ColorRole.AlternateBase, QColor(bg_panel))
        qpalette.setColor(qpalette.ColorRole.Text, QColor(text_color))
        qpalette.setColor(qpalette.ColorRole.Button, QColor(button_bg))
        qpalette.setColor(qpalette.ColorRole.ButtonText, QColor(text_color))
        qpalette.setColor(qpalette.ColorRole.Light, QColor(border))
        qpalette.setColor(qpalette.ColorRole.Mid, QColor(bg_panel))
        qpalette.setColor(qpalette.ColorRole.Dark, QColor(bg_main))
        qpalette.setColor(qpalette.ColorRole.Shadow, QColor(bg_main))
        qpalette.setColor(qpalette.ColorRole.ToolTipBase, QColor(bg_panel))
        qpalette.setColor(qpalette.ColorRole.ToolTipText, QColor(text_color))
        qpalette.setColor(qpalette.ColorRole.Highlight, QColor(accent))
        qpalette.setColor(qpalette.ColorRole.HighlightedText, QColor(selection_text))
        qpalette.setColor(qpalette.ColorRole.Link, QColor(accent))
        qpalette.setColor(qpalette.ColorRole.PlaceholderText, QColor(muted))
        app.setPalette(qpalette)

    def open_workspace(self, workspace_id: str) -> None:
        if workspace_id in self._TAB_MAKERS:
            self.tabs.setCurrentWidget(self._get_tab(workspace_id))

    def go_home(self) -> None:
        self.tabs.setCurrentWidget(self.home_page)
        self.home_page.focus_search()

    def open_tool_search(self) -> None:
        palette = ToolSearchPalette(self.tool_registry, self)
        if palette.exec() == ToolSearchPalette.DialogCode.Accepted and palette.selected_tool:
            palette.selected_tool.activate()

    def _open_settings_hub(self) -> None:
        hub = SettingsHub(self, self.settings, main_window=self)
        hub.settings_changed.connect(self._reload_appearance_from_settings)
        hub.exec()

    def _reload_appearance_from_settings(self) -> None:
        self.current_theme = str(self.settings.value("app/theme", self.current_theme))
        try:
            self.font_scale = float(self.settings.value("app/font_scale", self.font_scale))
        except (TypeError, ValueError):
            self.font_scale = 1.0
        if not math.isfinite(self.font_scale) or self.font_scale <= 0:
            self.font_scale = 1.0

        default_accent = self._default_palette(self.current_theme)["accent"]
        self.accent_color = str(self.settings.value("app/accent_color", default_accent))
        if not self._parse_color_value(self.accent_color, default_accent).isValid():
            self.accent_color = default_accent

        self.button_radius = int(self.settings.value("app/button_radius", self.button_radius))
        self.ui_palette = self._load_ui_palette()

        self._apply_font_scale()
        if self._home_page is not None:
            saved_view_mode = str(self.settings.value("home/view_mode", self.home_page.view_mode))
            if saved_view_mode != self.home_page.view_mode:
                self.home_page.set_view_mode(saved_view_mode)

    def closeEvent(self, event: Any) -> None:
        background_resident = bool(self.settings.value("app/background_resident", True, type=bool))
        if background_resident and self.tray_icon is not None and not self._force_quit:
            event.ignore()
            self.hide()
            return
        if bool(self.settings.value("app/remember_window", True, type=bool)):
            self.settings.setValue("app/window_geometry", self.saveGeometry())
        super().closeEvent(event)

