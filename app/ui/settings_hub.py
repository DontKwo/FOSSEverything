"""Centralized customization dashboard for appearance and window settings."""
from __future__ import annotations

import json
from typing import Any

from PyQt6.QtCore import QSettings, Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShowEvent
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QSlider, QCheckBox, QWidget, QGroupBox,
    QListWidget, QListWidgetItem, QFormLayout, QColorDialog, QFileDialog,
    QInputDialog, QMessageBox,
    QLabel, QLineEdit, QKeySequenceEdit, QScrollArea, QFrame
)

from app.core.spinbox import NoScrollSpinBox
from app.system import shell_integration
from app.core.theme import (
    DEFAULT_BUTTON_RADIUS,
    THEME_PRESET_LABELS,
    THEME_PRESET_ORDER,
    default_palette,
    load_ui_palette,
    resolved_palette,
    parse_color_value,
    profile_key,
)
from app.core.tooltips import get_tooltip_for
from app.ui.file_association_settings import FileAssociationSettings
from app.ui.settings_page import SettingsPage

PALETTE_FIELDS = [
    ("background", "Background"),
    ("panel", "Panel"),
    ("text", "Text"),
    ("muted", "Muted text"),
    ("border", "Border"),
    ("button", "Button"),
    ("input", "Input"),
    ("menu", "Menu"),
    ("toolbar", "Toolbar"),
    ("tab", "Tab"),
    ("accent", "Accent"),
    ("on_accent", "Text on accent"),
    ("selection_text", "Selection text"),
    ("success", "Success"),
    ("warning", "Warning"),
    ("danger", "Danger"),
]

PROFILE_SLOTS = 3


