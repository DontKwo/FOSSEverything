"""Reusable command palette for finding FOSSEverything features by intent."""
from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout

from app.core.tool_registry import ToolDefinition, ToolRegistry
from app.core.tooltips import TooltipEntry, keywords_tooltip, tooltip_search
from app.ui.ui_scaling import scaled_font_pt


class ToolSearchPalette(QDialog):
    """A keyboard-friendly Ctrl+K picker backed by the offline search engine."""

    def __init__(self, registry: ToolRegistry, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self.registry = registry
        self.selected_tool: ToolDefinition | None = None
        self.setWindowTitle("Find a tool")
        self.resize(560, 380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        self.query = QLineEdit(placeholderText="Search: merge PDF, crop image, convert...")
        self.query.setMinimumHeight(38)
        self.query.setClearButtonEnabled(True)
        self.query.setStyleSheet(f"font-size: {scaled_font_pt(14)}; padding: 4px 10px;")
        self.results = QListWidget()
        self.results.setSpacing(2)
        self.result_count = QLabel()
        self.result_count.setStyleSheet(f"font-size: {scaled_font_pt(11)};")
        layout.addWidget(self.query)
        layout.addWidget(self.results)
        layout.addWidget(self.result_count)

        self.query.textChanged.connect(self._refresh)
        self.results.itemActivated.connect(self._choose)
        self.query.installEventFilter(self)
        self._refresh()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.query.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def _refresh(self) -> None:
        self.results.clear()
        query = self.query.text()
        matches = self.registry.search(query, limit=50)
        for match in matches:
            tool = match.tool
            item = QListWidgetItem(f"{tool.title}  -  {tool.category}\n{tool.description}")
            item.setToolTip(keywords_tooltip(tool.keywords))
            item.setData(Qt.ItemDataRole.UserRole, match)
            self.results.addItem(item)

        tooltip_matches = tooltip_search(query, limit=20) if query.strip() else []
        for entry in tooltip_matches:
            item = QListWidgetItem(f"{entry.label}  -  UI tip\n{entry.description}")
            item.setToolTip(entry.description)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.results.addItem(item)

        total = len(matches) + len(tooltip_matches)
        if total:
            self.results.setCurrentRow(0)
            plural = "matches" if total != 1 else "match"
            self.result_count.setText(f"{total} {plural} - Enter to open")
        else:
            empty = QListWidgetItem("No tools match that search.")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.results.addItem(empty)
            self.result_count.setText("Try a broader word or a filter such as pdf:")

    def _choose(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if data is None or isinstance(data, TooltipEntry):
            return
        self.selected_tool = data.tool
        self.accept()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.query and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                step = 1 if event.key() == Qt.Key.Key_Down else -1
                row = max(0, min(self.results.count() - 1, self.results.currentRow() + step))
                self.results.setCurrentRow(row)
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                item = self.results.currentItem()
                if item:
                    self._choose(item)
                return True
            if event.key() == Qt.Key.Key_Escape:
                self.reject()
                return True
        return super().eventFilter(watched, event)
