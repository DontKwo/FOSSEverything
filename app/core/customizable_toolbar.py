import json
from typing import Any, Callable, Dict, List, Optional, Set

from PyQt6.QtCore import QSettings, QSize, Qt, QTimer
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence
from PyQt6.QtWidgets import (  # noqa: 31 (QSpinBox used only for isinstance, matches NoScrollSpinBox subclass too)
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSpinBox,
    QStyle,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.core.theme import theme_signals
from app.core.tooltips import get_tooltip_for
from app.ui.ui_scaling import scaled_font_pt, scaled_font_size

# Ordered longest/most-specific keyword first: the first substring match against
# the normalized label wins, so "save as" must be tested before the bare "save".
_STANDARD_ICON_KEYWORDS: tuple[tuple[str, QStyle.StandardPixmap], ...] = (
    ("new folder", QStyle.StandardPixmap.SP_FileDialogNewFolder),
    ("open file", QStyle.StandardPixmap.SP_DialogOpenButton),
    ("open files", QStyle.StandardPixmap.SP_DialogOpenButton),
    ("add file", QStyle.StandardPixmap.SP_DialogOpenButton),
    ("browse", QStyle.StandardPixmap.SP_DialogOpenButton),
    ("import", QStyle.StandardPixmap.SP_DialogOpenButton),
    ("open", QStyle.StandardPixmap.SP_DialogOpenButton),
    ("save as", QStyle.StandardPixmap.SP_DialogSaveButton),
    ("save file", QStyle.StandardPixmap.SP_DialogSaveButton),
    ("save", QStyle.StandardPixmap.SP_DialogSaveButton),
    ("export", QStyle.StandardPixmap.SP_DialogSaveButton),
    ("download", QStyle.StandardPixmap.SP_ArrowDown),
    ("undo", QStyle.StandardPixmap.SP_ArrowBack),
    ("previous", QStyle.StandardPixmap.SP_ArrowBack),
    ("back", QStyle.StandardPixmap.SP_ArrowBack),
    ("redo", QStyle.StandardPixmap.SP_ArrowForward),
    ("next", QStyle.StandardPixmap.SP_ArrowForward),
    ("forward", QStyle.StandardPixmap.SP_ArrowForward),
    ("delete", QStyle.StandardPixmap.SP_TrashIcon),
    ("remove", QStyle.StandardPixmap.SP_TrashIcon),
    ("clear", QStyle.StandardPixmap.SP_TrashIcon),
    ("trash", QStyle.StandardPixmap.SP_TrashIcon),
    ("refresh", QStyle.StandardPixmap.SP_BrowserReload),
    ("reload", QStyle.StandardPixmap.SP_BrowserReload),
    ("cancel", QStyle.StandardPixmap.SP_DialogCancelButton),
    ("close", QStyle.StandardPixmap.SP_DialogCloseButton),
    ("apply", QStyle.StandardPixmap.SP_DialogApplyButton),
    ("play", QStyle.StandardPixmap.SP_MediaPlay),
    ("pause", QStyle.StandardPixmap.SP_MediaPause),
    ("stop", QStyle.StandardPixmap.SP_MediaStop),
    ("help", QStyle.StandardPixmap.SP_DialogHelpButton),
    ("info", QStyle.StandardPixmap.SP_MessageBoxInformation),
)


def _normalize_label(text: str) -> str:
    normalized = text.lower().lstrip("*").strip()
    normalized = normalized.split("(")[0].split("...")[0]
    return normalized.strip(" .")


def standard_icon_for_label(text: str) -> Optional[QStyle.StandardPixmap]:
    """Best-effort standard-icon lookup by keyword, so toolbar/button labels
    get a real icon instead of relying on manually typed text markers."""
    normalized = _normalize_label(text)
    for keyword, pixmap in _STANDARD_ICON_KEYWORDS:
        if keyword in normalized:
            return pixmap
    return None


def apply_standard_icon(button: QPushButton, text: str) -> None:
    """Give a plain QPushButton a real icon based on its label, when one matches."""
    pixmap = standard_icon_for_label(text)
    if pixmap is not None:
        button.setIcon(button.style().standardIcon(pixmap))


def build_dialog_panel(parent: QWidget, title: str, list_widget: "DragDropListWidget") -> QWidget:
    panel = QWidget(parent)
    panel_layout = QVBoxLayout(panel)
    panel_layout.addWidget(QLabel(title))
    panel_layout.addWidget(list_widget)
    return panel


class DragDropListWidget(QListWidget):
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasText() or event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        if event.source() is self:
            super().dropEvent(event)
            return

        source_widget = event.source()
        if not isinstance(source_widget, QListWidget):
            event.ignore()
            return

        source_item = source_widget.currentItem()
        if source_item is None:
            event.ignore()
            return

        new_item = source_item.clone()
        target_row = self.indexAt(event.position().toPoint()).row()
        if target_row >= 0:
            self.insertItem(target_row, new_item)
        else:
            self.addItem(new_item)
        self.setCurrentItem(new_item)
        source_widget.takeItem(source_widget.row(source_item))
        event.acceptProposedAction()


class ToolbarCustomizationDialog(QDialog):
    def __init__(self, toolbar: "AppToolBar", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.toolbar = toolbar
        self.setWindowTitle("Customize toolbar")
        self.resize(520, 360)

        root_layout = QVBoxLayout(self)
        label = QLabel("Drag items to reorder. Move them between visible and hidden sections.")
        root_layout.addWidget(label)

        list_layout = QHBoxLayout()
        self.visible_list = DragDropListWidget()
        self.visible_list.setDragDropMode(self.visible_list.DragDropMode.InternalMove)
        self.hidden_list = DragDropListWidget()
        self.hidden_list.setDragDropMode(self.hidden_list.DragDropMode.InternalMove)

        list_layout.addWidget(build_dialog_panel(self, "Visible", self.visible_list))
        list_layout.addWidget(build_dialog_panel(self, "Hidden / overflow", self.hidden_list))
        root_layout.addLayout(list_layout)

        button_row = QHBoxLayout()
        hide_btn = QPushButton("Hide >")
        hide_btn.setToolTip(get_tooltip_for("Hide Toolbar Item"))
        show_btn = QPushButton("< Show")
        show_btn.setToolTip(get_tooltip_for("Show Toolbar Item"))
        up_btn = QPushButton("Move up")
        up_btn.setToolTip(get_tooltip_for("Move Toolbar Item Up"))
        down_btn = QPushButton("Move down")
        down_btn.setToolTip(get_tooltip_for("Move Toolbar Item Down"))
        reset_btn = QPushButton("Reset")
        reset_btn.setToolTip(get_tooltip_for("Reset Toolbar"))
        done_btn = QPushButton("Done")
        done_btn.setToolTip(get_tooltip_for("Done Customizing Toolbar"))

        hide_btn.clicked.connect(self._move_visible_to_hidden)
        show_btn.clicked.connect(self._move_hidden_to_visible)
        up_btn.clicked.connect(self._move_selected_up)
        down_btn.clicked.connect(self._move_selected_down)
        reset_btn.clicked.connect(self._reset_to_defaults)
        done_btn.clicked.connect(self.accept)

        for btn in (hide_btn, show_btn, up_btn, down_btn, reset_btn, done_btn):
            button_row.addWidget(btn)
        root_layout.addLayout(button_row)

        self.refresh_lists()

    def refresh_lists(self) -> None:
        self.visible_list.clear()
        self.hidden_list.clear()

        for entry in self.toolbar.visible_items():
            item = QListWidgetItem(entry["label"])
            item.setData(Qt.ItemDataRole.UserRole, entry["key"])
            self.visible_list.addItem(item)

        for entry in self.toolbar.hidden_items():
            item = QListWidgetItem(entry["label"])
            item.setData(Qt.ItemDataRole.UserRole, entry["key"])
            self.hidden_list.addItem(item)

    def _move_visible_to_hidden(self) -> None:
        row = self.visible_list.currentRow()
        if row < 0:
            return
        item = self.visible_list.takeItem(row)
        if item is not None:
            self.hidden_list.addItem(item)

    def _move_hidden_to_visible(self) -> None:
        row = self.hidden_list.currentRow()
        if row < 0:
            return
        item = self.hidden_list.takeItem(row)
        if item is not None:
            self.visible_list.addItem(item)

    def _move_selected_up(self) -> None:
        list_widget = self.visible_list if self.visible_list.hasFocus() else self.hidden_list
        row = list_widget.currentRow()
        if row > 0:
            item = list_widget.takeItem(row)
            list_widget.insertItem(row - 1, item)
            list_widget.setCurrentRow(row - 1)

    def _move_selected_down(self) -> None:
        list_widget = self.visible_list if self.visible_list.hasFocus() else self.hidden_list
        row = list_widget.currentRow()
        if row >= 0 and row < list_widget.count() - 1:
            item = list_widget.takeItem(row)
            list_widget.insertItem(row + 1, item)
            list_widget.setCurrentRow(row + 1)

    def _reset_to_defaults(self) -> None:
        self.toolbar.restore_defaults()
        self.refresh_lists()

    def apply(self) -> None:
        visible_keys = [self.visible_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.visible_list.count())]
        hidden_keys = [self.hidden_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.hidden_list.count())]
        self.toolbar.set_custom_state(visible_keys, hidden_keys)