class AppearanceSettings(SettingsPage):
    """Theme, colors, fonts, and visual customization."""

    def setup_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        scroll.setWidget(inner)
        outer_layout.addWidget(scroll)

        form = QFormLayout()

        initial_palette = resolved_palette(self.settings)
        self.color_fields: dict[str, QLineEdit] = {}
        self.color_previews: dict[str, QLabel] = {}

        self.theme_combo = QComboBox()
        self.theme_combo.setToolTip(get_tooltip_for("Theme"))
        self.theme_combo.addItems([THEME_PRESET_LABELS[name] for name in THEME_PRESET_ORDER])
        current = str(self.settings.value("app/theme", "dark"))
        if current not in THEME_PRESET_ORDER:
            current = "dark"
        self.theme_combo.setCurrentIndex(THEME_PRESET_ORDER.index(current))
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow("Theme", self.theme_combo)

        accent_row = QHBoxLayout()
        self.accent_preview = QLabel()
        self.accent_preview.setFixedSize(48, 30)
        accent_btn = QPushButton("Choose accent color...")
        accent_btn.setToolTip(get_tooltip_for("Choose accent color..."))
        accent_btn.clicked.connect(self._pick_accent_color)
        accent_row.addWidget(self.accent_preview)
        accent_row.addWidget(accent_btn)
        accent_row.addStretch()
        form.addRow("Accent color", accent_row)
        self._update_accent_swatch(initial_palette["accent"])

        font_scale_row = QHBoxLayout()
        self.font_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_scale_slider.setRange(80, 180)
        self.font_scale_slider.setValue(int(float(self.settings.value("app/font_scale", 1.0)) * 100))
        self.font_scale_value_label = QLabel(f"{self.font_scale_slider.value()}%")
        self.font_scale_slider.valueChanged.connect(lambda value: self.font_scale_value_label.setText(f"{value}%"))
        font_scale_row.addWidget(self.font_scale_slider)
        font_scale_row.addWidget(self.font_scale_value_label)
        form.addRow("Text size", font_scale_row)

        self.button_radius_spin = NoScrollSpinBox()
        self.button_radius_spin.setToolTip(get_tooltip_for("Button roundness"))
        self.button_radius_spin.setRange(0, 20)
        self.button_radius_spin.setValue(int(self.settings.value("app/button_radius", DEFAULT_BUTTON_RADIUS)))
        form.addRow("Button roundness", self.button_radius_spin)

        self.compact_mode_check = QCheckBox("Compact UI (reduced spacing)")
        self.compact_mode_check.setToolTip(get_tooltip_for("Compact UI (reduced spacing)"))
        self.compact_mode_check.setChecked(bool(self.settings.value("app/compact_mode", False, type=bool)))
        form.addRow("", self.compact_mode_check)

        self.toolbar_compact_check = QCheckBox("Compact toolbars (icon-only)")
        self.toolbar_compact_check.setToolTip(get_tooltip_for("Compact toolbars (icon-only)"))
        self.toolbar_compact_check.setChecked(bool(self.settings.value("app/toolbar_compact", False, type=bool)))
        form.addRow("", self.toolbar_compact_check)

        layout.addLayout(form)

        colors_box = QGroupBox("Custom colors (advanced)")
        colors_box.setCheckable(True)
        has_custom_colors = bool(load_ui_palette(self.settings))
        colors_box.setChecked(has_custom_colors)
        colors_box.setToolTip(get_tooltip_for("Custom colors (advanced)"))
        colors_outer = QVBoxLayout(colors_box)
        colors_content = QWidget()
        colors_content.setVisible(has_custom_colors)
        colors_box.toggled.connect(colors_content.setVisible)
        colors_outer.addWidget(colors_content)
        colors_layout = QVBoxLayout(colors_content)
        colors_layout.setContentsMargins(0, 4, 0, 0)
        colors_form = QFormLayout()
        colors_form.setVerticalSpacing(12)
        colors_form.setHorizontalSpacing(14)

        for key, label in PALETTE_FIELDS:
            row, line_edit, preview = self._build_color_row(key, initial_palette[key])
            colors_form.addRow(label, row)
            self.color_fields[key] = line_edit
            self.color_previews[key] = preview
            if key == "accent":
                line_edit.textEdited.connect(self._update_accent_swatch)
        colors_layout.addLayout(colors_form)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Color profile"))
        self.profile_combo = QComboBox()
        self.profile_combo.setToolTip(get_tooltip_for("Color profile"))
        profile_row.addWidget(self.profile_combo)
        save_profile_btn = QPushButton("Save to profile")
        save_profile_btn.setToolTip(get_tooltip_for("Save to profile"))
        save_profile_btn.clicked.connect(self._save_profile)
        profile_row.addWidget(save_profile_btn)
        load_profile_btn = QPushButton("Load profile")
        load_profile_btn.setToolTip(get_tooltip_for("Load profile"))
        load_profile_btn.clicked.connect(self._load_profile)
        profile_row.addWidget(load_profile_btn)
        rename_profile_btn = QPushButton("Rename")
        rename_profile_btn.setToolTip(get_tooltip_for("Rename color profile"))
        rename_profile_btn.clicked.connect(self._rename_profile)
        profile_row.addWidget(rename_profile_btn)
        profile_row.addStretch()
        colors_layout.addLayout(profile_row)
        self._refresh_profile_combo()

        io_row = QHBoxLayout()
        export_btn = QPushButton("Export theme...")
        export_btn.setToolTip(get_tooltip_for("Export theme..."))
        export_btn.clicked.connect(self._export_theme)
        io_row.addWidget(export_btn)
        import_btn = QPushButton("Import theme...")
        import_btn.setToolTip(get_tooltip_for("Import theme..."))
        import_btn.clicked.connect(self._import_theme)
        io_row.addWidget(import_btn)
        io_row.addStretch()
        colors_layout.addLayout(io_row)

        reset_colors_btn = QPushButton("Reset colors to theme defaults")
        reset_colors_btn.setToolTip(get_tooltip_for("Reset colors to theme defaults"))
        reset_colors_btn.clicked.connect(self._reset_colors)
        colors_layout.addWidget(reset_colors_btn)

        layout.addWidget(colors_box)
        layout.addStretch()

    def _current_theme_name(self) -> str:
        return THEME_PRESET_ORDER[self.theme_combo.currentIndex()]

    def _build_color_row(self, key: str, initial_value: str) -> tuple[QHBoxLayout, QLineEdit, QLabel]:
        line_edit = QLineEdit(initial_value)
        line_edit.setPlaceholderText("#RRGGBB or rgb(r, g, b)")
        line_edit.setMinimumWidth(170)
        line_edit.setMinimumHeight(30)
        preview = QLabel()
        preview.setFixedSize(48, 30)
        self._update_preview(line_edit, preview, key)
        line_edit.textEdited.connect(lambda _text, k=key, f=line_edit, p=preview: self._update_preview(f, p, k))

        pick_button = QPushButton("Pick")
        pick_button.setToolTip(get_tooltip_for(f"Pick {key} color"))
        pick_button.setMinimumHeight(30)
        pick_button.clicked.connect(lambda _checked=False, k=key, f=line_edit, p=preview: self._pick_color(k, f, p))

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(line_edit)
        row.addWidget(preview)
        row.addWidget(pick_button)
        return row, line_edit, preview

    def _update_preview(self, line_edit: QLineEdit, preview: QLabel, key: str) -> None:
        fallback = default_palette(self._current_theme_name())[key]
        color = parse_color_value(line_edit.text(), fallback)
        border = self.color_fields["border"].text() if "border" in self.color_fields else default_palette(self._current_theme_name())["border"]
        preview.setStyleSheet(f"background: {color.name()}; border: 2px solid {border}; border-radius: 4px; min-width: 48px; max-width: 48px; min-height: 30px; max-height: 30px;")

    def _pick_color(self, key: str, line_edit: QLineEdit, preview: QLabel) -> None:
        fallback = default_palette(self._current_theme_name())[key]
        current = parse_color_value(line_edit.text(), fallback)
        chosen = QColorDialog.getColor(current, self, f"Choose {key} color")
        if chosen.isValid():
            line_edit.setText(chosen.name())
            self._update_preview(line_edit, preview, key)

    def _on_theme_changed(self) -> None:
        defaults = default_palette(self._current_theme_name())
        for key, field in self.color_fields.items():
            field.setText(defaults[key])
            self._update_preview(field, self.color_previews[key], key)
        self._update_accent_swatch(defaults["accent"])

    def _update_accent_swatch(self, color_value: str) -> None:
        fallback = default_palette(self._current_theme_name())["accent"]
        color = parse_color_value(color_value, fallback)
        border = self.color_fields["border"].text() if "border" in self.color_fields else default_palette(self._current_theme_name())["border"]
        self.accent_preview.setStyleSheet(f"background: {color.name()}; border: 2px solid {border}; border-radius: 4px;")

    def _pick_accent_color(self) -> None:
        fallback = default_palette(self._current_theme_name())["accent"]
        current_hex = self.color_fields["accent"].text() if "accent" in self.color_fields else fallback
        current_color = parse_color_value(current_hex, fallback)
        chosen = QColorDialog.getColor(current_color, self, "Choose accent color")
        if chosen.isValid():
            if "accent" in self.color_fields:
                self.color_fields["accent"].setText(chosen.name())
                self._update_preview(self.color_fields["accent"], self.color_previews["accent"], "accent")
            self._update_accent_swatch(chosen.name())

    def _profile_entry(self, slot: int) -> dict:
        raw = self.settings.value(profile_key(slot), "")
        if not raw:
            return {}
        try:
            data = json.loads(str(raw))
        except (TypeError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _profile_label(self, slot: int) -> str:
        entry = self._profile_entry(slot)
        if not entry:
            return f"Profile {slot} (empty)"
        name = entry.get("name")
        return name if isinstance(name, str) and name.strip() else f"Profile {slot}"

    def _refresh_profile_combo(self) -> None:
        current_index = self.profile_combo.currentIndex() if self.profile_combo.count() else 0
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for slot in range(1, PROFILE_SLOTS + 1):
            self.profile_combo.addItem(self._profile_label(slot))
        self.profile_combo.setCurrentIndex(max(0, min(current_index, PROFILE_SLOTS - 1)))
        self.profile_combo.blockSignals(False)

    def _save_profile(self) -> None:
        slot = self.profile_combo.currentIndex() + 1
        existing_name = self._profile_entry(slot).get("name")
        values = {key: field.text() for key, field in self.color_fields.items()}
        values["name"] = existing_name if isinstance(existing_name, str) and existing_name.strip() else f"Profile {slot}"
        self.settings.setValue(profile_key(slot), json.dumps(values))
        self._refresh_profile_combo()

    def _load_profile(self) -> None:
        slot = self.profile_combo.currentIndex() + 1
        entry = self._profile_entry(slot)
        if not entry:
            return
        for key, field in self.color_fields.items():
            value = entry.get(key)
            if isinstance(value, str) and value:
                field.setText(value)
                self._update_preview(field, self.color_previews[key], key)
        if isinstance(entry.get("accent"), str) and entry["accent"]:
            self._update_accent_swatch(entry["accent"])
        self.save_settings()
        if self.main_window is not None:
            self.main_window._reload_appearance_from_settings()

    def _rename_profile(self) -> None:
        slot = self.profile_combo.currentIndex() + 1
        entry = self._profile_entry(slot)
        if not entry:
            QMessageBox.information(self, "Rename profile", "Save this profile before renaming it.")
            return
        current_name = entry.get("name") if isinstance(entry.get("name"), str) else f"Profile {slot}"
        new_name, accepted = QInputDialog.getText(self, "Rename profile", "Profile name:", text=current_name)
        if accepted and new_name.strip():
            entry["name"] = new_name.strip()
            self.settings.setValue(profile_key(slot), json.dumps(entry))
            self._refresh_profile_combo()

    def _export_theme(self) -> None:
        get_save_file_name = getattr(QFileDialog, "_foss_original_get_save_file_name", QFileDialog.getSaveFileName)
        path, _ = get_save_file_name(self, "Export theme", "theme.json", "JSON files (*.json)")
        if not path:
            return
        values = {key: field.text() for key, field in self.color_fields.items()}
        values["name"] = "Exported theme"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(values, handle, indent=2)

    def _import_theme(self) -> None:
        get_open_file_name = getattr(QFileDialog, "_foss_original_get_open_file_name", QFileDialog.getOpenFileName)
        path, _ = get_open_file_name(self, "Import theme", "", "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            QMessageBox.warning(self, "Import theme", "Could not read that file as a theme.")
            return
        if not isinstance(data, dict):
            QMessageBox.warning(self, "Import theme", "That file isn't a valid theme.")
            return
        for key, field in self.color_fields.items():
            value = data.get(key)
            if isinstance(value, str) and value:
                field.setText(value)
                self._update_preview(field, self.color_previews[key], key)
        if isinstance(data.get("accent"), str) and data["accent"]:
            self._update_accent_swatch(data["accent"])

    def _reset_colors(self) -> None:
        self._on_theme_changed()

    def save_settings(self) -> None:
        theme = self._current_theme_name()
        self.settings.setValue("app/theme", theme)
        self.settings.setValue("app/font_scale", self.font_scale_slider.value() / 100.0)
        self.settings.setValue("app/button_radius", self.button_radius_spin.value())
        self.settings.setValue("app/compact_mode", self.compact_mode_check.isChecked())
        self.settings.setValue("app/toolbar_compact", self.toolbar_compact_check.isChecked())

        defaults = default_palette(theme)
        parsed_palette = {key: parse_color_value(field.text(), defaults[key]).name() for key, field in self.color_fields.items()}
        self.settings.setValue("app/ui_palette", json.dumps(parsed_palette))
        self.settings.setValue("app/accent_color", parsed_palette["accent"])

    def reset_to_defaults(self) -> None:
        self.theme_combo.setCurrentIndex(0)
        self.font_scale_slider.setValue(100)
        self.button_radius_spin.setValue(DEFAULT_BUTTON_RADIUS)
        self.compact_mode_check.setChecked(False)
        self.toolbar_compact_check.setChecked(False)
        self._on_theme_changed()


class WindowLayoutSettings(SettingsPage):
    """Window size, position, startup behavior, and home/view options."""

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.remember_window_check = QCheckBox("Remember window size and position")
        self.remember_window_check.setToolTip(get_tooltip_for("Remember window size and position"))
        self.remember_window_check.setChecked(bool(self.settings.value("app/remember_window", True, type=bool)))
        form.addRow("", self.remember_window_check)

        self.maximize_on_start_check = QCheckBox("Maximize window on startup")
        self.maximize_on_start_check.setToolTip(get_tooltip_for("Maximize window on startup"))
        self.maximize_on_start_check.setChecked(bool(self.settings.value("app/maximize_on_start", True, type=bool)))
        form.addRow("", self.maximize_on_start_check)

        self.background_resident_check = QCheckBox("Keep running in the system tray for instant file opening")
        self.background_resident_check.setToolTip(get_tooltip_for("Keep running in the system tray for instant file opening"))
        self.background_resident_check.setChecked(bool(self.settings.value("app/background_resident", True, type=bool)))
        form.addRow("", self.background_resident_check)

        layout.addLayout(form)

        home_box = QGroupBox("Home && view")
        home_form = QFormLayout(home_box)

        self.home_layout_combo = QComboBox()
        self.home_layout_combo.setToolTip(get_tooltip_for("Home layout"))
        self.home_layout_combo.addItems(["Tiles", "Compact list"])
        current_view_mode = str(self.settings.value("home/view_mode", "tiles"))
        self.home_layout_combo.setCurrentIndex(1 if current_view_mode == "compact" else 0)
        self.home_layout_combo.currentIndexChanged.connect(self._on_home_layout_changed)
        home_form.addRow("Home layout", self.home_layout_combo)

        self.start_on_favorites_check = QCheckBox("Open app on Favorites page")
        self.start_on_favorites_check.setToolTip(get_tooltip_for("Open app on Favorites page"))
        self.start_on_favorites_check.setChecked(bool(self.settings.value("home/start_on_favorites", False, type=bool)))
        home_form.addRow("", self.start_on_favorites_check)

        self.favorites_tiles_check = QCheckBox("Show Favorites as tiles")
        self.favorites_tiles_check.setToolTip(get_tooltip_for("Show Favorites as tiles"))
        self.favorites_tiles_check.setChecked(str(self.settings.value("home/favorites_view_override", "")) == "tiles")
        self.favorites_tiles_check.setVisible(current_view_mode == "compact")
        home_form.addRow("", self.favorites_tiles_check)

        self.sort_mode_combo = QComboBox()
        self.sort_mode_combo.setToolTip(get_tooltip_for("App sort order"))
        self.sort_mode_combo.addItems(["Alphabetical", "Custom order", "Recently used"])
        sort_values = ["alphabetical", "custom", "recent"]
        current_sort = str(self.settings.value("home/sort_mode", "alphabetical"))
        self.sort_mode_combo.setCurrentIndex(sort_values.index(current_sort) if current_sort in sort_values else 0)
        home_form.addRow("App sort order", self.sort_mode_combo)

        self.recent_max_spin = NoScrollSpinBox()
        self.recent_max_spin.setToolTip(get_tooltip_for("Recent items to keep"))
        self.recent_max_spin.setRange(5, 50)
        self.recent_max_spin.setValue(int(self.settings.value("home/recent_max", 10)))
        home_form.addRow("Recent items to keep", self.recent_max_spin)

        if self.main_window is not None:
            fullscreen_btn = QPushButton("Toggle fullscreen now")
            fullscreen_btn.setToolTip(get_tooltip_for("Toggle fullscreen now"))
            fullscreen_btn.clicked.connect(self.main_window._toggle_fullscreen)
            home_form.addRow("", fullscreen_btn)

        layout.addWidget(home_box)
        layout.addStretch()

    def _on_home_layout_changed(self, index: int) -> None:
        self.favorites_tiles_check.setVisible(index == 1)

    def save_settings(self) -> None:
        self.settings.setValue("app/remember_window", self.remember_window_check.isChecked())
        self.settings.setValue("app/maximize_on_start", self.maximize_on_start_check.isChecked())
        self.settings.setValue("app/background_resident", self.background_resident_check.isChecked())
        self.settings.setValue("home/view_mode", "compact" if self.home_layout_combo.currentIndex() == 1 else "tiles")
        self.settings.setValue("home/start_on_favorites", self.start_on_favorites_check.isChecked())
        self.settings.setValue("home/favorites_view_override", "tiles" if self.favorites_tiles_check.isChecked() else "")
        sort_values = ["alphabetical", "custom", "recent"]
        self.settings.setValue("home/sort_mode", sort_values[self.sort_mode_combo.currentIndex()])
        self.settings.setValue("home/recent_max", self.recent_max_spin.value())

    def reset_to_defaults(self) -> None:
        self.remember_window_check.setChecked(True)
        self.maximize_on_start_check.setChecked(True)
        self.background_resident_check.setChecked(True)
        self.home_layout_combo.setCurrentIndex(0)
        self.start_on_favorites_check.setChecked(False)
        self.favorites_tiles_check.setChecked(False)
        self.sort_mode_combo.setCurrentIndex(0)
        self.recent_max_spin.setValue(10)


class KeybindingsSettings(SettingsPage):
    """View and rebind global application keyboard shortcuts."""

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        shortcut_defs = getattr(self.main_window, "shortcut_defs", None) if self.main_window is not None else None
        self.editors: dict[str, QKeySequenceEdit] = {}
        self.defaults: dict[str, str] = {}

        if not shortcut_defs:
            layout.addWidget(QLabel("Keybindings are unavailable."))
            layout.addStretch()
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)
        form.setVerticalSpacing(12)
        form.setHorizontalSpacing(14)

        for shortcut_id, entry in shortcut_defs.items():
            default = entry["default"]
            label = entry["label"]
            self.defaults[shortcut_id] = default

            editor = QKeySequenceEdit(entry["action"].shortcut())
            editor.setMinimumWidth(160)
            self.editors[shortcut_id] = editor

            default_label = QLabel(f"Default: {default}")

            reset_btn = QPushButton("Reset")
            reset_btn.setToolTip(get_tooltip_for(f"Reset {label} shortcut"))
            reset_btn.clicked.connect(lambda _checked=False, sid=shortcut_id: self._reset_one(sid))

            row = QHBoxLayout()
            row.addWidget(editor)
            row.addWidget(default_label)
            row.addWidget(reset_btn)
            row.addStretch()
            form.addRow(label, row)

        scroll.setWidget(inner)
        layout.addWidget(scroll)

    def _reset_one(self, shortcut_id: str) -> None:
        editor = self.editors.get(shortcut_id)
        default = self.defaults.get(shortcut_id)
        if editor is not None and default is not None:
            editor.setKeySequence(QKeySequence(default))

    def save_settings(self) -> None:
        if self.main_window is None:
            return
        shortcut_defs = getattr(self.main_window, "shortcut_defs", {})
        for shortcut_id, editor in self.editors.items():
            entry = shortcut_defs.get(shortcut_id)
            if entry is None:
                continue
            sequence = editor.keySequence()
            entry["action"].setShortcut(sequence)
            self.settings.setValue(f"shortcuts/{shortcut_id}", sequence.toString())

    def reset_to_defaults(self) -> None:
        for shortcut_id in self.editors:
            self._reset_one(shortcut_id)


class SettingsHub(QDialog):
    """Central settings and customization dashboard."""

    settings_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None, settings: QSettings | None = None, main_window: Any = None) -> None:
        super().__init__(parent)
        self.settings = settings or QSettings("FOSSEverything", "FOSSEverything")
        self.main_window = main_window
        self.setWindowTitle("Settings")
        self.setMinimumSize(480, 400)
        self.resize(760, 640)

        main_layout = QVBoxLayout(self)

        content = QHBoxLayout()

        self.category_list = QListWidget()
        self.category_list.setMinimumWidth(150)
        self.category_list.setMaximumWidth(180)
        self.category_list.itemSelectionChanged.connect(self._on_category_selected)
        content.addWidget(self.category_list, 0)

        self.pages_widget = QWidget()
        self.pages_layout = QVBoxLayout(self.pages_widget)
        content.addWidget(self.pages_widget, 1)

        self.pages: dict[str, SettingsPage] = {
            "appearance": AppearanceSettings(self.settings, main_window),
            "window": WindowLayoutSettings(self.settings, main_window),
            "keybindings": KeybindingsSettings(self.settings, main_window),
            "file_associations": FileAssociationSettings(self.settings, main_window),
        }

        categories = [
            ("Appearance", "appearance", "Theme, colors, fonts, and visual style"),
            ("Window & Layout", "window", "Window size and startup behavior"),
            ("Keybindings", "keybindings", "View and rebind keyboard shortcuts"),
            ("File Associations", "file_associations", "Set FOSSEverything as the default app for file types"),
        ]

        for name, key, description in categories:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.category_list.addItem(item)

        buttons = QHBoxLayout()
        wizard_btn = QPushButton("Run Setup Wizard...")
        wizard_btn.setToolTip(get_tooltip_for("Run Setup Wizard..."))
        wizard_btn.clicked.connect(self._run_setup_wizard)
        reset_btn = QPushButton("Reset to defaults")
        reset_btn.setToolTip(get_tooltip_for("Reset settings to defaults"))
        reset_btn.clicked.connect(self._reset_all)
        apply_btn = QPushButton("Apply")
        apply_btn.setToolTip(get_tooltip_for("Apply settings"))
        apply_btn.clicked.connect(self._apply)
        close_btn = QPushButton("Close")
        close_btn.setToolTip(get_tooltip_for("Close"))
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(wizard_btn)
        buttons.addStretch()
        buttons.addWidget(reset_btn)
        buttons.addWidget(apply_btn)
        buttons.addWidget(close_btn)

        main_layout.addLayout(content)
        main_layout.addLayout(buttons)

        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)

    def showEvent(self, event: QShowEvent) -> None:  # noqa: 21 (Qt virtual override, invoked by the framework)
        super().showEvent(event)
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        frame_margin_w = max(0, self.frameGeometry().width() - self.geometry().width())
        frame_margin_h = max(0, self.frameGeometry().height() - self.geometry().height())
        max_width = max(400, int(avail.width() * 0.92) - frame_margin_w)
        max_height = max(300, int(avail.height() * 0.92) - frame_margin_h)
        self.setMaximumSize(max_width, max_height)
        if self.width() > max_width or self.height() > max_height:
            self.resize(min(self.width(), max_width), min(self.height(), max_height))
        x = avail.x() + max(0, (avail.width() - self.width()) // 2)
        y = avail.y() + max(0, (avail.height() - self.height()) // 2)
        self.move(x, y)

    def _on_category_selected(self) -> None:
        item = self.category_list.currentItem()
        if item:
            key = item.data(Qt.ItemDataRole.UserRole)
            page = self.pages.get(key)
            if page:
                while self.pages_layout.count():
                    self.pages_layout.takeAt(0).widget().hide()
                self.pages_layout.addWidget(page)
                page.show()

    def _run_setup_wizard(self) -> None:
        from app.ui.setup_wizard import SetupWizard  # noqa: 13 (avoids a circular import: setup_wizard.py embeds FileAssociationSettings from this module)
        SetupWizard(self.settings, main_window=self.main_window, parent=self).exec()

    def _reset_all(self) -> None:
        for page in self.pages.values():
            page.reset_to_defaults()

    def _apply(self) -> None:
        for page in self.pages.values():
            page.save_settings()
        self.settings_changed.emit()
