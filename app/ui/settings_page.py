"""Base class shared by every page in the Settings dashboard."""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QWidget


class SettingsPage(QWidget):
    """Base class for individual settings pages."""
    def __init__(self, settings: QSettings, main_window: Any = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self) -> None:
        """Override to create this page's UI."""
        pass

    def save_settings(self) -> None:
        """Override to save changes to QSettings."""
        pass

    def reset_to_defaults(self) -> None:
        """Override to reset this page to default values."""
        pass