class AppToolBar(QToolBar):
    """Shared, customizable toolbar used by every tab: grouped actions with real
    separators, optional standard icons, an overflow menu, drag-to-reorder /
    hide via the customize dialog, and a global compact (icon-only) mode."""

    def __init__(self, settings: Optional[QSettings], scope: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.settings = settings or QSettings("FOSSEverything", "FOSSEverything")
        self.scope = scope
        self._entries = []
        self._default_entries = []
        self._entry_by_key = {}
        self._hidden_keys = set()
        self._rebuilding = False
        self._extra_rows: List[QToolBar] = []
        self._separator_count = 0
        self._last_reflow_width = 0

        self._more_menu = QMenu(self)
        self._more_action = QAction("More", self)
        self._more_action.setMenu(self._more_menu)
        self._more_action.setVisible(False)

        self._more_action.setToolTip(get_tooltip_for("More"))

        self._customize_action = QAction("Customize...", self)
        self._customize_action.setToolTip(get_tooltip_for("Customize toolbar"))
        self._customize_action.triggered.connect(self.open_customizer)

        theme_signals.changed.connect(self._apply_style)

    def add_action(
        self,
        text: str,
        callback: Optional[Callable[[], None]] = None,
        *,
        icon: Optional[QStyle.StandardPixmap] = None,
        shortcut: QKeySequence.StandardKey | str | None = None,
        checkable: bool = False,
        tooltip_key: Optional[str] = None,
    ) -> QAction:
        """Convenience factory: build a QAction (tooltip looked up from the
        shared tooltip dictionary, by tooltip_key if given else by its text)
        and add it in one call."""
        action = QAction(text, self)
        resolved_icon = icon if icon is not None else standard_icon_for_label(text)
        if resolved_icon is not None:
            action.setIcon(self.style().standardIcon(resolved_icon))
        action.setToolTip(get_tooltip_for(tooltip_key or text))
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        if checkable:
            action.setCheckable(True)
        if callback is not None:
            action.triggered.connect(callback)
        self.addAction(action)
        return action

    def _make_key(self, entry_type: str, source: Any) -> str:
        if isinstance(source, QAction):
            text = source.text() or source.objectName() or f"action_{len(self._entries)}"
            return f"{entry_type}:{text}"
        if hasattr(source, "text"):
            text = source.text() or source.objectName() or f"widget_{len(self._entries)}"
            return f"{entry_type}:{text}"
        return f"{entry_type}:{len(self._entries)}"

    def addAction(self, action: QAction) -> QAction:
        key = self._make_key("action", action)
        if not self._rebuilding and key not in self._entry_by_key:
            self._entry_by_key[key] = {"key": key, "label": action.text() or action.objectName() or "Action", "type": "action", "action": action}
            self._entries.append(self._entry_by_key[key])
        return super().addAction(action)

    def addSeparator(self) -> QAction:
        action = QAction(self)
        action.setSeparator(True)
        self._separator_count += 1
        key = f"separator:{self._separator_count}"
        if not self._rebuilding:
            self._entry_by_key[key] = {"key": key, "label": "Separator", "type": "separator", "action": action}
            self._entries.append(self._entry_by_key[key])
        return super().addAction(action)

    def addWidget(self, widget: QWidget) -> QAction:
        if isinstance(widget, (QLabel, QSpinBox, QComboBox)):
            return super().addWidget(widget)

        key = self._make_key("widget", widget)
        if not self._rebuilding and key not in self._entry_by_key:
            label = getattr(widget, "text", lambda: widget.objectName() or "Widget")()
            label = label if isinstance(label, str) and label else (widget.objectName() or "Widget")
            self._entry_by_key[key] = {"key": key, "label": label, "type": "widget", "widget": widget}
            self._entries.append(self._entry_by_key[key])
        return super().addWidget(widget)

    def visible_items(self) -> List[Dict[str, Any]]:
        return [entry for entry in self._entries if entry["key"] not in self._hidden_keys and entry["type"] != "separator"]

    def hidden_items(self) -> List[Dict[str, Any]]:
        return [entry for entry in self._entries if entry["key"] in self._hidden_keys and entry["type"] != "separator"]

    def restore_defaults(self) -> None:
        self._entries = list(self._default_entries)
        self._hidden_keys = set()
        self._apply_state()

    def set_custom_state(self, visible_keys: List[Any], hidden_keys: List[Any]) -> None:
        seen: Set[Any] = set()
        reordered: List[Dict[str, Any]] = []
        for key in visible_keys:
            if key in self._entry_by_key and key not in seen:
                reordered.append(self._entry_by_key[key])
                seen.add(key)
        for entry in self._entries:
            if entry["key"] not in seen:
                reordered.append(entry)
                seen.add(entry["key"])
        self._entries = reordered
        self._hidden_keys = set(hidden_keys)
        self._apply_state()
        self.save_state()

    def _available_width(self) -> int:
        parent = self.parentWidget()
        if parent is not None and parent.width() > 0:
            return parent.width()
        if self.width() > 0:
            return self.width()
        return 2000

    def _entry_pixel_width(self, entry: Dict[str, Any], show_text: bool) -> int:
        if entry["type"] == "separator":
            return 14
        if entry["type"] == "widget":
            return entry["widget"].sizeHint().width() + 8
        action = entry["action"]
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(action.text()) if show_text else 0
        icon_w = self.iconSize().width() if not action.icon().isNull() else 0
        return text_w + icon_w + 28

    def _row_for_index(self, index: int) -> QToolBar:
        if index == 0:
            return self
        while len(self._extra_rows) < index:
            row = QToolBar(self.parentWidget())
            row.setObjectName(f"{self.objectName()}_row{len(self._extra_rows) + 1}")
            row.setMovable(False)
            self._extra_rows.append(row)
        return self._extra_rows[index - 1]

    def _apply_state(self) -> None:
        self._rebuilding = True
        self.clear()
        for row in self._extra_rows:
            row.clear()

        self._update_overflow_menu()

        visible_entries = [entry for entry in self._entries if entry["key"] not in self._hidden_keys]
        compact = bool(self.settings.value("app/toolbar_compact", False, type=bool))
        available_width = self._available_width()
        reserved = 0
        if self._more_action.isVisible():
            reserved += self._entry_pixel_width({"type": "action", "action": self._more_action}, not compact)
        reserved += self._entry_pixel_width({"type": "action", "action": self._customize_action}, not compact)

        rows: List[List[Dict[str, Any]]] = [[]]
        row_width = reserved
        for entry in visible_entries:
            width = self._entry_pixel_width(entry, not compact)
            if row_width + width > available_width and rows[-1]:
                rows.append([])
                row_width = 0
            rows[-1].append(entry)
            row_width += width

        used_rows = []
        for index, row_entries in enumerate(rows):
            toolbar = self._row_for_index(index)
            used_rows.append(toolbar)
            for entry in row_entries:
                if entry["type"] in ("action", "separator"):
                    (super().addAction if toolbar is self else toolbar.addAction)(entry["action"])
                elif entry["type"] == "widget":
                    (super().addWidget if toolbar is self else toolbar.addWidget)(entry["widget"])

        last_row = used_rows[-1] if used_rows else self
        if self._more_action.isVisible():
            (super().addAction if last_row is self else last_row.addAction)(self._more_action)
        (super().addAction if last_row is self else last_row.addAction)(self._customize_action)

        self._attach_extra_rows(used_rows)
        for row in self._extra_rows:
            row.setVisible(row in used_rows)

        self._rebuilding = False
        self._apply_style()

    def _attach_extra_rows(self, used_rows: List[QToolBar]) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        layout = parent.layout()
        if layout is None:
            return
        anchor = self
        for row in self._extra_rows:
            if row in used_rows and layout.indexOf(row) < 0:
                index = layout.indexOf(anchor)
                layout.insertWidget(index + 1, row)
            if row in used_rows:
                anchor = row

    def _apply_style(self) -> None:
        compact = bool(self.settings.value("app/toolbar_compact", False, type=bool))
        style = Qt.ToolButtonStyle.ToolButtonIconOnly if compact else Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        icon_px = scaled_font_size(18)
        font_size = scaled_font_pt(10)
        for toolbar in [self] + self._extra_rows:
            toolbar.setToolButtonStyle(style)
            toolbar.setIconSize(QSize(icon_px, icon_px))
            toolbar.setStyleSheet(
                f"QToolBar {{ spacing: 4px; padding: 2px; }} "
                f"QToolButton {{ font-size: {font_size}; padding: 5px 8px; }}"
            )

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        if self._rebuilding:
            return
        new_width = event.size().width()
        if abs(new_width - self._last_reflow_width) < 12:
            return
        self._last_reflow_width = new_width
        QTimer.singleShot(0, self._apply_state)

    def _update_overflow_menu(self) -> None:
        self._more_menu.clear()
        hidden = self.hidden_items()
        if not hidden:
            self._more_action.setVisible(False)
            return
        self._more_action.setVisible(True)
        for entry in hidden:
            action = QAction(entry["label"], self)
            action.triggered.connect(lambda checked=False, key=entry["key"]: self._restore_item(key))
            self._more_menu.addAction(action)

    def _restore_item(self, key: Any) -> None:
        self._hidden_keys.discard(key)
        self._apply_state()
        self.save_state()

    def open_customizer(self) -> None:
        dialog = ToolbarCustomizationDialog(self, self.parent())
        dialog.accepted.connect(dialog.apply)
        dialog.exec()

    def save_state(self) -> None:
        payload = {"hidden": sorted(self._hidden_keys)}
        self.settings.setValue(f"toolbar/{self.scope}", json.dumps(payload))

    def load_state(self) -> None:
        raw = self.settings.value(f"toolbar/{self.scope}")
        if not raw:
            return
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            return
        self._hidden_keys = set(payload.get("hidden", []))
        self._apply_state()

    def finalize(self) -> None:
        self._default_entries = list(self._entries)
        self.load_state()
        self._apply_state()
        self.save_state()
